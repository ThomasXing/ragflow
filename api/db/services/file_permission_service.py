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
import logging
from datetime import datetime
from typing import Optional, List, Tuple

from peewee import fn

from api.db import FilePermissionLevel
from api.db.db_models import DB, FilePermissionShare, File, UserTenant
from api.db.services.common_service import CommonService
from api.db.services.file_service import FileService
from api.db.services.user_service import TenantService
from common.misc_utils import get_uuid


class FilePermissionService(CommonService):
    """文件权限共享服务"""
    model = FilePermissionShare

    @classmethod
    @DB.connection_context()
    def create_share(
        cls,
        file_id: str,
        target_user_id: str,
        sharer_id: str,
        permission_level: str,
        tenant_id: str,
        expires_at: Optional[datetime] = None
    ) -> FilePermissionShare:
        """
        创建文件共享权限

        Args:
            file_id: 文件/文件夹ID
            target_user_id: 被共享的用户ID
            sharer_id: 共享者用户ID
            permission_level: 权限级别 (view/edit/admin)
            tenant_id: 租户ID
            expires_at: 权限过期时间（可选）

        Returns:
            创建的 FilePermissionShare 对象
        """
        # 检查是否已存在共享记录
        existing = cls.model.select().where(
            (cls.model.file_id == file_id) &
            (cls.model.target_user_id == target_user_id) &
            (cls.model.status == "1")
        ).first()

        if existing:
            # 更新现有记录
            existing.permission_level = permission_level
            existing.sharer_id = sharer_id
            existing.expires_at = expires_at
            existing.save()
            return existing

        # 创建新记录
        share = cls.model.create(
            id=get_uuid(),
            file_id=file_id,
            target_user_id=target_user_id,
            sharer_id=sharer_id,
            permission_level=permission_level,
            tenant_id=tenant_id,
            expires_at=expires_at,
            status="1"
        )
        return share

    @classmethod
    @DB.connection_context()
    def batch_create_shares(
        cls,
        shares: List[dict]
    ) -> Tuple[List[dict], List[dict]]:
        """
        批量创建共享权限

        Args:
            shares: 共享权限列表，每个元素包含:
                - file_id: 文件ID
                - target_user_id: 目标用户ID
                - sharer_id: 共享者ID
                - permission_level: 权限级别
                - tenant_id: 租户ID
                - expires_at: 过期时间（可选）

        Returns:
            (成功列表, 失败列表)
        """
        success = []
        failed = []

        for share_data in shares:
            try:
                share = cls.create_share(
                    file_id=share_data["file_id"],
                    target_user_id=share_data["target_user_id"],
                    sharer_id=share_data["sharer_id"],
                    permission_level=share_data["permission_level"],
                    tenant_id=share_data["tenant_id"],
                    expires_at=share_data.get("expires_at")
                )
                success.append({
                    "share_id": share.id,
                    "file_id": share_data["file_id"],
                    "target_user_id": share_data["target_user_id"]
                })
            except Exception as e:
                logging.exception(f"Failed to create share for file {share_data.get('file_id')}")
                failed.append({
                    "file_id": share_data.get("file_id"),
                    "target_user_id": share_data.get("target_user_id"),
                    "error": str(e)
                })

        return success, failed

    @classmethod
    @DB.connection_context()
    def get_file_permissions(
        cls,
        file_id: str,
        status: str = "1"
    ) -> List[dict]:
        """
        获取文件的所有共享权限

        Args:
            file_id: 文件ID
            status: 状态过滤（默认获取有效权限）

        Returns:
            权限列表
        """
        now = datetime.now()

        query = cls.model.select().where(
            (cls.model.file_id == file_id) &
            (cls.model.status == status)
        )

        permissions = []
        for perm in query:
            # 检查是否过期
            if perm.expires_at and perm.expires_at < now:
                continue
            permissions.append(perm.to_dict())

        return permissions

    @classmethod
    @DB.connection_context()
    def get_user_permission(
        cls,
        file_id: str,
        user_id: str
    ) -> Optional[str]:
        """
        获取用户对文件的显式权限（不考虑继承）

        Args:
            file_id: 文件ID
            user_id: 用户ID

        Returns:
            权限级别字符串，如果没有权限返回 None
        """
        now = datetime.now()

        perm = cls.model.select().where(
            (cls.model.file_id == file_id) &
            (cls.model.target_user_id == user_id) &
            (cls.model.status == "1")
        ).first()

        if not perm:
            return None

        # 检查是否过期
        if perm.expires_at and perm.expires_at < now:
            return None

        return perm.permission_level

    @classmethod
    @DB.connection_context()
    def get_user_effective_permission(
        cls,
        file_id: str,
        user_id: str
    ) -> Optional[str]:
        """
        获取用户对文件的有效权限（考虑继承）

        权限优先级: 显式权限 > 继承权限 > 所有者权限

        Args:
            file_id: 文件ID
            user_id: 用户ID

        Returns:
            有效权限级别，如果没有权限返回 None
        """
        # Step 1: 检查是否是文件所有者
        e, file = FileService.get_by_id(file_id)
        if e and file:
            if file.created_by == user_id:
                return FilePermissionLevel.OWNER

            # Step 2: 检查是否是租户所有者（文件所属租户）
            if file.tenant_id == user_id:
                return FilePermissionLevel.OWNER

        # Step 3: 检查显式权限
        explicit_perm = cls.get_user_permission(file_id, user_id)

        # Step 4: 获取继承权限
        inherited_perms = []
        if e and file:
            parent_id = file.parent_id
            visited = set()
            max_depth = 100  # 防止循环引用导致的无限循环
            depth = 0

            # 遍历所有父文件夹
            while parent_id and parent_id != file_id and depth < max_depth:  # 根目录的 parent_id == id
                # 防止循环引用
                if parent_id in visited:
                    logging.warning(f"Circular reference detected in permission inheritance chain: {parent_id} already visited")
                    break
                visited.add(parent_id)

                parent_perm = cls.get_user_permission(parent_id, user_id)
                if parent_perm:
                    inherited_perms.append(parent_perm)
                e, parent = FileService.get_by_id(parent_id)
                if not e or not parent:
                    break
                parent_id = parent.parent_id
                depth += 1

            if depth >= max_depth:
                logging.error(f"Max depth ({max_depth}) exceeded while traversing permission inheritance for file {file_id}")

        # Step 5: 合并权限，取最高级别
        all_perms = ([explicit_perm] if explicit_perm else []) + inherited_perms

        if not all_perms:
            return None

        # 权限优先级映射
        priority = {
            FilePermissionLevel.VIEW: 1,
            FilePermissionLevel.EDIT: 2,
            FilePermissionLevel.ADMIN: 3,
            FilePermissionLevel.OWNER: 4,
        }

        return max(all_perms, key=lambda p: priority.get(p, 0))

    @classmethod
    @DB.connection_context()
    def get_inherited_permissions(
        cls,
        file_id: str,
        user_id: str
    ) -> List[dict]:
        """
        获取用户从父文件夹继承的所有权限

        Args:
            file_id: 文件ID
            user_id: 用户ID

        Returns:
            继承的权限列表，每项包含 file_id, permission_level, file_name
        """
        inherited = []
        e, file = FileService.get_by_id(file_id)

        if not e or not file:
            return inherited

        parent_id = file.parent_id
        visited = set()

        while parent_id and parent_id not in visited:
            visited.add(parent_id)
            perm = cls.get_user_permission(parent_id, user_id)

            if perm:
                e, parent = FileService.get_by_id(parent_id)
                if e and parent:
                    inherited.append({
                        "file_id": parent_id,
                        "file_name": parent.name,
                        "permission_level": perm
                    })

            e, parent = FileService.get_by_id(parent_id)
            if not e or not parent:
                break
            parent_id = parent.parent_id
            if parent_id == parent.id:  # 到达根目录
                break

        return inherited

    @classmethod
    @DB.connection_context()
    def update_permission(
        cls,
        share_id: str,
        permission_level: str,
        expires_at: Optional[datetime] = None
    ) -> bool:
        """
        更新共享权限

        Args:
            share_id: 共享记录ID
            permission_level: 新的权限级别
            expires_at: 新的过期时间

        Returns:
            是否更新成功
        """
        try:
            update_data = {"permission_level": permission_level}
            if expires_at is not None:
                update_data["expires_at"] = expires_at

            rows = cls.model.update(**update_data).where(
                cls.model.id == share_id
            ).execute()

            return rows > 0
        except Exception as e:
            logging.exception(f"Failed to update permission {share_id}")
            return False

    @classmethod
    @DB.connection_context()
    def revoke_permission(
        cls,
        share_id: str
    ) -> bool:
        """
        撤销共享权限（软删除）

        Args:
            share_id: 共享记录ID

        Returns:
            是否撤销成功
        """
        try:
            rows = cls.model.update(status="0").where(
                cls.model.id == share_id
            ).execute()

            return rows > 0
        except Exception as e:
            logging.exception(f"Failed to revoke permission {share_id}")
            return False

    @classmethod
    @DB.connection_context()
    def revoke_all_permissions(
        cls,
        file_id: str
    ) -> int:
        """
        撤销文件的所有共享权限

        Args:
            file_id: 文件ID

        Returns:
            撤销的权限数量
        """
        try:
            rows = cls.model.update(status="0").where(
                cls.model.file_id == file_id
            ).execute()

            return rows
        except Exception as e:
            logging.exception(f"Failed to revoke all permissions for file {file_id}")
            return 0

    @classmethod
    @DB.connection_context()
    def get_shared_files_for_user(
        cls,
        user_id: str,
        page: int = 1,
        page_size: int = 15,
        keywords: str = ""
    ) -> Tuple[List[dict], int]:
        """
        获取共享给用户的所有文件

        Args:
            user_id: 用户ID
            page: 页码
            page_size: 每页数量
            keywords: 搜索关键词

        Returns:
            (文件列表, 总数)
        """
        now = datetime.now()

        # 构建查询
        query = (
            cls.model
            .select(File, cls.model.permission_level, cls.model.expires_at, cls.model.id.alias("share_id"))
            .join(File, on=(File.id == cls.model.file_id))
            .where(
                (cls.model.target_user_id == user_id) &
                (cls.model.status == "1") &
                (
                    (cls.model.expires_at.is_null()) |
                    (cls.model.expires_at >= now)
                )
            )
        )

        # 关键词搜索
        if keywords:
            query = query.where(File.name.contains(keywords))

        # 计算总数
        total = query.count()

        # 分页
        files = query.paginate(page, page_size)

        result = []
        for item in files:
            file_dict = item.file.to_dict()
            file_dict["share_permission"] = item.file_permission_share.permission_level
            file_dict["share_expires_at"] = item.file_permission_share.expires_at
            file_dict["share_id"] = item.file_permission_share.id
            result.append(file_dict)

        return result, total

    @classmethod
    @DB.connection_context()
    def get_all_descendants(
        cls,
        folder_id: str
    ) -> List[str]:
        """
        获取文件夹的所有子资源ID（递归）

        Args:
            folder_id: 文件夹ID

        Returns:
            所有子文件/文件夹的ID列表
        """
        descendants = []

        def _collect_descendants(parent_id):
            children = File.select().where(File.parent_id == parent_id)
            for child in children:
                descendants.append(child.id)
                if child.type == "folder":  # FileType.FOLDER.value
                    _collect_descendants(child.id)

        _collect_descendants(folder_id)
        return descendants

    @classmethod
    @DB.connection_context()
    def get_files_shared_by_user(
        cls,
        user_id: str,
        page: int = 1,
        page_size: int = 15,
        keywords: str = ""
    ) -> Tuple[List[dict], int]:
        """
        获取用户分享给他人的所有文件

        Args:
            user_id: 用户ID
            page: 页码
            page_size: 每页数量
            keywords: 搜索关键词

        Returns:
            (文件列表, 总数)
        """
        now = datetime.now()

        # 构建查询
        query = (
            cls.model
            .select(File, cls.model.permission_level, cls.model.target_user_id)
            .join(File, on=(File.id == cls.model.file_id))
            .where(
                (cls.model.sharer_id == user_id) &
                (cls.model.status == "1") &
                (
                    (cls.model.expires_at.is_null()) |
                    (cls.model.expires_at >= now)
                )
            )
        )

        # 关键词搜索
        if keywords:
            query = query.where(File.name.contains(keywords))

        # 计算总数
        total = query.count()

        # 分页
        files = query.paginate(page, page_size)

        result = []
        for item in files:
            file_dict = item.file.to_dict()
            file_dict["share_permission"] = item.file_permission_share.permission_level
            file_dict["shared_with"] = item.file_permission_share.target_user_id
            result.append(file_dict)

        return result, total

    @classmethod
    @DB.connection_context()
    def can_share_to_user(
        cls,
        file_id: str,
        target_user_id: str,
        tenant_id: str
    ) -> Tuple[bool, str]:
        """
        检查是否可以将文件分享给目标用户

        规则：
        1. 目标用户必须在同一租户内
        2. 目标用户不能是文件所有者
        3. 目标用户不能已经有相同或更高级别的权限

        Args:
            file_id: 文件ID
            target_user_id: 目标用户ID
            tenant_id: 租户ID

        Returns:
            (是否可以分享, 错误消息)
        """
        # 检查目标用户是否在同一租户
        tenant_users = TenantService.get_joined_tenants_by_user_id(target_user_id)
        user_tenants = [t["tenant_id"] for t in tenant_users]

        # 用户是自己租户的owner，或者是被邀请加入的租户成员
        if tenant_id not in user_tenants and tenant_id != target_user_id:
            # 检查是否是租户owner
            if target_user_id != tenant_id:
                return False, "目标用户不在同一租户内"

        # 检查目标用户是否是文件所有者
        e, file = FileService.get_by_id(file_id)
        if e and file and file.created_by == target_user_id:
            return False, "不能将文件分享给所有者"

        return True, ""

    @classmethod
    @DB.connection_context()
    def get_share_by_id(
        cls,
        share_id: str
    ) -> Tuple[bool, Optional[dict]]:
        """
        获取共享记录详情

        Args:
            share_id: 共享记录ID

        Returns:
            (是否存在, 共享记录字典)
        """
        share = cls.model.select().where(cls.model.id == share_id).first()
        if share:
            return True, share.to_dict()
        return False, None

    @classmethod
    @DB.connection_context()
    def delete_file_shares(cls, file_id: str) -> int:
        """
        删除文件的所有共享记录（硬删除，用于文件被删除时）

        Args:
            file_id: 文件ID

        Returns:
            删除的记录数
        """
        try:
            return cls.model.delete().where(cls.model.file_id == file_id).execute()
        except Exception as e:
            logging.exception(f"Failed to delete shares for file {file_id}")
            return 0

    @classmethod
    @DB.connection_context()
    def delete_folder_shares_recursive(cls, folder_id: str) -> int:
        """
        递归删除文件夹及其所有子文件的共享记录

        Args:
            folder_id: 文件夹ID

        Returns:
            删除的总记录数
        """
        total_deleted = 0

        # 删除当前文件夹的共享记录
        total_deleted += cls.delete_file_shares(folder_id)

        # 获取所有子文件
        descendant_ids = cls.get_all_descendants(folder_id)

        # 批量删除子文件的共享记录
        for descendant_id in descendant_ids:
            total_deleted += cls.delete_file_shares(descendant_id)

        return total_deleted
