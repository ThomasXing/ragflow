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
from typing import Optional, List, Dict, Any

from peewee import fn

from api.db.db_models import DB, TeamPermissionShare, File
from api.db.services.common_service import CommonService
from api.db.services.file_service import FileService
from api.db.services.user_service import TenantService
from common.misc_utils import get_uuid


class TeamPermissionService(CommonService):
    """团队权限共享服务"""
    model = TeamPermissionShare

    @classmethod
    @DB.connection_context()
    def enable_team_share(
        cls,
        file_id: str,
        tenant_id: str,
        user_id: str,
        permission_level: str = "view"
    ) -> bool:
        """
        启用团队共享

        Args:
            file_id: 文件/文件夹ID
            tenant_id: 租户ID
            user_id: 操作者用户ID
            permission_level: 权限级别 (view/edit/admin)

        Returns:
            True if successful, False otherwise
        """
        try:
            # 检查文件是否存在 - 注意：FileService.get_by_id 返回 (e, file) 元组
            e, file = FileService.get_by_id(file_id)
            if not e or not file:
                logging.error(f"File not found: {file_id}")
                return False

            # 检查是否已存在团队共享记录
            existing = cls.model.select().where(
                (cls.model.file_id == file_id) &
                (cls.model.tenant_id == tenant_id)
            ).first()

            if existing:
                # 更新现有记录
                existing.permission_level = permission_level
                existing.is_enabled = True
                existing.updated_at = datetime.now()
                existing.save()
            else:
                # 创建新记录
                cls.model.create(
                    id=get_uuid(),
                    file_id=file_id,
                    tenant_id=tenant_id,
                    permission_level=permission_level,
                    is_enabled=True,
                    created_by=user_id,
                    created_at=datetime.now(),
                    updated_at=datetime.now()
                )

            logging.info(f"Enabled team share for file {file_id} in tenant {tenant_id} with level {permission_level}")
            return True

        except Exception as e:
            logging.exception(f"Failed to enable team share for file {file_id}: {e}")
            return False

    @classmethod
    @DB.connection_context()
    def disable_team_share(
        cls,
        file_id: str,
        tenant_id: str
    ) -> bool:
        """
        禁用团队共享

        Args:
            file_id: 文件/文件夹ID
            tenant_id: 租户ID

        Returns:
            True if successful, False otherwise
        """
        try:
            # 查找现有记录
            existing = cls.model.select().where(
                (cls.model.file_id == file_id) &
                (cls.model.tenant_id == tenant_id)
            ).first()

            if not existing:
                logging.warning(f"No team share found for file {file_id} in tenant {tenant_id}")
                return False

            # 更新为禁用状态
            existing.is_enabled = False
            existing.updated_at = datetime.now()
            existing.save()

            logging.info(f"Disabled team share for file {file_id} in tenant {tenant_id}")
            return True

        except Exception as e:
            logging.exception(f"Failed to disable team share for file {file_id}: {e}")
            return False

    @classmethod
    @DB.connection_context()
    def get_team_share_status(
        cls,
        file_id: str,
        tenant_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        获取团队共享状态

        Args:
            file_id: 文件/文件夹ID
            tenant_id: 租户ID

        Returns:
            团队共享状态字典，如果不存在则返回None
        """
        try:
            record = cls.model.select().where(
                (cls.model.file_id == file_id) &
                (cls.model.tenant_id == tenant_id)
            ).first()

            if not record:
                return None

            return {
                "file_id": record.file_id,
                "tenant_id": record.tenant_id,
                "permission_level": record.permission_level,
                "is_enabled": record.is_enabled,
                "created_by": record.created_by,
                "created_at": record.created_at.isoformat() if record.created_at else None,
                "updated_at": record.updated_at.isoformat() if record.updated_at else None
            }

        except Exception as e:
            logging.exception(f"Failed to get team share status for file {file_id}: {e}")
            return None

    @classmethod
    @DB.connection_context()
    def update_team_share_level(
        cls,
        file_id: str,
        tenant_id: str,
        permission_level: str
    ) -> bool:
        """
        更新团队共享权限级别

        Args:
            file_id: 文件/文件夹ID
            tenant_id: 租户ID
            permission_level: 新的权限级别 (view/edit/admin)

        Returns:
            True if successful, False otherwise
        """
        try:
            # 查找现有记录
            existing = cls.model.select().where(
                (cls.model.file_id == file_id) &
                (cls.model.tenant_id == tenant_id)
            ).first()

            if not existing:
                logging.warning(f"No team share found for file {file_id} in tenant {tenant_id}")
                return False

            if not existing.is_enabled:
                logging.warning(f"Team share is not enabled for file {file_id}")
                return False

            # 更新权限级别
            existing.permission_level = permission_level
            existing.updated_at = datetime.now()
            existing.save()

            logging.info(f"Updated team share level for file {file_id} to {permission_level}")
            return True

        except Exception as e:
            logging.exception(f"Failed to update team share level for file {file_id}: {e}")
            return False

    @classmethod
    @DB.connection_context()
    def get_all_team_shares_for_user(
        cls,
        user_id: str,
        tenant_id: str,
        enabled_only: bool = True
    ) -> List[Dict[str, Any]]:
        """
        获取用户所在租户的所有团队共享

        安全要求：用户必须是租户成员才能获取团队共享列表
        Args:
            user_id: 用户ID（用于权限检查）
            tenant_id: 租户ID
            enabled_only: 是否只返回已启用的共享

        Returns:
            团队共享列表
        """
        try:
            # Step 1: 验证用户是否属于该租户（安全修复）
            joined_tenants = TenantService.get_joined_tenants_by_user_id(user_id)
            user_tenant_ids = {tenant["tenant_id"] for tenant in joined_tenants}
            
            # 如果用户不是该租户的成员，返回空列表
            if tenant_id not in user_tenant_ids:
                logging.debug(f"User {user_id} is not a member of tenant {tenant_id}, cannot get team shares")
                return []
            
            query = cls.model.select().where(
                (cls.model.tenant_id == tenant_id)
            )

            if enabled_only:
                query = query.where(cls.model.is_enabled == True)

            records = query.order_by(cls.model.updated_at.desc())

            result = []
            for record in records:
                result.append({
                    "file_id": record.file_id,
                    "permission_level": record.permission_level,
                    "is_enabled": record.is_enabled,
                    "created_by": record.created_by,
                    "created_at": record.created_at.isoformat() if record.created_at else None,
                    "updated_at": record.updated_at.isoformat() if record.updated_at else None
                })

            return result

        except Exception as e:
            logging.exception(f"Failed to get team shares for tenant {tenant_id}: {e}")
            return []

    @classmethod
    @DB.connection_context()
    def get_shared_file_ids_for_user(cls, user_id: str, user_tenant_id: str) -> List[str]:
        """
        获取共享给指定用户的所有文件/文件夹 ID 列表

        安全要求：用户必须是租户成员才能获取共享文件列表
        逻辑: 查承 team_permission_share 表中属于该用户所在租户 (user_tenant_id) 的
        已启用共享记录，排除用户自己是文件所有者的情况。

        Args:
            user_id: 当前用户 ID
            user_tenant_id: 当前用户所属的租户 ID

        Returns:
            已共享给该用户的文件 ID 列表
        """
        try:
            # Step 1: 验证用户是否属于该租户（安全修复）
            joined_tenants = TenantService.get_joined_tenants_by_user_id(user_id)
            user_tenant_ids = {tenant["tenant_id"] for tenant in joined_tenants}
            
            # 如果用户不是该租户的成员，返回空列表
            if user_tenant_id not in user_tenant_ids:
                logging.debug(f"User {user_id} is not a member of tenant {user_tenant_id}, cannot get shared files")
                return []
            
            from api.db.db_models import File as FileModel
            # 查承属于该租户的已启用共享记录，但文件的租户不是当前用户（排除自己的文件）
            # 使用显式字段选择避免 JOIN 后字段名冲突：cls.model.file_id 显式选择
            records = (
                cls.model.select(cls.model.file_id)
                .join(FileModel, on=(cls.model.file_id == FileModel.id))
                .where(
                    (cls.model.tenant_id == user_tenant_id) &
                    (cls.model.is_enabled == True) &
                    (FileModel.created_by != user_id) &
                    (FileModel.tenant_id != user_id)
                )
                .namedtuples()
            )
            # 使用 .namedtuples() 后通过属性名访问，避免字段顺序问题
            return [r.file_id for r in records]
        except Exception as e:
            logging.exception(f"Failed to get shared file ids for user {user_id}: {e}")
            return []

    @classmethod
    @DB.connection_context()
    def check_user_team_permission(
        cls,
        user_id: str,
        file_id: str,
        tenant_id: str,
        parent_folder_id: str = None
    ) -> Optional[str]:
        """
        检查用户对文件的团队共享权限

        安全要求：用户必须是租户成员才能访问团队共享的文件
        支持递归权限继承：
        1. 首先检查文件本身的团队共享权限
        2. 如果文件本身没有权限，检查是否继承父文件夹的权限
        3. 子文件自己的权限优先于继承的权限

        Args:
            user_id: 用户ID
            file_id: 文件/文件夹ID
            tenant_id: 用户所在租户ID
            parent_folder_id: 父文件夹ID（用于递归权限继承）

        Returns:
            权限级别 (view/edit/admin) 如果用户有权限，否则返回None
        """
        try:
            # Step 1: 验证用户是否属于该租户（安全修复）
            joined_tenants = TenantService.get_joined_tenants_by_user_id(user_id)
            user_tenant_ids = {tenant["tenant_id"] for tenant in joined_tenants}
            
            # 如果用户不是该租户的成员，直接返回 None
            if tenant_id not in user_tenant_ids:
                logging.debug(f"User {user_id} is not a member of tenant {tenant_id}, cannot access team-shared files")
                return None
            
            # 首先检查文件本身是否有团队共享权限
            team_share = cls.model.select().where(
                (cls.model.file_id == file_id) &
                (cls.model.tenant_id == tenant_id) &
                (cls.model.is_enabled == True)
            ).first()

            if team_share:
                return team_share.permission_level

            # 如果文件本身没有权限，检查是否继承父文件夹的权限
            if parent_folder_id:
                parent_share = cls.model.select().where(
                    (cls.model.file_id == parent_folder_id) &
                    (cls.model.tenant_id == tenant_id) &
                    (cls.model.is_enabled == True)
                ).first()

                if parent_share:
                    return parent_share.permission_level

            return None

        except Exception as e:
            logging.exception(f"Failed to check team permission for user {user_id} on file {file_id}: {e}")
            return None

    @classmethod
    @DB.connection_context()
    def get_inherited_team_permission(
        cls,
        file_id: str,
        tenant_id: str,
        max_depth: int = 10
    ) -> Optional[str]:
        """
        获取文件继承的团队共享权限（递归查找父文件夹）

        从文件开始向上查找父文件夹链，直到找到启用的团队共享权限。

        Args:
            file_id: 文件/文件夹ID
            tenant_id: 租户ID
            max_depth: 最大递归深度，防止无限循环

        Returns:
            继承的权限级别，如果没有返回None
        """
        try:
            current_file_id = file_id
            depth = 0

            while current_file_id and depth < max_depth:
                # 检查当前文件的团队共享权限
                team_share = cls.model.select().where(
                    (cls.model.file_id == current_file_id) &
                    (cls.model.tenant_id == tenant_id) &
                    (cls.model.is_enabled == True)
                ).first()

                if team_share:
                    return team_share.permission_level

                # 获取父文件夹
                e, file = FileService.get_by_id(current_file_id)
                if not e or not file or not file.parent_id:
                    break

                current_file_id = file.parent_id
                depth += 1

            return None

        except Exception as e:
            logging.exception(f"Failed to get inherited team permission for file {file_id}: {e}")
            return None

    # ============ 批量操作方法 ============

    @classmethod
    @DB.connection_context()
    def batch_enable_team_share(
        cls,
        file_ids: List[str],
        tenant_id: str,
        user_id: str,
        permission_level: str = "view"
    ) -> Dict[str, Any]:
        """
        批量启用团队共享

        Args:
            file_ids: 文件ID列表
            tenant_id: 租户ID
            user_id: 操作者用户ID
            permission_level: 权限级别 (view/edit/admin)

        Returns:
            {"success_count": int, "failed_count": int, "failed_items": list}
        """
        results = {
            "success_count": 0,
            "failed_count": 0,
            "failed_items": []
        }

        for file_id in file_ids:
            try:
                # 检查文件是否存在
                e, file = FileService.get_by_id(file_id)
                if not e or not file:
                    results["failed_count"] += 1
                    results["failed_items"].append({
                        "file_id": file_id,
                        "error": "文件不存在"
                    })
                    continue

                # 检查是否已存在团队共享记录
                existing = cls.model.select().where(
                    (cls.model.file_id == file_id) &
                    (cls.model.tenant_id == tenant_id)
                ).first()

                if existing:
                    # 更新现有记录
                    existing.permission_level = permission_level
                    existing.is_enabled = True
                    existing.updated_at = datetime.now()
                    existing.save()
                else:
                    # 创建新记录
                    cls.model.create(
                        id=get_uuid(),
                        file_id=file_id,
                        tenant_id=tenant_id,
                        permission_level=permission_level,
                        is_enabled=True,
                        created_by=user_id,
                        created_at=datetime.now(),
                        updated_at=datetime.now()
                    )

                results["success_count"] += 1

            except Exception as e:
                results["failed_count"] += 1
                results["failed_items"].append({
                    "file_id": file_id,
                    "error": str(e)
                })
                logging.exception(f"Failed to enable team share for file {file_id}: {e}")

        return results

    @classmethod
    @DB.connection_context()
    def batch_disable_team_share(
        cls,
        file_ids: List[str],
        tenant_id: str
    ) -> Dict[str, Any]:
        """
        批量禁用团队共享

        Args:
            file_ids: 文件ID列表
            tenant_id: 租户ID

        Returns:
            {"success_count": int, "failed_count": int, "failed_items": list}
        """
        results = {
            "success_count": 0,
            "failed_count": 0,
            "failed_items": []
        }

        for file_id in file_ids:
            try:
                # 查找现有记录
                existing = cls.model.select().where(
                    (cls.model.file_id == file_id) &
                    (cls.model.tenant_id == tenant_id)
                ).first()

                if not existing:
                    results["failed_count"] += 1
                    results["failed_items"].append({
                        "file_id": file_id,
                        "error": "团队共享记录不存在"
                    })
                    continue

                # 更新为禁用状态
                existing.is_enabled = False
                existing.updated_at = datetime.now()
                existing.save()

                results["success_count"] += 1

            except Exception as e:
                results["failed_count"] += 1
                results["failed_items"].append({
                    "file_id": file_id,
                    "error": str(e)
                })
                logging.exception(f"Failed to disable team share for file {file_id}: {e}")

        return results

    @classmethod
    @DB.connection_context()
    def batch_update_permission_level(
        cls,
        file_ids: List[str],
        tenant_id: str,
        permission_level: str
    ) -> Dict[str, Any]:
        """
        批量更新权限级别

        Args:
            file_ids: 文件ID列表
            tenant_id: 租户ID
            permission_level: 新的权限级别

        Returns:
            {"success_count": int, "failed_count": int, "failed_items": list}
        """
        results = {
            "success_count": 0,
            "failed_count": 0,
            "failed_items": []
        }

        for file_id in file_ids:
            try:
                # 查找现有记录
                existing = cls.model.select().where(
                    (cls.model.file_id == file_id) &
                    (cls.model.tenant_id == tenant_id)
                ).first()

                if not existing or not existing.is_enabled:
                    results["failed_count"] += 1
                    results["failed_items"].append({
                        "file_id": file_id,
                        "error": "团队共享未启用或记录不存在"
                    })
                    continue

                # 更新权限级别
                existing.permission_level = permission_level
                existing.updated_at = datetime.now()
                existing.save()

                results["success_count"] += 1

            except Exception as e:
                results["failed_count"] += 1
                results["failed_items"].append({
                    "file_id": file_id,
                    "error": str(e)
                })
                logging.exception(f"Failed to update team share level for file {file_id}: {e}")

        return results

    # ============ 审计日志方法 ============

    @classmethod
    @DB.connection_context()
    def log_team_share_operation(
        cls,
        action: str,
        file_id: str,
        tenant_id: str,
        user_id: str,
        old_value: str = None,
        new_value: str = None
    ) -> bool:
        """
        记录团队共享操作日志

        Args:
            action: 操作类型 (enable/disable/update)
            file_id: 文件ID
            tenant_id: 租户ID
            user_id: 操作用户ID
            old_value: 旧值（可选）
            new_value: 新值（可选）

        Returns:
            True if logged successfully
        """
        try:
            # 使用数据库表记录日志（如果存在）
            # 或者使用简单的日志记录
            logging.info(
                f"Team share operation: action={action}, file_id={file_id}, "
                f"tenant_id={tenant_id}, user_id={user_id}, "
                f"old_value={old_value}, new_value={new_value}"
            )
            return True

        except Exception as e:
            logging.exception(f"Failed to log team share operation: {e}")
            return False

    @classmethod
    @DB.connection_context()
    def get_audit_logs(
        cls,
        tenant_id: str,
        file_id: str = None,
        start_date: datetime = None,
        end_date: datetime = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        获取团队共享审计日志

        Args:
            tenant_id: 租户ID
            file_id: 文件ID（可选，用于过滤）
            start_date: 开始日期（可选）
            end_date: 结束日期（可选）
            limit: 返回记录数量限制

        Returns:
            审计日志列表
        """
        try:
            # 如果有审计日志表，从数据库查询
            # 否则返回空列表（可以后续扩展）
            # 这里提供一个可扩展的接口
            return []

        except Exception as e:
            logging.exception(f"Failed to get audit logs: {e}")
            return []