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
文件权限共享 API 端点

提供文件共享权限管理的 REST API:
- 创建共享权限
- 获取共享列表
- 更新/撤销权限
- 获取共享给我的文件
"""
import logging
from datetime import datetime
from typing import Optional

from quart import request

from api.apps import login_required, current_user
from api.db import FilePermissionLevel
from api.db.services.file_permission_service import FilePermissionService
from api.db.services.team_permission_service import TeamPermissionService
from api.db.services.file_service import FileService
from api.db.services.user_service import UserService
from api.common.check_file_permission import (
    can_user_share_file,
    can_user_manage_permissions,
    get_permission_info,
    check_file_permission,
)
from api.utils.api_utils import (
    get_json_result,
    get_data_error_result,
    server_error_response,
    validate_request,
)
from common.constants import RetCode
from common.misc_utils import get_uuid


@manager.route('/share', methods=['POST'])  # noqa: F821
@login_required
@validate_request("file_id", "target_user_ids", "permission_level")
async def create_share():
    """
    创建文件共享权限

    Request:
        {
            "file_id": "文件ID",
            "target_user_ids": ["用户ID列表"],
            "permission_level": "view|edit|admin",
            "expires_at": "过期时间（可选，ISO格式）"
        }

    Response:
        {
            "data": {
                "shares": [...],
                "failed": [...]
            }
        }
    """
    req = await request.get_json()

    file_id = req.get("file_id")
    target_user_ids = req.get("target_user_ids", [])
    permission_level = req.get("permission_level")
    expires_at_str = req.get("expires_at")

    # 验证权限级别
    valid_levels = [FilePermissionLevel.VIEW, FilePermissionLevel.EDIT, FilePermissionLevel.ADMIN]
    if permission_level not in valid_levels:
        return get_json_result(
            data=False,
            message=f"无效的权限级别，有效值为: {', '.join(valid_levels)}",
            code=RetCode.ARGUMENT_ERROR
        )

    # 检查文件是否存在
    e, file = FileService.get_by_id(file_id)
    if not e or not file:
        return get_data_error_result(message="文件不存在")

    # 检查当前用户是否有分享权限
    can_share, msg = can_user_share_file(file_id, current_user.id)
    if not can_share:
        return get_json_result(
            data=False,
            message=msg or "您没有分享此文件的权限",
            code=RetCode.AUTHENTICATION_ERROR
        )

    # 检查当前用户是否能设置该权限级别
    can_manage, msg = can_user_manage_permissions(file_id, current_user.id, permission_level)
    if not can_manage:
        return get_json_result(
            data=False,
            message=msg or "您没有设置此权限级别的权限",
            code=RetCode.AUTHENTICATION_ERROR
        )

    # 解析过期时间
    expires_at = None
    if expires_at_str:
        try:
            expires_at = datetime.fromisoformat(expires_at_str.replace('Z', '+00:00'))
        except ValueError:
            return get_json_result(
                data=False,
                message="无效的过期时间格式",
                code=RetCode.ARGUMENT_ERROR
            )

    # 批量创建共享
    shares = []
    failed = []

    for target_user_id in target_user_ids:
        # 检查是否可以分享给该用户
        can_share_to, err_msg = FilePermissionService.can_share_to_user(
            file_id, target_user_id, file.tenant_id
        )

        if not can_share_to:
            failed.append({
                "target_user_id": target_user_id,
                "error": err_msg
            })
            continue

        try:
            share = FilePermissionService.create_share(
                file_id=file_id,
                target_user_id=target_user_id,
                sharer_id=current_user.id,
                permission_level=permission_level,
                tenant_id=file.tenant_id,
                expires_at=expires_at
            )
            shares.append(share.to_dict())
        except Exception as e:
            logging.exception(f"Failed to create share for user {target_user_id}")
            failed.append({
                "target_user_id": target_user_id,
                "error": str(e)
            })

    return get_json_result(data={
        "shares": shares,
        "failed": failed
    })


@manager.route('/list', methods=['GET'])  # noqa: F821
@login_required
async def list_shares():
    """
    获取文件的共享权限列表

    Query Parameters:
        file_id: 文件ID

    Response:
        {
            "data": {
                "permissions": [...],
                "inherited": [...],
                "can_manage": true/false
            }
        }
    """
    file_id = request.args.get("file_id")

    if not file_id:
        return get_json_result(
            data=False,
            message="缺少 file_id 参数",
            code=RetCode.ARGUMENT_ERROR
        )

    # 检查文件是否存在
    e, file = FileService.get_by_id(file_id)
    if not e or not file:
        return get_data_error_result(message="文件不存在")

    # 检查当前用户是否有权限查看
    has_perm, msg = check_file_permission(file_id, current_user.id, FilePermissionLevel.VIEW)
    if not has_perm:
        return get_json_result(
            data=False,
            message=msg or "您没有查看此文件的权限",
            code=RetCode.AUTHENTICATION_ERROR
        )

    # 获取显式权限列表
    permissions = FilePermissionService.get_file_permissions(file_id)

    # 获取继承权限（仅当用户有管理权限时返回）
    inherited = []
    can_manage, _ = can_user_manage_permissions(file_id, current_user.id)

    if can_manage:
        inherited = FilePermissionService.get_inherited_permissions(file_id, current_user.id)

    # 获取用户信息
    for perm in permissions:
        user = UserService.query(id=perm.get("target_user_id"))
        if user:
            perm["target_user"] = user[0].to_dict()

        sharer = UserService.query(id=perm.get("sharer_id"))
        if sharer:
            perm["sharer"] = sharer[0].to_dict()

    return get_json_result(data={
        "permissions": permissions,
        "inherited": inherited,
        "can_manage": can_manage,
        "is_owner": file.created_by == current_user.id or file.tenant_id == current_user.id
    })


@manager.route('/update', methods=['PUT'])  # noqa: F821
@login_required
@validate_request("share_id", "permission_level")
async def update_share():
    """
    更新共享权限

    Request:
        {
            "share_id": "共享记录ID",
            "permission_level": "view|edit|admin",
            "expires_at": "过期时间（可选）"
        }

    Response:
        {
            "data": true
        }
    """
    req = await request.get_json()

    share_id = req.get("share_id")
    permission_level = req.get("permission_level")
    expires_at_str = req.get("expires_at")

    # 验证权限级别
    valid_levels = [FilePermissionLevel.VIEW, FilePermissionLevel.EDIT, FilePermissionLevel.ADMIN]
    if permission_level not in valid_levels:
        return get_json_result(
            data=False,
            message=f"无效的权限级别，有效值为: {', '.join(valid_levels)}",
            code=RetCode.ARGUMENT_ERROR
        )

    # 获取共享记录
    e, share = FilePermissionService.get_share_by_id(share_id)
    if not e or not share:
        return get_data_error_result(message="共享记录不存在")

    # 检查当前用户是否有权限管理
    can_manage, msg = can_user_manage_permissions(
        share["file_id"],
        current_user.id,
        permission_level
    )
    if not can_manage:
        return get_json_result(
            data=False,
            message=msg or "您没有管理此权限的权限",
            code=RetCode.AUTHENTICATION_ERROR
        )

    # 解析过期时间
    expires_at = None
    if expires_at_str:
        try:
            expires_at = datetime.fromisoformat(expires_at_str.replace('Z', '+00:00'))
        except ValueError:
            return get_json_result(
                data=False,
                message="无效的过期时间格式",
                code=RetCode.ARGUMENT_ERROR
            )

    # 更新权限
    success = FilePermissionService.update_permission(share_id, permission_level, expires_at)

    if not success:
        return get_data_error_result(message="更新权限失败")

    return get_json_result(data=True)


@manager.route('/revoke', methods=['DELETE'])  # noqa: F821
@login_required
async def revoke_share():
    """
    撤销共享权限

    Query Parameters:
        share_id: 共享记录ID

    Response:
        {
            "data": true
        }
    """
    share_id = request.args.get("share_id")

    if not share_id:
        return get_json_result(
            data=False,
            message="缺少 share_id 参数",
            code=RetCode.ARGUMENT_ERROR
        )

    # 获取共享记录
    e, share = FilePermissionService.get_share_by_id(share_id)
    if not e or not share:
        return get_data_error_result(message="共享记录不存在")

    # 检查当前用户是否有权限管理
    can_manage, msg = can_user_manage_permissions(share["file_id"], current_user.id)
    if not can_manage:
        return get_json_result(
            data=False,
            message=msg or "您没有管理此权限的权限",
            code=RetCode.AUTHENTICATION_ERROR
        )

    # 撤销权限
    success = FilePermissionService.revoke_permission(share_id)

    if not success:
        return get_data_error_result(message="撤销权限失败")

    return get_json_result(data=True)


@manager.route('/shared_with_me', methods=['GET'])  # noqa: F821
@login_required
async def shared_with_me():
    """
    获取共享给我的文件列表

    Query Parameters:
        page: 页码（默认1）
        page_size: 每页数量（默认15）
        keywords: 搜索关键词（可选）

    Response:
        {
            "data": {
                "files": [...],
                "total": 100
            }
        }
    """
    page = int(request.args.get("page", 1))
    page_size = int(request.args.get("page_size", 15))
    keywords = request.args.get("keywords", "")

    files, total = FilePermissionService.get_shared_files_for_user(
        user_id=current_user.id,
        page=page,
        page_size=page_size,
        keywords=keywords
    )

    return get_json_result(data={
        "files": files,
        "total": total
    })


@manager.route('/shared_by_me', methods=['GET'])  # noqa: F821
@login_required
async def shared_by_me():
    """
    获取我分享给他人的文件列表

    Query Parameters:
        page: 页码（默认1）
        page_size: 每页数量（默认15）
        keywords: 搜索关键词（可选）

    Response:
        {
            "data": {
                "files": [...],
                "total": 100
            }
        }
    """
    page = int(request.args.get("page", 1))
    page_size = int(request.args.get("page_size", 15))
    keywords = request.args.get("keywords", "")

    files, total = FilePermissionService.get_files_shared_by_user(
        user_id=current_user.id,
        page=page,
        page_size=page_size,
        keywords=keywords
    )

    return get_json_result(data={
        "files": files,
        "total": total
    })


@manager.route('/batch_share', methods=['POST'])  # noqa: F821
@login_required
@validate_request("file_ids", "target_user_ids", "permission_level")
async def batch_share():
    """
    批量设置文件共享权限

    Request:
        {
            "file_ids": ["文件ID列表"],
            "target_user_ids": ["用户ID列表"],
            "permission_level": "view|edit|admin",
            "expires_at": "过期时间（可选）"
        }

    Response:
        {
            "data": {
                "success": [...],
                "failed": [...]
            }
        }
    """
    req = await request.get_json()

    file_ids = req.get("file_ids", [])
    target_user_ids = req.get("target_user_ids", [])
    permission_level = req.get("permission_level")
    expires_at_str = req.get("expires_at")

    if not file_ids:
        return get_json_result(
            data=False,
            message="文件ID列表不能为空",
            code=RetCode.ARGUMENT_ERROR
        )

    if not target_user_ids:
        return get_json_result(
            data=False,
            message="用户ID列表不能为空",
            code=RetCode.ARGUMENT_ERROR
        )

    # 验证权限级别
    valid_levels = [FilePermissionLevel.VIEW, FilePermissionLevel.EDIT, FilePermissionLevel.ADMIN]
    if permission_level not in valid_levels:
        return get_json_result(
            data=False,
            message=f"无效的权限级别，有效值为: {', '.join(valid_levels)}",
            code=RetCode.ARGUMENT_ERROR
        )

    # 解析过期时间
    expires_at = None
    if expires_at_str:
        try:
            expires_at = datetime.fromisoformat(expires_at_str.replace('Z', '+00:00'))
        except ValueError:
            return get_json_result(
                data=False,
                message="无效的过期时间格式",
                code=RetCode.ARGUMENT_ERROR
            )

    success = []
    failed = []

    for file_id in file_ids:
        # 检查文件是否存在
        e, file = FileService.get_by_id(file_id)
        if not e or not file:
            failed.append({
                "file_id": file_id,
                "error": "文件不存在"
            })
            continue

        # 检查当前用户是否有分享权限
        can_share, msg = can_user_share_file(file_id, current_user.id)
        if not can_share:
            failed.append({
                "file_id": file_id,
                "error": msg or "没有分享权限"
            })
            continue

        # 检查是否能设置该权限级别
        can_manage, msg = can_user_manage_permissions(file_id, current_user.id, permission_level)
        if not can_manage:
            failed.append({
                "file_id": file_id,
                "error": msg or "没有设置此权限级别的权限"
            })
            continue

        # 批量创建共享
        shares_data = []
        for target_user_id in target_user_ids:
            can_share_to, _ = FilePermissionService.can_share_to_user(
                file_id, target_user_id, file.tenant_id
            )
            if can_share_to:
                shares_data.append({
                    "file_id": file_id,
                    "target_user_id": target_user_id,
                    "sharer_id": current_user.id,
                    "permission_level": permission_level,
                    "tenant_id": file.tenant_id,
                    "expires_at": expires_at
                })

        if shares_data:
            created, failed_creates = FilePermissionService.batch_create_shares(shares_data)
            success.extend(created)
            for fail in failed_creates:
                failed.append({
                    "file_id": file_id,
                    "target_user_id": fail.get("target_user_id"),
                    "error": fail.get("error")
                })

    return get_json_result(data={
        "success": success,
        "failed": failed
    })


@manager.route('/check', methods=['GET'])  # noqa: F821
@login_required
async def check_permission():
    """
    检查用户对文件的权限

    Query Parameters:
        file_id: 文件ID
        operation: 操作名称（可选，view/download/edit/upload/create_folder/delete/rename/move/share）

    Response:
        {
            "data": {
                "has_permission": true/false,
                "permission_level": "view|edit|admin|owner",
                "permission_source": "owner|explicit|inherited|tenant|none",
                "error_message": "错误消息（如果没有权限）"
            }
        }
    """
    from api.common.check_file_permission import check_file_operation_permission

    file_id = request.args.get("file_id")
    operation = request.args.get("operation")

    if not file_id:
        return get_json_result(
            data=False,
            message="缺少 file_id 参数",
            code=RetCode.ARGUMENT_ERROR
        )

    # 获取权限详情
    perm_info = get_permission_info(file_id, current_user.id)

    result = {
        "has_permission": perm_info["permission_level"] is not None,
        "permission_level": perm_info["permission_level"],
        "permission_source": perm_info["permission_source"],
        "is_owner": perm_info["is_owner"],
        "error_message": None
    }

    # 如果指定了操作，检查操作权限
    if operation:
        has_perm, msg = check_file_operation_permission(file_id, current_user.id, operation)
        result["has_permission"] = has_perm
        result["error_message"] = msg if not has_perm else None

    return get_json_result(data=result)


@manager.route('/shareable_users', methods=['GET'])  # noqa: F821
@login_required
async def get_shareable_users():
    """
    获取可分享的用户列表

    Query Parameters:
        file_id: 文件ID

    Response:
        {
            "data": {
                "users": [
                    {
                        "id": "用户ID",
                        "nickname": "用户昵称",
                        "email": "用户邮箱",
                        "existing_permission": "已有权限级别（如果有）"
                    }
                ],
                "can_share": true/false
            }
        }
    """
    from api.common.check_file_permission import get_shareable_users as _get_shareable_users

    file_id = request.args.get("file_id")

    if not file_id:
        return get_json_result(
            data=False,
            message="缺少 file_id 参数",
            code=RetCode.ARGUMENT_ERROR
        )

    # 检查文件是否存在
    e, file = FileService.get_by_id(file_id)
    if not e or not file:
        return get_data_error_result(message="文件不存在")

    # 获取可分享的用户列表
    success, users_or_msg = _get_shareable_users(file_id, current_user.id, file.tenant_id)

    if not success:
        return get_json_result(
            data=False,
            message=users_or_msg,
            code=RetCode.AUTHENTICATION_ERROR
        )

    return get_json_result(data={
        "users": users_or_msg,
        "can_share": True
    })


@manager.route('/team/enable', methods=['POST'])  # noqa: F821
@login_required
@validate_request("file_id", "permission_level")
async def enable_team_share():
    """
    启用团队共享

    Request:
        {
            "file_id": "文件ID",
            "permission_level": "view|edit|admin"
        }

    Response:
        {
            "data": {
                "success": true/false,
                "message": "操作结果消息"
            }
        }
    """
    from api.db.services.team_permission_service import TeamPermissionService
    from api.common.check_file_permission import can_user_manage_permissions

    req = await request.get_json()

    file_id = req.get("file_id")
    permission_level = req.get("permission_level")

    # 验证权限级别
    valid_levels = [FilePermissionLevel.VIEW, FilePermissionLevel.EDIT, FilePermissionLevel.ADMIN]
    if permission_level not in valid_levels:
        return get_json_result(
            data=False,
            message=f"无效的权限级别，有效值为: {', '.join(valid_levels)}",
            code=RetCode.ARGUMENT_ERROR
        )

    # 检查文件是否存在
    e, file = FileService.get_by_id(file_id)
    if not e or not file:
        return get_data_error_result(message="文件不存在")

    # 检查当前用户是否有权限管理权限
    can_manage, msg = can_user_manage_permissions(file_id, current_user.id, permission_level)
    if not can_manage:
        return get_json_result(
            data=False,
            message=msg or "您没有设置此权限级别的权限",
            code=RetCode.AUTHENTICATION_ERROR
        )

    # 启用团队共享
    success = TeamPermissionService.enable_team_share(
        file_id=file_id,
        tenant_id=file.tenant_id,
        user_id=current_user.id,
        permission_level=permission_level
    )

    if success:
        return get_json_result(data={
            "success": True,
            "message": "团队共享已启用"
        })
    else:
        return get_json_result(
            data=False,
            message="启用团队共享失败",
            code=RetCode.INTERNAL_ERROR
        )


@manager.route('/team/disable', methods=['POST'])  # noqa: F821
@login_required
@validate_request("file_id")
async def disable_team_share():
    """
    禁用团队共享

    Request:
        {
            "file_id": "文件ID"
        }

    Response:
        {
            "data": {
                "success": true/false,
                "message": "操作结果消息"
            }
        }
    """
    from api.db.services.team_permission_service import TeamPermissionService
    from api.common.check_file_permission import can_user_manage_permissions

    req = await request.get_json()

    file_id = req.get("file_id")

    # 检查文件是否存在
    e, file = FileService.get_by_id(file_id)
    if not e or not file:
        return get_data_error_result(message="文件不存在")

    # 检查当前用户是否有ADMIN权限
    can_manage, msg = can_user_manage_permissions(file_id, current_user.id, FilePermissionLevel.ADMIN)
    if not can_manage:
        return get_json_result(
            data=False,
            message=msg or "您没有禁用团队共享的权限",
            code=RetCode.AUTHENTICATION_ERROR
        )

    # 禁用团队共享
    success = TeamPermissionService.disable_team_share(
        file_id=file_id,
        tenant_id=file.tenant_id
    )

    if success:
        return get_json_result(data={
            "success": True,
            "message": "团队共享已禁用"
        })
    else:
        return get_json_result(
            data=False,
            message="禁用团队共享失败",
            code=RetCode.INTERNAL_ERROR
        )


@manager.route('/team/status', methods=['GET'])  # noqa: F821
@login_required
async def get_team_share_status():
    """
    获取团队共享状态

    Query Parameters:
        file_id: 文件ID

    Response:
        {
            "data": {
                "is_enabled": true/false,
                "permission_level": "view|edit|admin|null",
                "created_by": "创建者ID",
                "created_at": "创建时间",
                "updated_at": "更新时间"
            }
        }
    """
    from api.db.services.team_permission_service import TeamPermissionService

    file_id = request.args.get("file_id")

    if not file_id:
        return get_json_result(
            data=False,
            message="缺少 file_id 参数",
            code=RetCode.ARGUMENT_ERROR
        )

    # 检查文件是否存在
    e, file = FileService.get_by_id(file_id)
    if not e or not file:
        return get_data_error_result(message="文件不存在")

    # 获取团队共享状态
    status = TeamPermissionService.get_team_share_status(
        file_id=file_id,
        tenant_id=file.tenant_id
    )

    if status:
        return get_json_result(data=status)
    else:
        return get_json_result(data={
            "is_enabled": False,
            "permission_level": None,
            "created_by": None,
            "created_at": None,
            "updated_at": None
        })


@manager.route('/team/level', methods=['PUT'])  # noqa: F821
@login_required
@validate_request("file_id", "permission_level")
async def update_team_share_level():
    """
    更新团队共享权限级别

    Request:
        {
            "file_id": "文件ID",
            "permission_level": "view|edit|admin"
        }

    Response:
        {
            "data": {
                "success": true/false,
                "message": "操作结果消息"
            }
        }
    """
    from api.db.services.team_permission_service import TeamPermissionService
    from api.common.check_file_permission import can_user_manage_permissions

    req = await request.get_json()

    file_id = req.get("file_id")
    permission_level = req.get("permission_level")

    # 验证权限级别
    valid_levels = [FilePermissionLevel.VIEW, FilePermissionLevel.EDIT, FilePermissionLevel.ADMIN]
    if permission_level not in valid_levels:
        return get_json_result(
            data=False,
            message=f"无效的权限级别，有效值为: {', '.join(valid_levels)}",
            code=RetCode.ARGUMENT_ERROR
        )

    # 检查文件是否存在
    e, file = FileService.get_by_id(file_id)
    if not e or not file:
        return get_data_error_result(message="文件不存在")

    # 检查当前用户是否有权限管理权限
    can_manage, msg = can_user_manage_permissions(file_id, current_user.id, permission_level)
    if not can_manage:
        return get_json_result(
            data=False,
            message=msg or "您没有设置此权限级别的权限",
            code=RetCode.AUTHENTICATION_ERROR
        )

    # 更新团队共享权限级别
    success = TeamPermissionService.update_team_share_level(
        file_id=file_id,
        tenant_id=file.tenant_id,
        permission_level=permission_level
    )

    if success:
        return get_json_result(data={
            "success": True,
            "message": "团队共享权限级别已更新"
        })
    else:
        return get_json_result(
            data=False,
            message="更新团队共享权限级别失败",
            code=RetCode.INTERNAL_ERROR
        )
