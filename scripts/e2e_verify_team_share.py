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
端到端功能验证 - TDD GREEN PHASE

这个脚本直接调用服务层验证团队共享功能的实际行为：
1. 模拟用户调用 list_files
2. 验证返回的文件列表是否包含共享文件夹

运行方式：
    source .venv/bin/activate && PYTHONPATH=. python scripts/e2e_verify_team_share.py
"""

import os
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(project_root))
os.environ.setdefault("PYTHONPATH", str(project_root))


def main():
    """主测试函数"""
    print("=" * 60)
    print("端到端功能验证 - 团队共享功能")
    print("=" * 60)

    # 使用数据库中的真实用户ID进行测试
    # 用户 haiqingxing@gmail.com (id: 68298ef2322c11f18dd21e71dcb42474)
    # 作为 normal 属于租户 aff56dc4323011f18dd21e71dcb42474
    test_user_id = "68298ef2322c11f18dd21e71dcb42474"

    try:
        from api.db.db_models import DB
        from api.apps.services.file_api_service import list_files
        from api.db.services.user_service import TenantService
        from api.db.services.team_permission_service import TeamPermissionService

        print(f"\n[1] 测试用户ID: {test_user_id}")

        # 获取用户加入的租户
        print("\n[2] 获取用户加入的租户...")
        joined_tenants = TenantService.get_joined_tenants_by_user_id(test_user_id)
        print(f"    租户数量: {len(joined_tenants)}")
        for t in joined_tenants:
            print(f"      - {t.get('name')} (tenant_id: {t.get('tenant_id')[:8]}..., role: normal)")

        # 获取每个租户的共享文件夹
        print("\n[3] 获取每个租户的共享文件夹...")
        all_shared = []
        for t in joined_tenants:
            tenant_id = t.get("tenant_id")
            shared_ids = TeamPermissionService.get_shared_file_ids_for_user(
                user_id=test_user_id,
                user_tenant_id=tenant_id
            )
            if shared_ids:
                print(f"    租户 {t.get('name')[:15]}: {len(shared_ids)} 个共享文件夹")
                for sid in shared_ids:
                    all_shared.append((sid, tenant_id))

        # 调用 list_files
        print("\n[4] 调用 list_files (模拟根目录查询)...")
        args = {}  # 无 parent_id = 根目录
        success, result = list_files(
            tenant_id=test_user_id,
            args=args,
            user_id=test_user_id
        )

        if not success:
            print(f"    ❌ list_files 失败: {result}")
            return

        files = result.get("files", [])
        total = result.get("total", 0)
        print(f"    文件总数: {total}")

        # 检查共享文件夹
        print("\n[5] 检查共享文件夹...")
        shared_files = [f for f in files if f.get("is_team_shared")]
        print(f"    共享文件夹数量: {len(shared_files)}")

        if shared_files:
            print("    ✅ 用户可以看到共享文件夹!")
            for sf in shared_files:
                print(f"      - {sf.get('name')} (权限来自团队共享)")
        else:
            print("    ⚠️ 用户没有看到共享文件夹")
            print("    检查可能的原因...")

            # 检查文件列表中的所有文件
            print(f"\n    所有文件列表 ({len(files)} 个):")
            for f in files:
                print(f"      - {f.get('name')} (id: {f.get('id')[:8]}..., type: {f.get('type')})")

        # 验证结果
        print("\n" + "=" * 60)
        print("验证结果")
        print("=" * 60)

        expected_shared_ids = [s[0] for s in all_shared]
        actual_ids = [f.get("id") for f in files]

        print(f"预期共享文件夹ID: {expected_shared_ids}")
        print(f"实际返回的文件ID: {actual_ids[:5]}...")

        found_count = 0
        for expected_id in expected_shared_ids:
            if expected_id in actual_ids:
                found_count += 1
                print(f"  ✅ 共享文件夹 {expected_id[:8]}... 在列表中")
            else:
                print(f"  ❌ 共享文件夹 {expected_id[:8]}... 不在列表中")

        if found_count == len(expected_shared_ids):
            print("\n✅ 所有共享文件夹都正确返回!")
        else:
            print(f"\n⚠️ 只找到 {found_count}/{len(expected_shared_ids)} 个共享文件夹")

    except Exception as e:
        print(f"\n❌ 验证失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
