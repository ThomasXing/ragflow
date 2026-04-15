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
权限检查模块单元测试

测试覆盖：
- 权限级别验证
- 操作权限检查
- 权限继承处理
"""

import pytest
from unittest.mock import Mock, patch, MagicMock


class TestCheckFilePermission:
    """测试权限级别检查"""

    @pytest.mark.p1
    def test_check_permission_view_success(self, mock_permission_service):
        """
        TC-101: 查看文件 - VIEW 权限
        Given: 用户有 VIEW 权限
        When: 检查查看权限
        Then: 返回 True
        """
        from api.common.check_file_permission import check_file_permission
        from api.db import FilePermissionLevel

        # Arrange
        file_id = "file_001"
        user_id = "user_002"
        required_level = FilePermissionLevel.VIEW

        # Act
        has_permission, msg = check_file_permission(file_id, user_id, required_level)

        # Assert
        assert has_permission is True
        assert msg == ""

    @pytest.mark.p1
    def test_check_permission_edit_denied_for_view_only(self, mock_permission_service_view_only):
        """
        TC-103: 编辑文件 - VIEW 权限不足
        Given: 用户只有 VIEW 权限
        When: 检查编辑权限
        Then: 返回 False
        """
        from api.common.check_file_permission import check_file_permission
        from api.db import FilePermissionLevel

        # Arrange
        file_id = "file_001"
        user_id = "user_002"
        required_level = FilePermissionLevel.EDIT

        # Act
        has_permission, msg = check_file_permission(file_id, user_id, required_level)

        # Assert
        assert has_permission is False
        assert "权限不足" in msg or "permission" in msg.lower()

    @pytest.mark.p1
    def test_check_permission_owner_has_all(self, mock_permission_service_owner):
        """
        TC-107: OWNER 权限可以执行所有操作
        Given: 用户是 OWNER
        When: 检查任何操作权限
        Then: 返回 True
        """
        from api.common.check_file_permission import check_file_permission
        from api.db import FilePermissionLevel

        # Arrange
        file_id = "file_001"
        user_id = "user_001"  # owner

        # Act & Assert - OWNER 应该有所有权限
        for level in [FilePermissionLevel.VIEW, FilePermissionLevel.EDIT,
                      FilePermissionLevel.ADMIN, FilePermissionLevel.OWNER]:
            has_permission, msg = check_file_permission(file_id, user_id, level)
            assert has_permission is True, f"OWNER should have {level} permission"


class TestCheckFileOperationPermission:
    """测试操作权限检查"""

    @pytest.mark.p1
    def test_operation_view_requires_view(self, mock_permission_service_view_only):
        """
        TC-101: 查看操作需要 VIEW 权限
        """
        from api.common.check_file_permission import check_file_operation_permission

        # Arrange
        file_id = "file_001"
        user_id = "user_002"  # has VIEW permission

        # Act
        has_permission, msg = check_file_operation_permission(file_id, user_id, "view")

        # Assert
        assert has_permission is True

    @pytest.mark.p1
    def test_operation_download_requires_view(self, mock_permission_service_view_only):
        """
        TC-102: 下载操作需要 VIEW 权限
        """
        from api.common.check_file_permission import check_file_operation_permission

        # Arrange
        file_id = "file_001"
        user_id = "user_002"  # has VIEW permission

        # Act
        has_permission, msg = check_file_operation_permission(file_id, user_id, "download")

        # Assert
        assert has_permission is True

    @pytest.mark.p1
    def test_operation_edit_requires_edit(self, mock_permission_service_view_only):
        """
        TC-103: 编辑操作需要 EDIT 权限 - VIEW 不足
        """
        from api.common.check_file_permission import check_file_operation_permission

        # Arrange
        file_id = "file_001"
        user_id = "user_002"  # has VIEW permission only

        # Act
        has_permission, msg = check_file_operation_permission(file_id, user_id, "edit")

        # Assert
        assert has_permission is False

    @pytest.mark.p1
    def test_operation_upload_requires_edit(self, mock_permission_service_edit):
        """
        TC-105: 上传操作需要 EDIT 权限
        """
        from api.common.check_file_permission import check_file_operation_permission

        # Arrange
        file_id = "folder_001"
        user_id = "user_002"  # has EDIT permission

        # Act
        has_permission, msg = check_file_operation_permission(file_id, user_id, "upload")

        # Assert
        assert has_permission is True

    @pytest.mark.p1
    def test_operation_delete_requires_admin(self, mock_permission_service_edit):
        """
        TC-106: 删除操作需要 ADMIN 权限 - EDIT 不足
        """
        from api.common.check_file_permission import check_file_operation_permission

        # Arrange
        file_id = "file_001"
        user_id = "user_002"  # has EDIT permission only

        # Act
        has_permission, msg = check_file_operation_permission(file_id, user_id, "delete")

        # Assert
        assert has_permission is False

    @pytest.mark.p1
    def test_operation_share_requires_admin(self, mock_permission_service_admin):
        """
        TC-108: 分享操作需要 ADMIN 权限
        """
        from api.common.check_file_permission import check_file_operation_permission

        # Arrange
        file_id = "file_001"
        user_id = "user_002"  # has ADMIN permission

        # Act
        has_permission, msg = check_file_operation_permission(file_id, user_id, "share")

        # Assert
        assert has_permission is True

    @pytest.mark.p1
    def test_operation_transfer_ownership_requires_owner(self, mock_permission_service_admin):
        """
        TC-109: 转让所有权需要 OWNER 权限 - ADMIN 不足
        """
        from api.common.check_file_permission import check_file_operation_permission

        # Arrange
        file_id = "file_001"
        user_id = "user_002"  # has ADMIN permission only

        # Act
        has_permission, msg = check_file_operation_permission(file_id, user_id, "transfer_ownership")

        # Assert
        assert has_permission is False


class TestCanUserShareFile:
    """测试分享权限检查"""

    @pytest.mark.p1
    def test_can_share_with_admin(self, mock_permission_service_admin):
        """
        ADMIN 权限可以分享文件
        """
        from api.common.check_file_permission import can_user_share_file

        # Arrange
        file_id = "file_001"
        user_id = "user_002"  # has ADMIN permission

        # Act
        can_share, msg = can_user_share_file(file_id, user_id)

        # Assert
        assert can_share is True

    @pytest.mark.p1
    def test_cannot_share_with_view_only(self, mock_permission_service_view_only):
        """
        VIEW 权限不能分享文件
        """
        from api.common.check_file_permission import can_user_share_file

        # Arrange
        file_id = "file_001"
        user_id = "user_002"  # has VIEW permission only

        # Act
        can_share, msg = can_user_share_file(file_id, user_id)

        # Assert
        assert can_share is False


class TestCanUserManagePermissions:
    """测试权限管理检查"""

    @pytest.mark.p1
    def test_admin_can_manage_view_permission(self, mock_permission_service_admin):
        """
        ADMIN 可以管理 VIEW 权限
        """
        from api.common.check_file_permission import can_user_manage_permissions
        from api.db import FilePermissionLevel

        # Arrange
        file_id = "file_001"
        user_id = "user_002"  # has ADMIN permission

        # Act
        can_manage, msg = can_user_manage_permissions(
            file_id, user_id, FilePermissionLevel.VIEW
        )

        # Assert
        assert can_manage is True

    @pytest.mark.p1
    def test_admin_cannot_set_admin_permission(self, mock_permission_service_admin):
        """
        TC-109: ADMIN 不能设置 ADMIN 权限（只有 OWNER 可以）
        """
        from api.common.check_file_permission import can_user_manage_permissions
        from api.db import FilePermissionLevel

        # Arrange
        file_id = "file_001"
        user_id = "user_002"  # has ADMIN permission

        # Act
        can_manage, msg = can_user_manage_permissions(
            file_id, user_id, FilePermissionLevel.ADMIN
        )

        # Assert
        assert can_manage is False
        assert "所有者" in msg or "owner" in msg.lower()

    @pytest.mark.p1
    def test_owner_can_set_any_permission(self, mock_permission_service_owner):
        """
        OWNER 可以设置任何权限级别
        """
        from api.common.check_file_permission import can_user_manage_permissions
        from api.db import FilePermissionLevel

        # Arrange
        file_id = "file_001"
        user_id = "user_001"  # owner

        # Act & Assert
        for level in [FilePermissionLevel.VIEW, FilePermissionLevel.EDIT,
                      FilePermissionLevel.ADMIN]:
            can_manage, msg = can_user_manage_permissions(file_id, user_id, level)
            assert can_manage is True, f"OWNER should be able to set {level}"


class TestGetPermissionInfo:
    """测试获取权限详情"""

    @pytest.mark.p1
    def test_get_permission_info_owner(self, mock_permission_service_owner):
        """
        获取所有者权限信息
        """
        from api.common.check_file_permission import get_permission_info
        from api.db import FilePermissionLevel

        # Arrange
        file_id = "file_001"
        user_id = "user_001"  # owner

        # Act
        info = get_permission_info(file_id, user_id)

        # Assert
        assert info["is_owner"] is True
        assert info["permission_level"] == FilePermissionLevel.OWNER
        assert info["permission_source"] == "owner"

    @pytest.mark.p1
    def test_get_permission_info_explicit(self, mock_permission_service_edit):
        """
        获取显式权限信息
        """
        from api.common.check_file_permission import get_permission_info
        from api.db import FilePermissionLevel

        # Arrange
        file_id = "file_001"
        user_id = "user_002"  # has explicit EDIT permission

        # Act
        info = get_permission_info(file_id, user_id)

        # Assert
        assert info["is_owner"] is False
        assert info["permission_level"] == FilePermissionLevel.EDIT
        assert info["permission_source"] == "explicit"

    @pytest.mark.p1
    def test_get_permission_info_inherited(self, mock_permission_service_inherited):
        """
        TC-110: 获取继承权限信息
        """
        from api.common.check_file_permission import get_permission_info
        from api.db import FilePermissionLevel

        # Arrange
        file_id = "file_nested"  # nested file
        user_id = "user_002"

        # Act
        info = get_permission_info(file_id, user_id)

        # Assert
        assert info["is_owner"] is False
        assert info["permission_level"] == FilePermissionLevel.ADMIN
        assert info["permission_source"] == "inherited"
        assert len(info["inherited_from"]) > 0


class TestCheckFilesPermission:
    """测试批量权限检查"""

    @pytest.mark.p2
    def test_check_files_permission_batch(self, mock_permission_service_mixed):
        """
        批量检查多个文件的权限
        """
        from api.common.check_file_permission import check_files_permission
        from api.db import FilePermissionLevel

        # Arrange
        file_ids = ["file_001", "file_002", "file_003", "file_no_access"]
        user_id = "user_002"
        required_level = FilePermissionLevel.VIEW

        # Act
        allowed, denied = check_files_permission(file_ids, user_id, required_level)

        # Assert
        assert "file_001" in allowed
        assert "file_002" in allowed
        assert "file_no_access" in denied


# ============== Fixtures ==============

@pytest.fixture
def mock_permission_service():
    """Mock FilePermissionService - 默认返回 EDIT 权限"""
    def mock_effective_permission(file_id, user_id):
        from api.db import FilePermissionLevel
        return FilePermissionLevel.EDIT

    with patch('api.common.check_file_permission.FilePermissionService.get_user_effective_permission',
               side_effect=mock_effective_permission):
        yield


@pytest.fixture
def mock_permission_service_view_only():
    """Mock FilePermissionService - 只有 VIEW 权限"""
    def mock_effective_permission(file_id, user_id):
        from api.db import FilePermissionLevel
        return FilePermissionLevel.VIEW

    with patch('api.common.check_file_permission.FilePermissionService.get_user_effective_permission',
               side_effect=mock_effective_permission):
        yield


@pytest.fixture
def mock_permission_service_edit():
    """Mock FilePermissionService - EDIT 权限"""
    def mock_effective_permission(file_id, user_id):
        from api.db import FilePermissionLevel
        return FilePermissionLevel.EDIT

    with patch('api.common.check_file_permission.FilePermissionService.get_user_effective_permission',
               side_effect=mock_effective_permission):
        yield


@pytest.fixture
def mock_permission_service_admin():
    """Mock FilePermissionService - ADMIN 权限"""
    def mock_effective_permission(file_id, user_id):
        from api.db import FilePermissionLevel
        return FilePermissionLevel.ADMIN

    with patch('api.common.check_file_permission.FilePermissionService.get_user_effective_permission',
               side_effect=mock_effective_permission):
        yield


@pytest.fixture
def mock_permission_service_owner():
    """Mock FilePermissionService - OWNER 权限"""
    def mock_effective_permission(file_id, user_id):
        from api.db import FilePermissionLevel
        return FilePermissionLevel.OWNER

    with patch('api.common.check_file_permission.FilePermissionService.get_user_effective_permission',
               side_effect=mock_effective_permission):
        yield


@pytest.fixture
def mock_permission_service_inherited():
    """Mock FilePermissionService - 继承权限"""
    from api.db import FilePermissionLevel

    def mock_effective_permission(file_id, user_id):
        return FilePermissionLevel.ADMIN

    def mock_inherited_permissions(file_id, user_id):
        return [
            {"file_id": "parent_folder", "file_name": "Parent Folder", "permission_level": FilePermissionLevel.ADMIN}
        ]

    with patch('api.common.check_file_permission.FilePermissionService.get_user_effective_permission',
               side_effect=mock_effective_permission), \
         patch('api.common.check_file_permission.FilePermissionService.get_inherited_permissions',
               side_effect=mock_inherited_permissions), \
         patch('api.common.check_file_permission.FilePermissionService.get_user_permission',
               return_value=None):
        yield


@pytest.fixture
def mock_permission_service_mixed():
    """Mock FilePermissionService - 混合权限场景"""
    from api.db import FilePermissionLevel

    permissions_map = {
        "file_001": FilePermissionLevel.VIEW,
        "file_002": FilePermissionLevel.EDIT,
        "file_003": FilePermissionLevel.ADMIN,
        "file_no_access": None
    }

    def mock_effective_permission(file_id, user_id):
        return permissions_map.get(file_id)

    with patch('api.common.check_file_permission.FilePermissionService.get_user_effective_permission',
               side_effect=mock_effective_permission):
        yield
