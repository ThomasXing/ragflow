#
#  Copyright 2024 The InfiniFlow Authors. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
#
"""
文件权限检查模块

提供文件共享权限的检查功能，包括：
- 权限级别验证
- 操作权限检查
- 权限继承处理
"""
from typing import Optional, Tuple, List, Set

from api.db import FilePermissionLevel
from api.db.db_models import File
from api.db.services.file_permission_service import FilePermissionService
from api.db.services.team_permission_service import TeamPermissionService
from api.db.services.file_service import FileService
from api.db.services.user_service import TenantService
from api.common.check_team_permission import check_file_team_permission


# 权限级别优先级映射（数值越高权限越大）
PERMISSION_PRIORITY = {
    FilePermissionLevel.VIEW: 1,
    FilePermissionLevel.EDIT: 2,
    FilePermissionLevel.ADMIN: 3,
    FilePermissionLevel.OWNER: 4,
}

# 操作所需权限级别映射
OPERATION_PERMISSIONS = {
    "view": FilePermissionLevel.VIEW,        # 查看文件/文件夹
    "download": FilePermissionLevel.VIEW,    # 下载文件
    "edit": FilePermissionLevel.EDIT,        # 编辑文件内容
    "upload": FilePermissionLevel.EDIT,      # 上传新文件
    "create_folder": FilePermissionLevel.EDIT,  # 创建子文件夹
    "delete": FilePermissionLevel.ADMIN,     # 删除文件/文件夹
    "rename": FilePermissionLevel.ADMIN,     # 重命名
    "move": FilePermissionLevel.ADMIN,       # 移动
    "share": FilePermissionLevel.ADMIN,      # 分享给他人
    "manage_permissions": FilePermissionLevel.ADMIN,  # 管理权限
    "transfer_ownership": FilePermissionLevel.OWNER,  # 转让所有权
}


def get_permission_priority(permission_level: str) -> int:
    """
    获取权限级别的优先级数值

    Args:
        permission_level: 权限级别字符串

    Returns:
        优先级数值，未知权限返回0
    """
    return PERMISSION_PRIORITY.get(permission_level, 0)


def compare_permissions(level1: str, level2: str) -> int:
    """
    比较两个权限级别

    Args:
        level1: 第一个权限级别
        level2: 第二个权限级别

    Returns:
        >0 如果 level1 > level2
        <0 如果 level1 < level2
        =0 如果 level1 == level2
    """
    return get_permission_priority(level1) - get_permission_priority(level2)


def get_effective_permission(file_id: str, user_id: str) -> Optional[str]:
    """
    获取用户对文件的有效权限（考虑继承和团队共享）

    权限优先级:
    1. 所有者权限 (created_by == user_id 或 tenant_id == user_id)
    2. 显式共享权限
    3. 团队共享权限
    4. 继承的共享权限
    5. 租户权限

    Args:
        file_id: 文件ID
        user_id: 用户ID

    Returns:
        有效权限级别字符串，如果没有权限返回 None
    """
    # Step 1: 检查是否是文件所有者
    e, file = FileService.get_by_id(file_id)
    if e and file:
        if file.created_by == user_id:
            return FilePermissionLevel.OWNER

        # Step 2: 检查是否是租户所有者（文件所属租户）
        if file.tenant_id == user_id:
            return FilePermissionLevel.OWNER

        # Step 3: 检查显式共享权限
        explicit_perm = FilePermissionService.get_user_permission(file_id, user_id)
        if explicit_perm:
            return explicit_perm

        # Step 4: 检查团队共享权限
        team_perm = TeamPermissionService.check_user_team_permission(user_id, file_id, file.tenant_id)
        if team_perm:
            return team_perm

        # Step 5: 检查继承的共享权限
        inherited_perm = FilePermissionService.get_user_effective_permission(file_id, user_id)
        if inherited_perm and inherited_perm != FilePermissionLevel.OWNER:
            # 继承权限可能来自父文件夹的共享
            return inherited_perm

        # Step 6: 检查租户权限（知识库团队权限）
        if check_file_team_permission(file, user_id):
            # 租户成员默认有 view 权限
            return FilePermissionLevel.VIEW

    return None


def check_file_permission(
    file_id: str,
    user_id: str,
    required_level: str
) -> Tuple[bool, str]:
    """
    检查用户对文件是否有指定的权限级别

    Args:
        file_id: 文件ID
        user_id: 用户ID
        required_level: 需要的权限级别

    Returns:
        (是否有权限, 错误消息)
    """
    # 获取用户的有效权限
    effective_perm = get_effective_permission(file_id, user_id)

    if effective_perm is None:
        # 检查是否有租户级别权限
        e, file = FileService.get_by_id(file_id)
        if e and file:
            if check_file_team_permission(file, user_id):
                # 租户成员默认有 view 权限
                if required_level == FilePermissionLevel.VIEW:
                    return True, ""
                return False, "权限不足"

        return False, "您没有访问此文件的权限"

    # 比较权限级别
    if get_permission_priority(effective_perm) >= get_permission_priority(required_level):
        return True, ""

    return False, f"需要 {required_level} 权限，当前权限为 {effective_perm}"


def check_file_operation_permission(
    file_id: str,
    user_id: str,
    operation: str
) -> Tuple[bool, str]:
    """
    检查用户是否有权限执行特定操作

    Args:
        file_id: 文件ID
        user_id: 用户ID
        operation: 操作名称 (view, download, edit, upload, create_folder, delete, rename, move, share)

    Returns:
        (是否有权限, 错误消息)
    """
    if operation not in OPERATION_PERMISSIONS:
        return False, f"未知操作: {operation}"

    required_level = OPERATION_PERMISSIONS[operation]
    return check_file_permission(file_id, user_id, required_level)


def check_files_permission(
    file_ids: List[str],
    user_id: str,
    required_level: str
) -> Tuple[List[str], List[str]]:
    """
    批量检查多个文件的权限

    Args:
        file_ids: 文件ID列表
        user_id: 用户ID
        required_level: 需要的权限级别

    Returns:
        (有权限的文件ID列表, 无权限的文件ID列表)
    """
    allowed = []
    denied = []

    for file_id in file_ids:
        has_perm, _ = check_file_permission(file_id, user_id, required_level)
        if has_perm:
            allowed.append(file_id)
        else:
            denied.append(file_id)

    return allowed, denied


def get_permission_info(file_id: str, user_id: str) -> dict:
    """
    获取用户对文件的权限详情

    Args:
        file_id: 文件ID
        user_id: 用户ID

    Returns:
        权限信息字典，包含:
        - is_owner: 是否是所有者
        - permission_level: 权限级别
        - permission_source: 权限来源 (owner/explicit/team/inherited/tenant/none)
        - inherited_from: 继承来源文件信息（如果有继承权限）
    """
    result = {
        "is_owner": False,
        "permission_level": None,
        "permission_source": "none",
        "inherited_from": [],
    }

    # 检查是否是所有者
    e, file = FileService.get_by_id(file_id)
    if e and file:
        if file.created_by == user_id or file.tenant_id == user_id:
            result["is_owner"] = True
            result["permission_level"] = FilePermissionLevel.OWNER
            result["permission_source"] = "owner"
            return result

    # 检查显式权限
    explicit_perm = FilePermissionService.get_user_permission(file_id, user_id)
    if explicit_perm:
        result["permission_level"] = explicit_perm
        result["permission_source"] = "explicit"

    # 检查团队共享权限（在显式权限之后，继承权限之前）
    if result["permission_level"] is None and e and file:
        team_perm = TeamPermissionService.check_user_team_permission(user_id, file_id, file.tenant_id)
        if team_perm:
            result["permission_level"] = team_perm
            result["permission_source"] = "team"

    # 检查继承权限
    inherited_perms = FilePermissionService.get_inherited_permissions(file_id, user_id)
    if inherited_perms:
        result["inherited_from"] = inherited_perms
        # 如果没有显式权限和团队共享权限，使用继承权限中的最高级别
        if result["permission_level"] is None:
            best_inherited = max(
                inherited_perms,
                key=lambda x: get_permission_priority(x["permission_level"])
            )
            result["permission_level"] = best_inherited["permission_level"]
            result["permission_source"] = "inherited"

    # 如果仍然没有权限，检查租户权限
    if result["permission_level"] is None:
        if e and file:
            if check_file_team_permission(file, user_id):
                result["permission_level"] = FilePermissionLevel.VIEW
                result["permission_source"] = "tenant"

    return result


def can_user_share_file(file_id: str, user_id: str) -> Tuple[bool, str]:
    """
    检查用户是否可以分享文件

    只有 admin 或 owner 权限的用户才能分享文件

    Args:
        file_id: 文件ID
        user_id: 用户ID

    Returns:
        (是否可以分享, 错误消息)
    """
    return check_file_operation_permission(file_id, user_id, "share")


def can_user_manage_permissions(
    file_id: str,
    user_id: str,
    target_permission: Optional[str] = None
) -> Tuple[bool, str]:
    """
    检查用户是否可以管理文件权限

    规则:
    - admin 可以管理 view 和 edit 权限
    - owner 可以管理所有权限级别

    Args:
        file_id: 文件ID
        user_id: 用户ID
        target_permission: 要设置的目标权限级别（可选）

    Returns:
        (是否可以管理, 错误消息)
    """
    effective_perm = get_effective_permission(file_id, user_id)

    if effective_perm is None:
        return False, "您没有此文件的访问权限"

    # owner 可以管理所有权限
    if effective_perm == FilePermissionLevel.OWNER:
        return True, ""

    # admin 只能管理 view 和 edit 权限
    if effective_perm == FilePermissionLevel.ADMIN:
        if target_permission and target_permission == FilePermissionLevel.ADMIN:
            return False, "只有所有者才能设置 admin 权限"
        if target_permission and target_permission == FilePermissionLevel.OWNER:
            return False, "只有所有者才能转让所有权"
        return True, ""

    return False, "需要 admin 或 owner 权限才能管理权限"


def filter_files_by_permission(
    file_ids: List[str],
    user_id: str,
    required_level: str = FilePermissionLevel.VIEW
) -> List[str]:
    """
    过滤出用户有权限的文件

    Args:
        file_ids: 文件ID列表
        user_id: 用户ID
        required_level: 需要的权限级别

    Returns:
        有权限的文件ID列表
    """
    allowed, _ = check_files_permission(file_ids, user_id, required_level)
    return allowed


def check_parent_folder_permission(
    file_id: str,
    user_id: str,
    required_level: str
) -> Tuple[bool, str]:
    """
    检查用户对文件父文件夹的权限

    用于检查创建、上传等需要父文件夹权限的操作

    Args:
        file_id: 文件ID（如果文件不存在，传入预期的父文件夹ID）
        user_id: 用户ID
        required_level: 需要的权限级别

    Returns:
        (是否有权限, 错误消息)
    """
    e, file = FileService.get_by_id(file_id)

    if not e or not file:
        # 文件不存在，直接检查传入的ID作为文件夹ID
        return check_file_permission(file_id, user_id, required_level)

    # 文件存在，检查其父文件夹权限
    parent_id = file.parent_id
    if not parent_id or parent_id == file_id:
        # 根目录，检查文件本身权限
        return check_file_permission(file_id, user_id, required_level)

    return check_file_permission(parent_id, user_id, required_level)


def get_shareable_users(file_id: str, user_id: str, tenant_id: str) -> Tuple[bool, List[dict]]:
    """
    获取可以分享给的用户列表

    返回同一租户内、当前用户有权限分享的用户列表

    Args:
        file_id: 文件ID
        user_id: 当前用户ID
        tenant_id: 租户ID

    Returns:
        (是否成功, 用户列表或错误消息)
    """
    # 检查当前用户是否有分享权限
    can_share, msg = can_user_share_file(file_id, user_id)
    if not can_share:
        return False, []

    from api.db.services.user_service import UserTenantService, UserService

    # 获取租户内所有用户（包括 OWNER）
    tenant_members = UserTenantService.get_by_tenant_id(tenant_id)
    user_ids = [m["user_id"] for m in tenant_members if "user_id" in m]

    # 添加租户所有者
    user_ids.append(tenant_id)

    # 获取文件所有者
    e, file = FileService.get_by_id(file_id)
    owner_id = file.created_by if e and file else None

    # 获取已有的共享权限
    existing_perms = FilePermissionService.get_file_permissions(file_id)
    existing_user_perms = {p["target_user_id"]: p for p in existing_perms}

    users = []
    for uid in set(user_ids):
        # 排除当前用户和文件所有者
        if uid == user_id or uid == owner_id:
            continue

        user_info = UserService.query(id=uid)
        if user_info:
            user = user_info[0].to_dict()
            user["existing_permission"] = existing_user_perms.get(uid, {}).get("permission_level")
            users.append(user)

    return True, users
