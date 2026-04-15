"""
文件权限管理 API 测试用例

测试文件权限共享功能的各个方面，包括：
1. 创建文件共享
2. 获取共享列表
3. 更新权限级别
4. 撤销权限
5. 批量共享操作
6. 权限检查
7. 可分享用户列表
"""

import pytest
import json
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock
from test.utils import BaseTestCase


class TestFilePermissionManagement(BaseTestCase):
    """文件权限管理测试类"""

    @classmethod
    def setUpClass(cls):
        """测试类级别的设置"""
        super().setUpClass()
        # 创建测试用户
        cls.user1 = cls.create_test_user("test_user_1", "test1@example.com", "TestUser1")
        cls.user2 = cls.create_test_user("test_user_2", "test2@example.com", "TestUser2")
        cls.user3 = cls.create_test_user("test_user_3", "test3@example.com", "TestUser3")

        # 为每个用户创建租户
        cls.tenant1 = cls.create_test_tenant("TestTenant1", cls.user1["id"])
        cls.tenant2 = cls.create_test_tenant("TestTenant2", cls.user2["id"])
        cls.tenant3 = cls.create_test_tenant("TestTenant3", cls.user3["id"])

        # 创建测试文件
        cls.file1 = cls.create_test_file(
            tenant_id=cls.tenant1["id"],
            user_id=cls.user1["id"],
            name="test_document.pdf",
            type="application/pdf"
        )
        cls.file2 = cls.create_test_file(
            tenant_id=cls.tenant1["id"],
            user_id=cls.user1["id"],
            name="test_folder",
            type="folder"
        )

    def test_create_share_success(self):
        """测试成功创建文件共享"""
        headers = self.get_auth_headers(self.user1["token"])

        payload = {
            "file_id": self.file1["id"],
            "target_user_ids": [self.user2["id"]],
            "permission_level": "view"
        }

        response = self.client.post(
            "/v1/file_permission/share",
            headers=headers,
            json=payload
        )

        self.assertEqual(response.status_code, 200)
        data = response.json
        self.assertIn("data", data)
        self.assertIn("shares", data["data"])
        self.assertIn("failed", data["data"])

        # 验证分享成功
        shares = data["data"]["shares"]
        failed = data["data"]["failed"]
        self.assertEqual(len(shares), 1)
        self.assertEqual(len(failed), 0)

        share = shares[0]
        self.assertEqual(share["file_id"], self.file1["id"])
        self.assertEqual(share["target_user_id"], self.user2["id"])
        self.assertEqual(share["permission_level"], "view")
        self.assertEqual(share["sharer_id"], self.user1["id"])

    def test_create_share_with_expiration(self):
        """测试创建带过期时间的文件共享"""
        headers = self.get_auth_headers(self.user1["token"])

        # 设置未来30天的过期时间
        expires_at = (datetime.utcnow() + timedelta(days=30)).isoformat()

        payload = {
            "file_id": self.file1["id"],
            "target_user_ids": [self.user2["id"]],
            "permission_level": "edit",
            "expires_at": expires_at
        }

        response = self.client.post(
            "/v1/file_permission/share",
            headers=headers,
            json=payload
        )

        self.assertEqual(response.status_code, 200)
        data = response.json
        self.assertEqual(len(data["data"]["shares"]), 1)

        # 验证过期时间设置正确
        share = data["data"]["shares"][0]
        self.assertIsNotNone(share.get("expires_at"))

    def test_create_share_invalid_permission_level(self):
        """测试使用无效权限级别创建共享"""
        headers = self.get_auth_headers(self.user1["token"])

        payload = {
            "file_id": self.file1["id"],
            "target_user_ids": [self.user2["id"]],
            "permission_level": "invalid_level"
        }

        response = self.client.post(
            "/v1/file_permission/share",
            headers=headers,
            json=payload
        )

        self.assertEqual(response.status_code, 400)
        data = response.json
        self.assertEqual(data["code"], "ARGUMENT_ERROR")

    def test_create_share_without_permission(self):
        """测试无权限用户尝试创建共享"""
        headers = self.get_auth_headers(self.user2["token"])  # 使用 user2 尝试分享 user1 的文件

        payload = {
            "file_id": self.file1["id"],
            "target_user_ids": [self.user3["id"]],
            "permission_level": "view"
        }

        response = self.client.post(
            "/v1/file_permission/share",
            headers=headers,
            json=payload
        )

        self.assertEqual(response.status_code, 403)  # 权限错误
        data = response.json
        self.assertEqual(data["code"], "AUTHENTICATION_ERROR")

    def test_create_share_nonexistent_file(self):
        """测试为不存在的文件创建共享"""
        headers = self.get_auth_headers(self.user1["token"])

        payload = {
            "file_id": "non_existent_file_id",
            "target_user_ids": [self.user2["id"]],
            "permission_level": "view"
        }

        response = self.client.post(
            "/v1/file_permission/share",
            headers=headers,
            json=payload
        )

        self.assertEqual(response.status_code, 400)
        data = response.json
        self.assertEqual(data["message"], "文件不存在")

    def test_list_shares(self):
        """测试获取文件共享列表"""
        headers = self.get_auth_headers(self.user1["token"])

        # 先创建一个共享
        create_payload = {
            "file_id": self.file1["id"],
            "target_user_ids": [self.user2["id"], self.user3["id"]],
            "permission_level": "edit"
        }

        self.client.post(
            "/v1/file_permission/share",
            headers=headers,
            json=create_payload
        )

        # 获取共享列表
        response = self.client.get(
            f"/v1/file_permission/list?file_id={self.file1['id']}",
            headers=headers
        )

        self.assertEqual(response.status_code, 200)
        data = response.json
        self.assertIn("data", data)

        result = data["data"]
        self.assertIn("permissions", result)
        self.assertIn("inherited", result)
        self.assertIn("can_manage", result)
        self.assertIn("is_owner", result)

        # 验证权限信息
        permissions = result["permissions"]
        self.assertEqual(len(permissions), 2)  # 两个用户
        self.assertTrue(result["can_manage"])
        self.assertTrue(result["is_owner"])

    def test_list_shares_without_permission(self):
        """测试无权限用户获取共享列表"""
        headers = self.get_auth_headers(self.user3["token"])  # 用户3没有权限

        response = self.client.get(
            f"/v1/file_permission/list?file_id={self.file1['id']}",
            headers=headers
        )

        self.assertEqual(response.status_code, 403)
        data = response.json
        self.assertEqual(data["code"], "AUTHENTICATION_ERROR")

    def test_update_share_permission(self):
        """测试更新共享权限级别"""
        headers = self.get_auth_headers(self.user1["token"])

        # 先创建一个 VIEW 权限的共享
        create_payload = {
            "file_id": self.file1["id"],
            "target_user_ids": [self.user2["id"]],
            "permission_level": "view"
        }

        create_response = self.client.post(
            "/v1/file_permission/share",
            headers=headers,
            json=create_payload
        )

        share_id = create_response.json["data"]["shares"][0]["id"]

        # 更新为 EDIT 权限
        update_payload = {
            "share_id": share_id,
            "permission_level": "edit"
        }

        response = self.client.put(
            "/v1/file_permission/update",
            headers=headers,
            json=update_payload
        )

        self.assertEqual(response.status_code, 200)
        data = response.json
        self.assertEqual(data["data"], True)

        # 验证权限已更新
        list_response = self.client.get(
            f"/v1/file_permission/list?file_id={self.file1['id']}",
            headers=headers
        )

        permissions = list_response.json["data"]["permissions"]
        updated_share = next(p for p in permissions if p["id"] == share_id)
        self.assertEqual(updated_share["permission_level"], "edit")

    def test_revoke_share(self):
        """测试撤销共享权限"""
        headers = self.get_auth_headers(self.user1["token"])

        # 创建一个共享
        create_payload = {
            "file_id": self.file1["id"],
            "target_user_ids": [self.user2["id"]],
            "permission_level": "view"
        }

        create_response = self.client.post(
            "/v1/file_permission/share",
            headers=headers,
            json=create_payload
        )

        share_id = create_response.json["data"]["shares"][0]["id"]

        # 撤销共享
        response = self.client.delete(
            f"/v1/file_permission/revoke?share_id={share_id}",
            headers=headers
        )

        self.assertEqual(response.status_code, 200)
        data = response.json
        self.assertEqual(data["data"], True)

        # 验证共享已被移除
        list_response = self.client.get(
            f"/v1/file_permission/list?file_id={self.file1['id']}",
            headers=headers
        )

        permissions = list_response.json["data"]["permissions"]
        remaining_share = [p for p in permissions if p["id"] == share_id]
        self.assertEqual(len(remaining_share), 0)

    def test_shared_with_me(self):
        """测试获取共享给我的文件列表"""
        headers = self.get_auth_headers(self.user2["token"])

        # 用户1将文件分享给用户2
        user1_headers = self.get_auth_headers(self.user1["token"])
        share_payload = {
            "file_id": self.file1["id"],
            "target_user_ids": [self.user2["id"]],
            "permission_level": "view"
        }

        self.client.post(
            "/v1/file_permission/share",
            headers=user1_headers,
            json=share_payload
        )

        # 用户2获取共享给他的文件
        response = self.client.get(
            "/v1/file_permission/shared_with_me",
            headers=headers
        )

        self.assertEqual(response.status_code, 200)
        data = response.json
        self.assertIn("data", data)

        result = data["data"]
        self.assertIn("files", result)
        self.assertIn("total", result)

        files = result["files"]
        self.assertGreater(len(files), 0)

        # 验证文件信息
        shared_file = files[0]
        self.assertIn("id", shared_file)
        self.assertIn("name", shared_file)
        self.assertIn("share_permission", shared_file)
        self.assertEqual(shared_file["share_permission"], "view")

    def test_shared_by_me(self):
        """测试获取我分享的文件列表"""
        headers = self.get_auth_headers(self.user1["token"])

        # 用户1将文件分享给用户2和用户3
        share_payload = {
            "file_id": self.file1["id"],
            "target_user_ids": [self.user2["id"], self.user3["id"]],
            "permission_level": "edit"
        }

        self.client.post(
            "/v1/file_permission/share",
            headers=headers,
            json=share_payload
        )

        # 用户1获取他分享的文件
        response = self.client.get(
            "/v1/file_permission/shared_by_me",
            headers=headers
        )

        self.assertEqual(response.status_code, 200)
        data = response.json
        self.assertIn("data", data)

        result = data["data"]
        self.assertIn("files", result)
        self.assertIn("total", result)

        files = result["files"]
        self.assertGreater(len(files), 0)

    def test_batch_share(self):
        """测试批量文件共享"""
        headers = self.get_auth_headers(self.user1["token"])

        # 创建另一个测试文件
        file3 = self.create_test_file(
            tenant_id=self.tenant1["id"],
            user_id=self.user1["id"],
            name="test_document2.pdf",
            type="application/pdf"
        )

        payload = {
            "file_ids": [self.file1["id"], file3["id"]],
            "target_user_ids": [self.user2["id"]],
            "permission_level": "view"
        }

        response = self.client.post(
            "/v1/file_permission/batch_share",
            headers=headers,
            json=payload
        )

        self.assertEqual(response.status_code, 200)
        data = response.json
        self.assertIn("data", data)

        result = data["data"]
        self.assertIn("success", result)
        self.assertIn("failed", result)

        # 验证两个文件都成功分享
        self.assertEqual(len(result["success"]), 2)  # 两个文件
        self.assertEqual(len(result["failed"]), 0)

    def test_check_permission(self):
        """测试检查文件权限"""
        headers = self.get_auth_headers(self.user2["token"])

        # 用户1将文件分享给用户2
        user1_headers = self.get_auth_headers(self.user1["token"])
        share_payload = {
            "file_id": self.file1["id"],
            "target_user_ids": [self.user2["id"]],
            "permission_level": "edit"
        }

        self.client.post(
            "/v1/file_permission/share",
            headers=user1_headers,
            json=share_payload
        )

        # 用户2检查权限
        response = self.client.get(
            f"/v1/file_permission/check?file_id={self.file1['id']}",
            headers=headers
        )

        self.assertEqual(response.status_code, 200)
        data = response.json
        self.assertIn("data", data)

        perm_info = data["data"]
        self.assertTrue(perm_info["has_permission"])
        self.assertEqual(perm_info["permission_level"], "edit")
        self.assertEqual(perm_info["permission_source"], "explicit")
        self.assertFalse(perm_info["is_owner"])

    def test_check_permission_with_operation(self):
        """测试检查具体操作权限"""
        headers = self.get_auth_headers(self.user2["token"])

        # 用户1将文件分享给用户2，只有查看权限
        user1_headers = self.get_auth_headers(self.user1["token"])
        share_payload = {
            "file_id": self.file1["id"],
            "target_user_ids": [self.user2["id"]],
            "permission_level": "view"
        }

        self.client.post(
            "/v1/file_permission/share",
            headers=user1_headers,
            json=share_payload
        )

        # 检查查看权限 - 应该有权限
        response = self.client.get(
            f"/v1/file_permission/check?file_id={self.file1['id']}&operation=view",
            headers=headers
        )

        self.assertEqual(response.status_code, 200)
        data = response.json
        self.assertTrue(data["data"]["has_permission"])

        # 检查编辑权限 - 应该没有权限
        response = self.client.get(
            f"/v1/file_permission/check?file_id={self.file1['id']}&operation=edit",
            headers=headers
        )

        self.assertEqual(response.status_code, 200)
        data = response.json
        self.assertFalse(data["data"]["has_permission"])
        self.assertIsNotNone(data["data"]["error_message"])

    def test_get_shareable_users(self):
        """测试获取可分享用户列表"""
        headers = self.get_auth_headers(self.user1["token"])

        response = self.client.get(
            f"/v1/file_permission/shareable_users?file_id={self.file1['id']}",
            headers=headers
        )

        self.assertEqual(response.status_code, 200)
        data = response.json
        self.assertIn("data", data)

        result = data["data"]
        self.assertIn("users", result)
        self.assertTrue(result["can_share"])

        users = result["users"]
        # 应该包含除自己以外的其他用户
        user_ids = [user["id"] for user in users]
        self.assertIn(self.user2["id"], user_ids)
        self.assertIn(self.user3["id"], user_ids)
        self.assertNotIn(self.user1["id"], user_ids)  # 不应该包含自己

    def test_folder_sharing(self):
        """测试文件夹共享功能"""
        headers = self.get_auth_headers(self.user1["token"])

        payload = {
            "file_id": self.file2["id"],  # 文件夹
            "target_user_ids": [self.user2["id"]],
            "permission_level": "admin"
        }

        response = self.client.post(
            "/v1/file_permission/share",
            headers=headers,
            json=payload
        )

        self.assertEqual(response.status_code, 200)
        data = response.json
        self.assertEqual(len(data["data"]["shares"]), 1)

        share = data["data"]["shares"][0]
        self.assertEqual(share["permission_level"], "admin")

    def test_expired_share(self):
        """测试过期共享权限不再有效"""
        headers = self.get_auth_headers(self.user1["token"])

        # 创建一个已过期的共享
        expired_time = (datetime.utcnow() - timedelta(days=1)).isoformat()

        payload = {
            "file_id": self.file1["id"],
            "target_user_ids": [self.user2["id"]],
            "permission_level": "view",
            "expires_at": expired_time
        }

        response = self.client.post(
            "/v1/file_permission/share",
            headers=headers,
            json=payload
        )

        self.assertEqual(response.status_code, 200)

        # 用户2尝试访问 - 应该失败
        user2_headers = self.get_auth_headers(self.user2["token"])
        check_response = self.client.get(
            f"/v1/file_permission/check?file_id={self.file1['id']}",
            headers=user2_headers
        )

        # 过期权限应该不生效
        check_data = check_response.json["data"]
        self.assertFalse(check_data["has_permission"])

    def test_duplicate_share_prevention(self):
        """测试防止重复共享"""
        headers = self.get_auth_headers(self.user1["token"])

        # 第一次共享
        payload = {
            "file_id": self.file1["id"],
            "target_user_ids": [self.user2["id"]],
            "permission_level": "view"
        }

        response1 = self.client.post(
            "/v1/file_permission/share",
            headers=headers,
            json=payload
        )

        self.assertEqual(response1.status_code, 200)

        # 第二次相同的共享 - 应该提示已存在
        response2 = self.client.post(
            "/v1/file_permission/share",
            headers=headers,
            json=payload
        )

        self.assertEqual(response2.status_code, 200)
        data = response2.json["data"]

        # 应该包含失败信息
        self.assertEqual(len(data["failed"]), 1)
        failed_item = data["failed"][0]
        self.assertIn("已存在", failed_item["error"])

    def test_cascade_permission_inheritance(self):
        """测试权限继承功能"""
        # 创建文件夹和子文件
        headers = self.get_auth_headers(self.user1["token"])

        # 分享文件夹给用户2（admin权限）
        folder_share_payload = {
            "file_id": self.file2["id"],  # 文件夹
            "target_user_ids": [self.user2["id"]],
            "permission_level": "admin"
        }

        self.client.post(
            "/v1/file_permission/share",
            headers=headers,
            json=folder_share_payload
        )

        # 创建文件夹下的子文件
        subfile = self.create_test_file(
            tenant_id=self.tenant1["id"],
            user_id=self.user1["id"],
            name="subfile.txt",
            type="text/plain",
            parent_id=self.file2["id"]
        )

        # 用户2应该继承文件夹权限，能访问子文件
        user2_headers = self.get_auth_headers(self.user2["token"])
        check_response = self.client.get(
            f"/v1/file_permission/check?file_id={subfile['id']}",
            headers=user2_headers
        )

        check_data = check_response.json["data"]
        self.assertTrue(check_data["has_permission"])
        self.assertEqual(check_data["permission_source"], "inherited")

    def test_remove_share_after_user_removal(self):
        """测试用户被删除后自动移除相关共享"""
        # 创建临时用户
        temp_user = self.create_test_user("temp_user", "temp@example.com", "TempUser")

        headers = self.get_auth_headers(self.user1["token"])

        # 分享文件给临时用户
        share_payload = {
            "file_id": self.file1["id"],
            "target_user_ids": [temp_user["id"]],
            "permission_level": "view"
        }

        response = self.client.post(
            "/v1/file_permission/share",
            headers=headers,
            json=share_payload
        )

        self.assertEqual(response.status_code, 200)

        # 删除临时用户
        self.delete_test_user(temp_user["id"])

        # 检查共享列表中应该不包含已删除用户
        list_response = self.client.get(
            f"/v1/file_permission/list?file_id={self.file1['id']}",
            headers=headers
        )

        permissions = list_response.json["data"]["permissions"]
        temp_user_shares = [p for p in permissions if p["target_user_id"] == temp_user["id"]]
        self.assertEqual(len(temp_user_shares), 0)

    def test_admin_permission_boundary(self):
        """测试管理员权限边界"""
        headers = self.get_auth_headers(self.user1["token"])

        # 分享文件给用户2（admin权限）
        share_payload = {
            "file_id": self.file1["id"],
            "target_user_ids": [self.user2["id"]],
            "permission_level": "admin"
        }

        response = self.client.post(
            "/v1/file_permission/share",
            headers=headers,
            json=share_payload
        )

        self.assertEqual(response.status_code, 200)

        # 用户2应该可以进一步分享文件
        user2_headers = self.get_auth_headers(self.user2["token"])
        user2_share_payload = {
            "file_id": self.file1["id"],
            "target_user_ids": [self.user3["id"]],
            "permission_level": "view"
        }

        user2_response = self.client.post(
            "/v1/file_permission/share",
            headers=user2_headers,
            json=user2_share_payload
        )

        self.assertEqual(user2_response.status_code, 200)

    def test_view_only_permission_limitations(self):
        """测试仅查看权限的限制"""
        headers = self.get_auth_headers(self.user1["token"])

        # 分享文件给用户2（仅查看权限）
        share_payload = {
            "file_id": self.file1["id"],
            "target_user_ids": [self.user2["id"]],
            "permission_level": "view"
        }

        response = self.client.post(
            "/v1/file_permission/share",
            headers=headers,
            json=share_payload
        )

        self.assertEqual(response.status_code, 200)

        # 用户2不能进一步分享文件
        user2_headers = self.get_auth_headers(self.user2["token"])
        user2_share_payload = {
            "file_id": self.file1["id"],
            "target_user_ids": [self.user3["id"]],
            "permission_level": "view"
        }

        user2_response = self.client.post(
            "/v1/file_permission/share",
            headers=user2_headers,
            json=user2_share_payload
        )

        self.assertEqual(user2_response.status_code, 403)
        self.assertEqual(user2_response.json["code"], "AUTHENTICATION_ERROR")

    def test_concurrent_share_operations(self):
        """测试并发共享操作"""
        headers = self.get_auth_headers(self.user1["token"])

        import threading
        from concurrent.futures import ThreadPoolExecutor

        def share_to_user(user_id):
            """分享文件给指定用户"""
            payload = {
                "file_id": self.file1["id"],
                "target_user_ids": [user_id],
                "permission_level": "view"
            }

            return self.client.post(
                "/v1/file_permission/share",
                headers=headers,
                json=payload
            )

        # 创建10个测试用户
        test_users = []
        for i in range(10):
            user = self.create_test_user(
                f"concurrent_user_{i}",
                f"concurrent{i}@example.com",
                f"ConcurrentUser{i}"
            )
            test_users.append(user["id"])

        # 并发执行分享操作
        results = []
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(share_to_user, user_id) for user_id in test_users]
            for future in futures:
                results.append(future.result())

        # 验证所有请求都成功
        for response in results:
            self.assertEqual(response.status_code, 200)

        # 验证所有分享都创建成功
        list_response = self.client.get(
            f"/v1/file_permission/list?file_id={self.file1['id']}",
            headers=headers
        )

        permissions = list_response.json["data"]["permissions"]
        shared_user_ids = {p["target_user_id"] for p in permissions}

        # 应该包含所有10个测试用户
        for user_id in test_users:
            self.assertIn(user_id, shared_user_ids)

    def test_share_performance(self):
        """测试分享性能"""
        headers = self.get_auth_headers(self.user1["token"])

        import time

        # 创建100个测试用户
        start_time = time.time()

        test_users = []
        for i in range(100):
            user = self.create_test_user(
                f"perf_user_{i}",
                f"perf{i}@example.com",
                f"PerfUser{i}"
            )
            test_users.append(user["id"])

        user_creation_time = time.time() - start_time
        print(f"用户创建耗时: {user_creation_time:.2f}秒")

        # 批量分享给所有用户
        start_time = time.time()

        payload = {
            "file_id": self.file1["id"],
            "target_user_ids": test_users,
            "permission_level": "view"
        }

        response = self.client.post(
            "/v1/file_permission/share",
            headers=headers,
            json=payload
        )

        share_time = time.time() - start_time
        print(f"批量分享耗时: {share_time:.2f}秒")

        self.assertEqual(response.status_code, 200)
        data = response.json["data"]

        # 验证成功和失败的数量
        successful = len(data["shares"])
        failed = len(data["failed"])
        print(f"成功: {successful}, 失败: {failed}")

        # 成功率应该很高（接近100%）
        self.assertGreater(successful / len(test_users), 0.95)

    @classmethod
    def tearDownClass(cls):
        """测试类级别的清理"""
        # 清理测试数据
        cls.delete_test_file(cls.file1["id"])
        cls.delete_test_file(cls.file2["id"])
        cls.delete_test_tenant(cls.tenant1["id"])
        cls.delete_test_tenant(cls.tenant2["id"])
        cls.delete_test_tenant(cls.tenant3["id"])
        cls.delete_test_user(cls.user1["id"])
        cls.delete_test_user(cls.user2["id"])
        cls.delete_test_user(cls.user3["id"])

        super().tearDownClass()