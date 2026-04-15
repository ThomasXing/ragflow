#
#  Copyright 2026 The InfiniFlow Authors. All Rights Reserved.
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
FilePermissionService 单元测试

测试覆盖：
- 创建共享权限
- 批量创建共享
- 获取文件权限列表
- 获取用户有效权限（含继承）
- 权限继承机制
- 更新权限
- 撤销权限
- 过期权限处理
"""

import importlib.util
import sys
import types
import warnings

import pytest

# Suppress pkg_resources deprecation warning
warnings.filterwarnings(
    "ignore",
    message="pkg_resources is deprecated as an API.*",
    category=UserWarning,
)


def _install_stubs():
    """Install module stubs to avoid heavy dependencies in tests"""

    # xgboost stub
    if "xgboost" not in sys.modules:
        if importlib.util.find_spec("xgboost") is None:
            xgb_stub = types.ModuleType("xgboost")
            sys.modules["xgboost"] = xgb_stub

    # cv2 stub
    try:
        importlib.import_module("cv2")
    except Exception:
        cv2_stub = types.ModuleType("cv2")
        cv2_stub.INTER_LINEAR = 1
        cv2_stub.INTER_CUBIC = 2
        cv2_stub.BORDER_CONSTANT = 0
        cv2_stub.BORDER_REPLICATE = 1
        sys.modules["cv2"] = cv2_stub


_install_stubs()

from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock


class TestFilePermissionServiceCreateShare:
    """测试创建共享权限"""

    @pytest.mark.p1
    def test_create_share_success(self, mock_db, mock_file_service):
        """
        US-001: 创建共享 - 成功场景
        Given: 文件存在，用户有 admin 权限
        When: 创建共享给目标用户
        Then: 返回共享记录
        """
        from api.db.services.file_permission_service import FilePermissionService
        from api.db import FilePermissionLevel

        # Arrange
        file_id = "file_001"
        target_user_id = "user_002"
        sharer_id = "user_001"
        permission_level = FilePermissionLevel.VIEW
        tenant_id = "tenant_001"

        # Act
        result = FilePermissionService.create_share(
            file_id=file_id,
            target_user_id=target_user_id,
            sharer_id=sharer_id,
            permission_level=permission_level,
            tenant_id=tenant_id
        )

        # Assert
        assert result is not None
        assert result.file_id == file_id
        assert result.target_user_id == target_user_id
        assert result.permission_level == permission_level
        assert result.status == "1"

    @pytest.mark.p1
    def test_create_share_update_existing(self, mock_db):
        """
        US-001: 重复共享 - 更新权限
        Given: 用户已有共享权限
        When: 再次共享给同一用户
        Then: 更新权限而非创建新记录
        """
        from api.db.services.file_permission_service import FilePermissionService
        from api.db import FilePermissionLevel

        # Arrange - 先创建一个共享
        file_id = "file_001"
        target_user_id = "user_002"

        FilePermissionService.create_share(
            file_id=file_id,
            target_user_id=target_user_id,
            sharer_id="user_001",
            permission_level=FilePermissionLevel.VIEW,
            tenant_id="tenant_001"
        )

        # Act - 更新权限
        result = FilePermissionService.create_share(
            file_id=file_id,
            target_user_id=target_user_id,
            sharer_id="user_001",
            permission_level=FilePermissionLevel.EDIT,
            tenant_id="tenant_001"
        )

        # Assert - 权限被更新
        assert result.permission_level == FilePermissionLevel.EDIT

        # Assert - 只有一条记录
        permissions = FilePermissionService.get_file_permissions(file_id)
        view_perms = [p for p in permissions if p["target_user_id"] == target_user_id]
        assert len(view_perms) == 1

    @pytest.mark.p2
    def test_create_share_with_expiry(self, mock_db):
        """
        US-001: 创建共享 - 带过期时间
        Given: 设置过期时间
        When: 创建共享
        Then: 共享记录包含过期时间
        """
        from api.db.services.file_permission_service import FilePermissionService
        from api.db import FilePermissionLevel

        # Arrange
        expires_at = datetime.now() + timedelta(days=7)

        # Act
        result = FilePermissionService.create_share(
            file_id="file_001",
            target_user_id="user_002",
            sharer_id="user_001",
            permission_level=FilePermissionLevel.VIEW,
            tenant_id="tenant_001",
            expires_at=expires_at
        )

        # Assert
        assert result.expires_at is not None
        assert result.expires_at.date() == expires_at.date()


class TestFilePermissionServiceGetEffectivePermission:
    """测试获取有效权限"""

    @pytest.mark.p1
    def test_get_effective_permission_owner(self, mock_db, mock_file_service):
        """
        TC-101: 所有者权限
        Given: 用户是文件创建者
        When: 检查权限
        Then: 返回 OWNER 权限
        """
        from api.db.services.file_permission_service import FilePermissionService
        from api.db import FilePermissionLevel

        # Arrange - 文件由 user_001 创建
        file_id = "file_001"
        user_id = "user_001"  # 所有者

        # Act
        permission = FilePermissionService.get_user_effective_permission(file_id, user_id)

        # Assert
        assert permission == FilePermissionLevel.OWNER

    @pytest.mark.p1
    def test_get_effective_permission_explicit(self, mock_db, mock_file_service):
        """
        TC-101: 显式权限
        Given: 用户被显式授予 EDIT 权限
        When: 检查权限
        Then: 返回 EDIT 权限
        """
        from api.db.services.file_permission_service import FilePermissionService
        from api.db import FilePermissionLevel

        # Arrange
        file_id = "file_001"
        user_id = "user_002"

        # 先创建共享
        FilePermissionService.create_share(
            file_id=file_id,
            target_user_id=user_id,
            sharer_id="user_001",
            permission_level=FilePermissionLevel.EDIT,
            tenant_id="tenant_001"
        )

        # Act
        permission = FilePermissionService.get_user_effective_permission(file_id, user_id)

        # Assert
        assert permission == FilePermissionLevel.EDIT

    @pytest.mark.p1
    def test_get_effective_permission_inherited(self, mock_db, mock_file_service_with_hierarchy):
        """
        TC-110: 权限继承
        Given: 父文件夹被共享给用户
        When: 检查子文件权限
        Then: 返回继承的权限
        """
        from api.db.services.file_permission_service import FilePermissionService
        from api.db import FilePermissionLevel

        # Arrange - 文件夹层级: root_folder -> sub_folder -> file
        # root_folder 被共享给 user_002，权限为 ADMIN
        root_folder_id = "folder_001"
        sub_folder_id = "folder_002"  # parent_id = folder_001
        file_id = "file_in_subfolder"  # parent_id = folder_002
        user_id = "user_002"

        # 共享根文件夹给用户
        FilePermissionService.create_share(
            file_id=root_folder_id,
            target_user_id=user_id,
            sharer_id="user_001",
            permission_level=FilePermissionLevel.ADMIN,
            tenant_id="tenant_001"
        )

        # Act - 检查子文件权限
        permission = FilePermissionService.get_user_effective_permission(file_id, user_id)

        # Assert - 继承父文件夹权限
        assert permission == FilePermissionLevel.ADMIN

    @pytest.mark.p2
    def test_get_effective_permission_expired(self, mock_db, mock_file_service):
        """
        TC-201: 过期权限
        Given: 共享已过期
        When: 检查权限
        Then: 返回 None（无权限）
        """
        from api.db.services.file_permission_service import FilePermissionService
        from api.db import FilePermissionLevel

        # Arrange - 创建一个已过期的共享
        file_id = "file_001"
        user_id = "user_002"
        expired_time = datetime.now() - timedelta(days=1)  # 昨天过期

        FilePermissionService.create_share(
            file_id=file_id,
            target_user_id=user_id,
            sharer_id="user_001",
            permission_level=FilePermissionLevel.VIEW,
            tenant_id="tenant_001",
            expires_at=expired_time
        )

        # Act
        permission = FilePermissionService.get_user_effective_permission(file_id, user_id)

        # Assert
        assert permission is None


class TestFilePermissionServiceRevokePermission:
    """测试撤销权限"""

    @pytest.mark.p1
    def test_revoke_permission_success(self, mock_db):
        """
        US-003: 撤销共享
        Given: 存在共享权限
        When: 撤销权限
        Then: 权限状态变为无效
        """
        from api.db.services.file_permission_service import FilePermissionService
        from api.db import FilePermissionLevel

        # Arrange
        share = FilePermissionService.create_share(
            file_id="file_001",
            target_user_id="user_002",
            sharer_id="user_001",
            permission_level=FilePermissionLevel.VIEW,
            tenant_id="tenant_001"
        )

        # Act
        result = FilePermissionService.revoke_permission(share.id)

        # Assert
        assert result is True

        # Verify - 权限已被撤销
        permissions = FilePermissionService.get_file_permissions("file_001")
        active_perms = [p for p in permissions if p["target_user_id"] == "user_002"]
        assert len(active_perms) == 0

    @pytest.mark.p2
    def test_revoke_all_permissions_for_file(self, mock_db):
        """
        撤销文件的所有共享权限
        """
        from api.db.services.file_permission_service import FilePermissionService
        from api.db import FilePermissionLevel

        # Arrange - 创建多个共享
        file_id = "file_001"
        FilePermissionService.create_share(
            file_id=file_id, target_user_id="user_002",
            sharer_id="user_001", permission_level=FilePermissionLevel.VIEW,
            tenant_id="tenant_001"
        )
        FilePermissionService.create_share(
            file_id=file_id, target_user_id="user_003",
            sharer_id="user_001", permission_level=FilePermissionLevel.EDIT,
            tenant_id="tenant_001"
        )

        # Act
        count = FilePermissionService.revoke_all_permissions(file_id)

        # Assert
        assert count == 2
        permissions = FilePermissionService.get_file_permissions(file_id)
        assert len(permissions) == 0


class TestFilePermissionServiceBatchShare:
    """测试批量共享"""

    @pytest.mark.p2
    def test_batch_create_shares_success(self, mock_db, mock_file_service):
        """
        US-001: 批量共享 - 成功场景
        Given: 多个文件和多个用户
        When: 批量创建共享
        Then: 返回成功和失败列表
        """
        from api.db.services.file_permission_service import FilePermissionService
        from api.db import FilePermissionLevel

        # Arrange
        shares = [
            {
                "file_id": "file_001",
                "target_user_id": "user_002",
                "sharer_id": "user_001",
                "permission_level": FilePermissionLevel.VIEW,
                "tenant_id": "tenant_001"
            },
            {
                "file_id": "file_002",
                "target_user_id": "user_002",
                "sharer_id": "user_001",
                "permission_level": FilePermissionLevel.EDIT,
                "tenant_id": "tenant_001"
            }
        ]

        # Act
        success, failed = FilePermissionService.batch_create_shares(shares)

        # Assert
        assert len(success) == 2
        assert len(failed) == 0

    @pytest.mark.p2
    def test_batch_create_shares_partial_failure(self, mock_db):
        """
        批量共享 - 部分失败
        Given: 部分文件不存在
        When: 批量创建共享
        Then: 返回部分成功和失败列表
        """
        from api.db.services.file_permission_service import FilePermissionService
        from api.db import FilePermissionLevel

        # Arrange
        shares = [
            {
                "file_id": "file_001",
                "target_user_id": "user_002",
                "sharer_id": "user_001",
                "permission_level": FilePermissionLevel.VIEW,
                "tenant_id": "tenant_001"
            },
            {
                "file_id": "non_existent_file",  # 不存在的文件
                "target_user_id": "user_002",
                "sharer_id": "user_001",
                "permission_level": FilePermissionLevel.VIEW,
                "tenant_id": "tenant_001"
            }
        ]

        # Act
        success, failed = FilePermissionService.batch_create_shares(shares)

        # Assert
        assert len(success) >= 1
        assert any(f["file_id"] == "non_existent_file" for f in failed)


class TestFilePermissionServiceCanShareToUser:
    """测试共享权限检查"""

    @pytest.mark.p1
    def test_cannot_share_to_owner(self, mock_file_service):
        """
        TC-003: 不能共享给文件所有者
        Given: 目标用户是文件所有者
        When: 尝试共享
        Then: 返回 False
        """
        from api.db.services.file_permission_service import FilePermissionService

        # Arrange - file_001 的所有者是 user_001
        file_id = "file_001"
        owner_id = "user_001"
        tenant_id = "tenant_001"

        # Act
        can_share, msg = FilePermissionService.can_share_to_user(
            file_id, owner_id, tenant_id
        )

        # Assert
        assert can_share is False
        assert "所有者" in msg or "owner" in msg.lower()

    @pytest.mark.p1
    def test_cannot_share_to_different_tenant(self, mock_file_service):
        """
        TC-004: 不能共享给其他租户用户
        Given: 目标用户不在同一租户
        When: 尝试共享
        Then: 返回 False
        """
        from api.db.services.file_permission_service import FilePermissionService

        # Arrange
        file_id = "file_001"  # tenant_001
        target_user_id = "user_other_tenant"  # 不在 tenant_001
        tenant_id = "tenant_001"

        # Act
        can_share, msg = FilePermissionService.can_share_to_user(
            file_id, target_user_id, tenant_id
        )

        # Assert
        assert can_share is False
        assert "租户" in msg or "tenant" in msg.lower()


class TestFilePermissionServiceGetInheritedPermissions:
    """测试获取继承权限"""

    @pytest.mark.p1
    def test_get_inherited_permissions_chain(self, mock_file_service_with_hierarchy):
        """
        TC-110: 权限继承链
        Given: 三层文件夹层级，每层都有权限
        When: 获取继承权限
        Then: 返回所有继承的权限
        """
        from api.db.services.file_permission_service import FilePermissionService
        from api.db import FilePermissionLevel

        # Arrange
        # root (ADMIN) -> folder1 (EDIT) -> folder2 -> file
        root_id = "folder_001"
        folder1_id = "folder_002"
        file_id = "file_in_subfolder"
        user_id = "user_002"

        # 共享根文件夹
        FilePermissionService.create_share(
            file_id=root_id,
            target_user_id=user_id,
            sharer_id="user_001",
            permission_level=FilePermissionLevel.ADMIN,
            tenant_id="tenant_001"
        )

        # 共享子文件夹
        FilePermissionService.create_share(
            file_id=folder1_id,
            target_user_id=user_id,
            sharer_id="user_001",
            permission_level=FilePermissionLevel.EDIT,
            tenant_id="tenant_001"
        )

        # Act
        inherited = FilePermissionService.get_inherited_permissions(file_id, user_id)

        # Assert - 应该返回两个继承权限
        assert len(inherited) == 2
        permission_levels = [p["permission_level"] for p in inherited]
        assert FilePermissionLevel.ADMIN in permission_levels
        assert FilePermissionLevel.EDIT in permission_levels


# ============== Fixtures ==============

@pytest.fixture
def mock_db():
    """Mock 数据库连接"""
    with patch('api.db.db_models.DB') as mock:
        mock.connection_context = MagicMock(return_value=MagicMock())
        mock.connection_context.return_value.__enter__ = MagicMock(return_value=None)
        mock.connection_context.return_value.__exit__ = MagicMock(return_value=None)
        yield mock


@pytest.fixture
def mock_file_service():
    """Mock FileService，创建基础文件数据"""
    mock_files = {
        "file_001": {
            "id": "file_001",
            "name": "test_file.txt",
            "type": "doc",
            "created_by": "user_001",
            "tenant_id": "tenant_001",
            "parent_id": "root"
        },
        "file_002": {
            "id": "file_002",
            "name": "test_file2.txt",
            "type": "doc",
            "created_by": "user_001",
            "tenant_id": "tenant_001",
            "parent_id": "root"
        }
    }

    def mock_get_by_id(file_id):
        if file_id in mock_files:
            mock_file = MagicMock()
            mock_file.id = mock_files[file_id]["id"]
            mock_file.name = mock_files[file_id]["name"]
            mock_file.type = mock_files[file_id]["type"]
            mock_file.created_by = mock_files[file_id]["created_by"]
            mock_file.tenant_id = mock_files[file_id]["tenant_id"]
            mock_file.parent_id = mock_files[file_id]["parent_id"]
            return True, mock_file
        return False, None

    with patch('api.db.services.file_service.FileService.get_by_id', side_effect=mock_get_by_id):
        yield mock_files


@pytest.fixture
def mock_file_service_with_hierarchy():
    """Mock FileService，创建文件夹层级结构"""
    mock_files = {
        "folder_001": {
            "id": "folder_001",
            "name": "root_folder",
            "type": "folder",
            "created_by": "user_001",
            "tenant_id": "tenant_001",
            "parent_id": "folder_001"  # 根目录
        },
        "folder_002": {
            "id": "folder_002",
            "name": "sub_folder",
            "type": "folder",
            "created_by": "user_001",
            "tenant_id": "tenant_001",
            "parent_id": "folder_001"
        },
        "file_in_subfolder": {
            "id": "file_in_subfolder",
            "name": "nested_file.txt",
            "type": "doc",
            "created_by": "user_001",
            "tenant_id": "tenant_001",
            "parent_id": "folder_002"
        }
    }

    def mock_get_by_id(file_id):
        if file_id in mock_files:
            mock_file = MagicMock()
            mock_file.id = mock_files[file_id]["id"]
            mock_file.name = mock_files[file_id]["name"]
            mock_file.type = mock_files[file_id]["type"]
            mock_file.created_by = mock_files[file_id]["created_by"]
            mock_file.tenant_id = mock_files[file_id]["tenant_id"]
            mock_file.parent_id = mock_files[file_id]["parent_id"]
            return True, mock_file
        return False, None

    with patch('api.db.services.file_service.FileService.get_by_id', side_effect=mock_get_by_id):
        yield mock_files
