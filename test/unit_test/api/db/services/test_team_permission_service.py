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
TeamPermissionService 单元测试

测试覆盖：
- 启用团队共享
- 禁用团队共享
- 获取团队共享状态
- 更新团队共享权限级别
- 获取用户所有团队共享
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

from datetime import datetime
from unittest.mock import Mock, patch, MagicMock


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
    with patch('api.db.services.file_service.FileService') as mock:
        mock_service = MagicMock()

        # Mock get_by_id 方法
        def get_by_id(file_id):
            if file_id == "file_001":
                return (True, MagicMock(id="file_001", name="test_file.txt", tenant_id="tenant_001", created_by="user_001"))
            else:
                return (False, None)

        mock_service.get_by_id = MagicMock(side_effect=get_by_id)
        mock.return_value = mock_service

        yield mock_service


@pytest.fixture
def mock_user_service():
    """Mock UserService，创建用户数据"""
    with patch('api.db.services.user_service.UserService') as mock:
        mock_service = MagicMock()

        def get_by_id(user_id):
            if user_id in ["user_001", "user_002"]:
                user = MagicMock()
                user.id = user_id
                user.nickname = f"User {user_id}"
                user.email = f"{user_id}@example.com"
                return user
            return None

        mock_service.get_by_id = MagicMock(side_effect=get_by_id)
        mock.return_value = mock_service

        yield mock_service


@pytest.fixture
def mock_tenant_service():
    """Mock TenantService，创建租户关系数据"""
    with patch('api.db.services.user_service.TenantService') as mock:
        mock_service = MagicMock()

        def get_joined_tenants_by_user_id(user_id):
            if user_id == "user_002":
                return [{"tenant_id": "tenant_001", "role": "member", "status": "active"}]
            elif user_id == "user_001":  # 租户owner
                return [{"tenant_id": "tenant_001", "role": "owner", "status": "active"}]
            else:
                return []

        mock_service.get_joined_tenants_by_user_id = MagicMock(side_effect=get_joined_tenants_by_user_id)
        mock.return_value = mock_service

        yield mock_service


class TestTeamPermissionServiceEnableTeamShare:
    """测试启用团队共享"""

    @pytest.mark.p1
    def test_enable_team_share_success(self, mock_db, mock_file_service):
        """
        测试启用团队共享 - 成功场景
        Given: 文件存在，用户有 admin 权限
        When: 启用团队共享
        Then: 返回TeamPermissionShare对象，is_enabled=True
        """
        from api.db.services.team_permission_service import TeamPermissionService
        from api.db.db_models import TeamPermissionShare
        from common.misc_utils import get_uuid

        # Arrange
        file_id = "file_001"
        tenant_id = "tenant_001"
        user_id = "user_001"
        permission_level = "view"

        # Mock get_by_id 返回成功
        mock_file_service.get_by_id.return_value = (True, MagicMock(
            id="file_001",
            name="test_file.txt",
            tenant_id="tenant_001",
            created_by="user_001"
        ))

        # Mock 不存在现有记录
        mock_query = MagicMock()
        mock_query.where.return_value.first.return_value = None
        mock_select = MagicMock(return_value=mock_query)
        with patch.object(TeamPermissionShare, 'select', mock_select):
            # Mock create 方法
            mock_team_share = MagicMock()
            mock_team_share.id = "team_share_001"
            mock_team_share.file_id = file_id
            mock_team_share.tenant_id = tenant_id
            mock_team_share.permission_level = permission_level
            mock_team_share.is_enabled = True
            mock_team_share.created_by = user_id
            mock_team_share.created_at = datetime.now()
            mock_team_share.updated_at = datetime.now()

            # Mock get_uuid 返回固定ID
            with patch('common.misc_utils.get_uuid', return_value="team_share_001"):
                # Mock create 方法
                mock_create = MagicMock(return_value=mock_team_share)
                with patch.object(TeamPermissionShare, 'create', mock_create):
                    # Act
                    result = TeamPermissionService.enable_team_share(
                        file_id=file_id,
                        tenant_id=tenant_id,
                        user_id=user_id,
                        permission_level=permission_level
                    )

                    # Assert
                    assert result is True
                    # 验证create被调用
                    mock_create.assert_called_once()
                    call_args = mock_create.call_args[1]
                    assert call_args['file_id'] == file_id
                    assert call_args['tenant_id'] == tenant_id
                    assert call_args['permission_level'] == permission_level
                    assert call_args['is_enabled'] is True
                    assert call_args['created_by'] == user_id

    @pytest.mark.p1
    def test_enable_team_share_update_existing(self, mock_db):
        """
        测试启用团队共享 - 更新现有记录
        Given: 团队共享已存在但未启用
        When: 重新启用团队共享
        Then: 更新现有记录，返回True
        """
        # 这里会失败，因为TeamPermissionService还没实现
        from api.db.services.team_permission_service import TeamPermissionService

        # Arrange
        file_id = "file_001"
        tenant_id = "tenant_001"
        user_id = "user_001"
        permission_level = "edit"

        # Act
        result = TeamPermissionService.enable_team_share(
            file_id=file_id,
            tenant_id=tenant_id,
            user_id=user_id,
            permission_level=permission_level
        )

        # Assert
        assert result is True


class TestTeamPermissionServiceDisableTeamShare:
    """测试禁用团队共享"""

    @pytest.mark.p1
    def test_disable_team_share_success(self, mock_db):
        """
        测试禁用团队共享 - 成功场景
        Given: 团队共享已启用
        When: 禁用团队共享
        Then: 返回True，记录状态更新为未启用
        """
        # 这里会失败，因为TeamPermissionService还没实现
        from api.db.services.team_permission_service import TeamPermissionService

        # Arrange
        file_id = "file_001"
        tenant_id = "tenant_001"

        # Act
        result = TeamPermissionService.disable_team_share(
            file_id=file_id,
            tenant_id=tenant_id
        )

        # Assert
        assert result is True


class TestTeamPermissionServiceGetStatus:
    """测试获取团队共享状态"""

    @pytest.mark.p1
    def test_get_team_share_status_enabled(self, mock_db):
        """
        测试获取团队共享状态 - 已启用
        Given: 团队共享已启用
        When: 获取状态
        Then: 返回包含状态信息的字典
        """
        # 这里会失败，因为TeamPermissionService还没实现
        from api.db.services.team_permission_service import TeamPermissionService

        # Arrange
        file_id = "file_001"
        tenant_id = "tenant_001"

        # Act
        result = TeamPermissionService.get_team_share_status(
            file_id=file_id,
            tenant_id=tenant_id
        )

        # Assert
        assert result is not None
        assert result["file_id"] == file_id
        assert result["tenant_id"] == tenant_id
        assert result["is_enabled"] is True
        assert result["permission_level"] == "view"

    @pytest.mark.p1
    def test_get_team_share_status_disabled(self, mock_db):
        """
        测试获取团队共享状态 - 未启用
        Given: 团队共享未启用
        When: 获取状态
        Then: 返回None或默认状态
        """
        # 这里会失败，因为TeamPermissionService还没实现
        from api.db.services.team_permission_service import TeamPermissionService

        # Arrange
        file_id = "file_002"
        tenant_id = "tenant_001"

        # Act
        result = TeamPermissionService.get_team_share_status(
            file_id=file_id,
            tenant_id=tenant_id
        )

        # Assert
        assert result is None or result["is_enabled"] is False


class TestTeamPermissionServiceUpdateLevel:
    """测试更新团队共享权限级别"""

    @pytest.mark.p1
    def test_update_team_share_level_success(self, mock_db):
        """
        测试更新团队共享权限级别 - 成功场景
        Given: 团队共享已启用
        When: 更新权限级别
        Then: 返回True，权限级别更新
        """
        # 这里会失败，因为TeamPermissionService还没实现
        from api.db.services.team_permission_service import TeamPermissionService

        # Arrange
        file_id = "file_001"
        tenant_id = "tenant_001"
        new_level = "edit"

        # Act
        result = TeamPermissionService.update_team_share_level(
            file_id=file_id,
            tenant_id=tenant_id,
            permission_level=new_level
        )

        # Assert
        assert result is True


if __name__ == "__main__":
    # 运行测试
    pytest.main([__file__, "-v"])