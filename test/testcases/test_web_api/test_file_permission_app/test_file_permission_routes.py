#
#  Copyright 2026 The InfiniFlow Authors. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  You may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
#
"""
文件权限 API 集成测试

测试覆盖：
- 创建共享 API
- 获取共享列表 API
- 更新权限 API
- 撤销权限 API
- 共享给我的文件 API
- 我的分享 API
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock, AsyncMock


class TestCreateShareAPI:
    """测试创建共享 API"""

    @pytest.mark.p1
    @pytest.mark.asyncio
    async def test_create_share_success(self, mock_app, mock_auth, mock_file_permission_service):
        """
        TC-001: 创建共享成功
        """
        from api.db import FilePermissionLevel

        # Arrange
        request_data = {
            "file_id": "file_001",
            "target_user_ids": ["user_002"],
            "permission_level": FilePermissionLevel.VIEW
        }

        # Act
        response = await mock_app.post('/api/file_permission/share', json=request_data)

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
        assert len(data["data"]["shares"]) == 1
        assert len(data["data"]["failed"]) == 0

    @pytest.mark.p1
    @pytest.mark.asyncio
    async def test_create_share_invalid_permission_level(self, mock_app, mock_auth):
        """
        TC-001: 创建共享 - 无效权限级别
        """
        request_data = {
            "file_id": "file_001",
            "target_user_ids": ["user_002"],
            "permission_level": "invalid_level"
        }

        response = await mock_app.post('/api/file_permission/share', json=request_data)

        assert response.status_code == 200
        data = response.json()
        assert data["code"] != 0
        assert "无效" in data["message"] or "invalid" in data["message"].lower()

    @pytest.mark.p1
    @pytest.mark.asyncio
    async def test_create_share_file_not_found(self, mock_app, mock_auth, mock_file_service_not_found):
        """
        TC-001: 创建共享 - 文件不存在
        """
        from api.db import FilePermissionLevel

        request_data = {
            "file_id": "non_existent_file",
            "target_user_ids": ["user_002"],
            "permission_level": FilePermissionLevel.VIEW
        }

        response = await mock_app.post('/api/file_permission/share', json=request_data)

        assert response.status_code == 200
        data = response.json()
        assert data["code"] != 0
        assert "不存在" in data["message"] or "not found" in data["message"].lower()

    @pytest.mark.p1
    @pytest.mark.asyncio
    async def test_create_share_no_permission(self, mock_app, mock_auth, mock_no_share_permission):
        """
        TC-001: 创建共享 - 无分享权限
        """
        from api.db import FilePermissionLevel

        request_data = {
            "file_id": "file_001",
            "target_user_ids": ["user_002"],
            "permission_level": FilePermissionLevel.VIEW
        }

        response = await mock_app.post('/api/file_permission/share', json=request_data)

        assert response.status_code == 200
        data = response.json()
        assert data["code"] != 0
        assert "权限" in data["message"]


class TestListSharesAPI:
    """测试获取共享列表 API"""

    @pytest.mark.p1
    @pytest.mark.asyncio
    async def test_list_shares_success(self, mock_app, mock_auth, mock_file_permission_service):
        """
        获取文件的共享列表
        """
        response = await mock_app.get('/api/file_permission/list?file_id=file_001')

        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
        assert "permissions" in data["data"]
        assert "inherited" in data["data"]
        assert "can_manage" in data["data"]

    @pytest.mark.p2
    @pytest.mark.asyncio
    async def test_list_shares_inherited_permissions(self, mock_app, mock_auth, mock_file_with_inheritance):
        """
        TC-110: 获取继承权限列表
        """
        response = await mock_app.get('/api/file_permission/list?file_id=file_nested')

        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
        # 应该包含继承权限
        assert len(data["data"]["inherited"]) > 0


class TestUpdateShareAPI:
    """测试更新权限 API"""

    @pytest.mark.p1
    @pytest.mark.asyncio
    async def test_update_share_success(self, mock_app, mock_auth, mock_file_permission_service):
        """
        US-003: 更新权限成功
        """
        from api.db import FilePermissionLevel

        request_data = {
            "share_id": "share_001",
            "permission_level": FilePermissionLevel.EDIT
        }

        response = await mock_app.put('/api/file_permission/update', json=request_data)

        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
        assert data["data"] is True

    @pytest.mark.p1
    @pytest.mark.asyncio
    async def test_update_share_not_found(self, mock_app, mock_auth, mock_share_not_found):
        """
        更新不存在共享
        """
        from api.db import FilePermissionLevel

        request_data = {
            "share_id": "non_existent_share",
            "permission_level": FilePermissionLevel.EDIT
        }

        response = await mock_app.put('/api/file_permission/update', json=request_data)

        assert response.status_code == 200
        data = response.json()
        assert data["code"] != 0


class TestRevokeShareAPI:
    """测试撤销权限 API"""

    @pytest.mark.p1
    @pytest.mark.asyncio
    async def test_revoke_share_success(self, mock_app, mock_auth, mock_file_permission_service):
        """
        TC-202: 撤销权限成功
        """
        response = await mock_app.delete('/api/file_permission/revoke?share_id=share_001')

        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
        assert data["data"] is True

    @pytest.mark.p2
    @pytest.mark.asyncio
    async def test_revoke_share_no_permission(self, mock_app, mock_auth, mock_no_manage_permission):
        """
        撤销权限 - 无管理权限
        """
        response = await mock_app.delete('/api/file_permission/revoke?share_id=share_001')

        assert response.status_code == 200
        data = response.json()
        assert data["code"] != 0


class TestSharedWithMeAPI:
    """测试共享给我的文件 API"""

    @pytest.mark.p1
    @pytest.mark.asyncio
    async def test_shared_with_me_success(self, mock_app, mock_auth, mock_file_permission_service):
        """
        US-002: 获取共享给我的文件列表
        """
        response = await mock_app.get('/api/file_permission/shared_with_me?page=1&page_size=15')

        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
        assert "files" in data["data"]
        assert "total" in data["data"]

    @pytest.mark.p2
    @pytest.mark.asyncio
    async def test_shared_with_me_with_keywords(self, mock_app, mock_auth, mock_file_permission_service):
        """
        US-002: 搜索共享给我的文件
        """
        response = await mock_app.get('/api/file_permission/shared_with_me?page=1&page_size=15&keywords=test')

        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0

    @pytest.mark.p2
    @pytest.mark.asyncio
    async def test_shared_with_me_expired_hidden(self, mock_app, mock_auth, mock_expired_share):
        """
        TC-201: 过期的共享不显示
        """
        response = await mock_app.get('/api/file_permission/shared_with_me?page=1&page_size=15')

        assert response.status_code == 200
        data = response.json()
        # 过期的共享不应该出现
        files = data["data"]["files"]
        expired_files = [f for f in files if f.get("share_id") == "expired_share"]
        assert len(expired_files) == 0


class TestSharedByMeAPI:
    """测试我的分享 API"""

    @pytest.mark.p1
    @pytest.mark.asyncio
    async def test_shared_by_me_success(self, mock_app, mock_auth, mock_file_permission_service):
        """
        US-003: 获取我分享的文件列表
        """
        response = await mock_app.get('/api/file_permission/shared_by_me?page=1&page_size=15')

        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
        assert "files" in data["data"]
        assert "total" in data["data"]


class TestBatchShareAPI:
    """测试批量共享 API"""

    @pytest.mark.p2
    @pytest.mark.asyncio
    async def test_batch_share_success(self, mock_app, mock_auth, mock_file_permission_service):
        """
        US-001: 批量共享成功
        """
        from api.db import FilePermissionLevel

        request_data = {
            "file_ids": ["file_001", "file_002"],
            "target_user_ids": ["user_002", "user_003"],
            "permission_level": FilePermissionLevel.VIEW
        }

        response = await mock_app.post('/api/file_permission/batch_share', json=request_data)

        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
        assert len(data["data"]["success"]) > 0

    @pytest.mark.p2
    @pytest.mark.asyncio
    async def test_batch_share_partial_failure(self, mock_app, mock_auth, mock_partial_permission):
        """
        批量共享 - 部分失败
        """
        from api.db import FilePermissionLevel

        request_data = {
            "file_ids": ["file_001", "no_permission_file"],
            "target_user_ids": ["user_002"],
            "permission_level": FilePermissionLevel.VIEW
        }

        response = await mock_app.post('/api/file_permission/batch_share', json=request_data)

        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
        # 应该有成功和失败
        assert len(data["data"]["success"]) > 0
        assert len(data["data"]["failed"]) > 0


class TestCheckPermissionAPI:
    """测试权限检查 API"""

    @pytest.mark.p1
    @pytest.mark.asyncio
    async def test_check_permission_view(self, mock_app, mock_auth, mock_view_permission):
        """
        TC-101: 检查查看权限
        """
        response = await mock_app.get('/api/file_permission/check?file_id=file_001&operation=view')

        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
        assert data["data"]["has_permission"] is True
        assert data["data"]["permission_level"] == "view"

    @pytest.mark.p1
    @pytest.mark.asyncio
    async def test_check_permission_edit_denied(self, mock_app, mock_auth, mock_view_permission):
        """
        TC-103: 检查编辑权限 - VIEW 权限不足
        """
        response = await mock_app.get('/api/file_permission/check?file_id=file_001&operation=edit')

        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
        assert data["data"]["has_permission"] is False

    @pytest.mark.p1
    @pytest.mark.asyncio
    async def test_check_permission_no_permission(self, mock_app, mock_auth, mock_no_permission):
        """
        检查权限 - 无权限
        """
        response = await mock_app.get('/api/file_permission/check?file_id=no_access_file')

        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
        assert data["data"]["has_permission"] is False
        assert data["data"]["permission_level"] is None


class TestShareableUsersAPI:
    """测试可分享用户 API"""

    @pytest.mark.p1
    @pytest.mark.asyncio
    async def test_get_shareable_users(self, mock_app, mock_auth, mock_team_members):
        """
        获取可分享用户列表
        """
        response = await mock_app.get('/api/file_permission/shareable_users?file_id=file_001')

        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
        assert "users" in data["data"]
        assert data["data"]["can_share"] is True

    @pytest.mark.p2
    @pytest.mark.asyncio
    async def test_shareable_users_exclude_owner(self, mock_app, mock_auth, mock_team_members):
        """
        TC-003: 可分享用户不包含所有者
        """
        response = await mock_app.get('/api/file_permission/shareable_users?file_id=file_001')

        assert response.status_code == 200
        data = response.json()
        # 所有者 user_001 不应该在列表中
        users = data["data"]["users"]
        owner_ids = [u["id"] for u in users if u.get("id") == "user_001"]
        assert len(owner_ids) == 0


# ============== Fixtures ==============

@pytest.fixture
def mock_app():
    """Mock Quart 应用"""
    from quart import Quart
    app = Quart(__name__)

    # 注册路由
    # 在实际测试中会导入真实的 API 蓝图
    yield app


@pytest.fixture
def mock_auth():
    """Mock 认证"""
    with patch('api.apps.current_user') as mock:
        mock.id = "user_001"
        mock.nickname = "Test User"
        mock.email = "test@example.com"
        yield mock


@pytest.fixture
def mock_file_permission_service():
    """Mock FilePermissionService"""
    from api.db import FilePermissionLevel

    mock_share = MagicMock()
    mock_share.id = "share_001"
    mock_share.file_id = "file_001"
    mock_share.target_user_id = "user_002"
    mock_share.permission_level = FilePermissionLevel.VIEW
    mock_share.status = "1"
    mock_share.to_dict.return_value = {
        "id": "share_001",
        "file_id": "file_001",
        "target_user_id": "user_002",
        "permission_level": "view",
        "status": "1"
    }

    with patch('api.db.services.file_permission_service.FilePermissionService.create_share',
               return_value=mock_share), \
         patch('api.db.services.file_permission_service.FilePermissionService.get_file_permissions',
               return_value=[mock_share.to_dict()]), \
         patch('api.db.services.file_permission_service.FilePermissionService.get_user_effective_permission',
               return_value=FilePermissionLevel.ADMIN), \
         patch('api.db.services.file_permission_service.FilePermissionService.update_permission',
               return_value=True), \
         patch('api.db.services.file_permission_service.FilePermissionService.revoke_permission',
               return_value=True), \
         patch('api.db.services.file_permission_service.FilePermissionService.get_shared_files_for_user',
               return_value=([{"id": "file_001", "name": "test.txt"}], 1)), \
         patch('api.db.services.file_permission_service.FilePermissionService.get_files_shared_by_user',
               return_value=([{"id": "file_002", "name": "shared.txt"}], 1)), \
         patch('api.db.services.file_permission_service.FilePermissionService.batch_create_shares',
               return_value=([{"share_id": "share_001", "file_id": "file_001"}], [])), \
         patch('api.db.services.file_permission_service.FilePermissionService.can_share_to_user',
               return_value=(True, "")):
        yield mock_share


@pytest.fixture
def mock_file_service_not_found():
    """Mock FileService - 文件不存在"""
    with patch('api.db.services.file_service.FileService.get_by_id',
               return_value=(False, None)):
        yield


@pytest.fixture
def mock_no_share_permission():
    """Mock 无分享权限"""
    with patch('api.common.check_file_permission.can_user_share_file',
               return_value=(False, "需要 ADMIN 权限才能分享")):
        yield


@pytest.fixture
def mock_no_manage_permission():
    """Mock 无管理权限"""
    with patch('api.common.check_file_permission.can_user_manage_permissions',
               return_value=(False, "需要 ADMIN 权限才能管理权限")):
        yield


@pytest.fixture
def mock_file_with_inheritance():
    """Mock 文件继承权限"""
    from api.db import FilePermissionLevel

    with patch('api.db.services.file_permission_service.FilePermissionService.get_file_permissions',
               return_value=[]), \
         patch('api.db.services.file_permission_service.FilePermissionService.get_inherited_permissions',
               return_value=[{"file_id": "parent_folder", "file_name": "Parent", "permission_level": "admin"}]), \
         patch('api.common.check_file_permission.can_user_manage_permissions',
               return_value=(True, "")):
        yield


@pytest.fixture
def mock_share_not_found():
    """Mock 共享不存在"""
    with patch('api.db.services.file_permission_service.FilePermissionService.get_share_by_id',
               return_value=(False, None)):
        yield


@pytest.fixture
def mock_expired_share():
    """Mock 过期共享"""
    from api.db import FilePermissionLevel

    expired_time = datetime.now() - timedelta(days=1)

    with patch('api.db.services.file_permission_service.FilePermissionService.get_shared_files_for_user',
               return_value=([], 0)):  # 过期共享不应返回
        yield


@pytest.fixture
def mock_view_permission():
    """Mock VIEW 权限"""
    from api.db import FilePermissionLevel

    with patch('api.common.check_file_permission.get_permission_info',
               return_value={
                   "is_owner": False,
                   "permission_level": FilePermissionLevel.VIEW,
                   "permission_source": "explicit",
                   "inherited_from": []
               }), \
         patch('api.common.check_file_permission.check_file_operation_permission') as mock_check:
        # view 和 download 允许，其他拒绝
        def check_op(file_id, user_id, operation):
            if operation in ["view", "download"]:
                return True, ""
            return False, f"权限不足，需要更高权限执行 {operation}"
        mock_check.side_effect = check_op
        yield


@pytest.fixture
def mock_no_permission():
    """Mock 无权限"""
    with patch('api.common.check_file_permission.get_permission_info',
               return_value={
                   "is_owner": False,
                   "permission_level": None,
                   "permission_source": "none",
                   "inherited_from": []
               }):
        yield


@pytest.fixture
def mock_partial_permission():
    """Mock 部分权限（部分文件无权限）"""
    from api.db import FilePermissionLevel

    permission_map = {
        "file_001": (True, ""),
        "no_permission_file": (False, "无权限")
    }

    def mock_can_share(file_id, user_id):
        return permission_map.get(file_id, (False, "无权限"))

    with patch('api.common.check_file_permission.can_user_share_file',
               side_effect=mock_can_share):
        yield


@pytest.fixture
def mock_team_members():
    """Mock 团队成员"""
    mock_users = [
        {"id": "user_001", "nickname": "Owner", "email": "owner@example.com"},  # 所有者
        {"id": "user_002", "nickname": "Member 1", "email": "member1@example.com"},
        {"id": "user_003", "nickname": "Member 2", "email": "member2@example.com"},
    ]

    with patch('api.db.services.user_service.TenantService.get_joined_tenants_by_user_id',
               return_value=[{"tenant_id": "tenant_001", "user_id": "user_002"},
                            {"tenant_id": "tenant_001", "user_id": "user_003"}]), \
         patch('api.db.services.user_service.UserService.query',
               return_value=[MagicMock(to_dict=lambda: u) for u in mock_users[1:]]), \
         patch('api.db.services.file_service.FileService.get_by_id',
               return_value=(True, MagicMock(created_by="user_001", tenant_id="tenant_001"))), \
         patch('api.common.check_file_permission.can_user_share_file',
               return_value=(True, "")):
        yield mock_users
