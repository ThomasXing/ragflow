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
端到端API测试 - TDD RED PHASE

这个脚本验证团队共享功能的实际API调用：
1. 登录获取token
2. 调用 /api/files 接口
3. 验证返回的文件列表是否包含共享文件夹

运行方式：
    source .venv/bin/activate && PYTHONPATH=. python scripts/e2e_test_team_share.py
"""

import json
import os
import sys
from pathlib import Path

import requests

# 添加项目根目录到路径
project_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(project_root))
os.environ.setdefault("PYTHONPATH", str(project_root))

# 配置
BASE_URL = os.environ.get("RAGFLOW_URL", "http://127.0.0.1:9380")


def login(email: str, password: str) -> str:
    """登录并返回token"""
    url = f"{BASE_URL}/v1/user/login"
    response = requests.post(url, json={"email": email, "password": password})
    if response.status_code != 200:
        raise Exception(f"登录失败: {response.text}")
    data = response.json()
    if data.get("code") != 0:
        raise Exception(f"登录失败: {data.get('message')}")
    return data["data"].get("authorization")


def get_user_info(token: str) -> dict:
    """获取用户信息"""
    url = f"{BASE_URL}/v1/user/info"
    headers = {"Authorization": token}
    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        raise Exception(f"获取用户信息失败: {response.text}")
    return response.json().get("data", {})


def list_files(token: str, parent_id: str = None) -> dict:
    """获取文件列表"""
    url = f"{BASE_URL}/api/files"
    headers = {"Authorization": token}
    params = {}
    if parent_id:
        params["parent_id"] = parent_id
    response = requests.get(url, headers=headers, params=params)
    if response.status_code != 200:
        raise Exception(f"获取文件列表失败: {response.text}")
    return response.json().get("data", {})


def get_joined_tenants(token: str) -> list:
    """获取用户加入的租户列表"""
    url = f"{BASE_URL}/v1/tenant/list"
    headers = {"Authorization": token}
    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        return []
    return response.json().get("data", [])


def main():
    """主测试函数"""
    print("=" * 60)
    print("端到端API测试 - 团队共享功能")
    print("=" * 60)

    # 测试用户凭据 - 需要根据实际环境配置
    # 使用数据库中实际存在的用户进行测试
    # 从 scripts/verify_team_share_data.py 获取正确的用户信息
    test_users = [
        # 用户 haiqingxing@gmail.com 同时是两个租户的成员
        # 作为 owner 属于 iwen's Kingdom (68298ef2...)
        # 作为 normal 属于 Alice's Kingdom (aff56dc4...)
        # Alice's Kingdom 有两个共享文件夹 test1/test2
        {"email": "haiqingxing@gmail.com", "password": os.environ.get("TEST_PASSWORD", "test123456")},
        # 可以添加更多测试用户
    ]

    results = []

    for user in test_users:
        print(f"\n{'='*60}")
        print(f"测试用户: {user['email']}")
        print("=" * 60)

        try:
            # 1. 登录
            print("\n[1] 登录...")
            token = login(user["email"], user["password"])
            print(f"    ✅ 登录成功，token: {token[:20]}...")

            # 2. 获取用户信息
            print("\n[2] 获取用户信息...")
            user_info = get_user_info(token)
            user_id = user_info.get("id")
            print(f"    用户ID: {user_id}")
            print(f"    用户名: {user_info.get('nickname', user_info.get('name'))}")

            # 3. 获取用户加入的租户
            print("\n[3] 获取用户加入的租户...")
            tenants = get_joined_tenants(token)
            print(f"    租户数量: {len(tenants)}")
            for t in tenants:
                print(f"      - {t.get('name')} (role: {t.get('role')})")

            # 4. 获取根目录文件列表
            print("\n[4] 获取根目录文件列表...")
            files_data = list_files(token)
            files = files_data.get("files", [])
            total = files_data.get("total", 0)
            print(f"    文件总数: {total}")
            print(f"    文件列表:")
            for f in files:
                is_shared = f.get("is_team_shared", False)
                marker = "🌐" if is_shared else "🔒"
                print(f"      {marker} {f.get('name')} (id: {f.get('id')[:8]}..., type: {f.get('type')})")
                if is_shared:
                    print(f"         └─ 团队共享文件夹!")

            # 5. 检查是否有共享文件夹
            shared_files = [f for f in files if f.get("is_team_shared")]
            print(f"\n[5] 共享文件夹统计...")
            print(f"    共享文件夹数量: {len(shared_files)}")

            if shared_files:
                print("    ✅ 用户可以看到共享文件夹!")
                for sf in shared_files:
                    print(f"      - {sf.get('name')}")
            else:
                print("    ⚠️ 用户没有看到共享文件夹")
                print("    可能原因:")
                print("      1. 用户没有以normal角色加入任何租户")
                print("      2. 租户没有启用团队共享的文件夹")
                print("      3. 共享文件夹的所有者就是当前用户自己")

            results.append({
                "email": user["email"],
                "user_id": user_id,
                "tenants": len(tenants),
                "total_files": total,
                "shared_files": len(shared_files),
                "success": True
            })

        except Exception as e:
            print(f"\n    ❌ 测试失败: {e}")
            results.append({
                "email": user["email"],
                "success": False,
                "error": str(e)
            })

    # 汇总报告
    print("\n" + "=" * 60)
    print("测试汇总")
    print("=" * 60)
    for r in results:
        if r["success"]:
            print(f"  ✅ {r['email']}: {r['shared_files']} 个共享文件夹")
        else:
            print(f"  ❌ {r['email']}: {r.get('error', 'Unknown error')}")

    return results


if __name__ == "__main__":
    main()
