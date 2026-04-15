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
数据层验证脚本 - TDD RED PHASE

这个脚本验证团队共享功能的数据层状态：
1. team_permission_share 表是否存在
2. user_tenant 表是否有正确的用户-租户关联
3. file 表中是否有正确的数据

运行方式：
    cd /path/to/ragflow && source .venv/bin/activate && PYTHONPATH=. python scripts/verify_team_share_data.py
"""

import os
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(project_root))
os.environ.setdefault("PYTHONPATH", str(project_root))


def check_table_exists(cursor, table_name: str) -> bool:
    """检查表是否存在"""
    cursor.execute(f"SHOW TABLES LIKE '{table_name}'")
    result = cursor.fetchone()
    return result is not None


def check_table_has_data(cursor, table_name: str) -> int:
    """检查表是否有数据，返回记录数"""
    cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
    result = cursor.fetchone()
    return result[0] if result else 0


def main():
    """主验证函数"""
    print("=" * 60)
    print("团队共享功能数据层验证")
    print("=" * 60)

    # 初始化数据库连接
    try:
        from api.db.db_models import DB

        # 获取游标
        conn = DB.connection()
        cursor = conn.cursor()

        results = {}

        # 1. 检查 team_permission_share 表
        print("\n[1] 检查 team_permission_share 表...")
        if check_table_exists(cursor, "team_permission_share"):
            count = check_table_has_data(cursor, "team_permission_share")
            print(f"    ✅ 表存在，记录数: {count}")
            results["team_permission_share"] = {"exists": True, "count": count}

            if count > 0:
                # 查看示例数据
                cursor.execute("SELECT * FROM team_permission_share LIMIT 3")
                rows = cursor.fetchall()
                cursor.execute("DESCRIBE team_permission_share")
                columns = [col[0] for col in cursor.fetchall()]
                print(f"    列: {columns}")
                for row in rows:
                    print(f"    示例: {dict(zip(columns, row))}")
        else:
            print("    ❌ 表不存在")
            results["team_permission_share"] = {"exists": False, "count": 0}

        # 2. 检查 user_tenant 表
        print("\n[2] 检查 user_tenant 表...")
        if check_table_exists(cursor, "user_tenant"):
            count = check_table_has_data(cursor, "user_tenant")
            print(f"    ✅ 表存在，记录数: {count}")
            results["user_tenant"] = {"exists": True, "count": count}

            if count > 0:
                cursor.execute("SELECT * FROM user_tenant LIMIT 3")
                rows = cursor.fetchall()
                cursor.execute("DESCRIBE user_tenant")
                columns = [col[0] for col in cursor.fetchall()]
                print(f"    列: {columns}")
                for row in rows:
                    print(f"    示例: {dict(zip(columns, row))}")
        else:
            print("    ❌ 表不存在")
            results["user_tenant"] = {"exists": False, "count": 0}

        # 3. 检查 file 表
        print("\n[3] 检查 file 表...")
        if check_table_exists(cursor, "file"):
            count = check_table_has_data(cursor, "file")
            print(f"    ✅ 表存在，记录数: {count}")
            results["file"] = {"exists": True, "count": count}

            if count > 0:
                # 查看文件夹类型的文件
                cursor.execute(
                    "SELECT id, name, tenant_id, created_by, type FROM file WHERE type = 'folder' LIMIT 5"
                )
                rows = cursor.fetchall()
                print(f"    文件夹示例:")
                for row in rows:
                    print(f"      id={row[0]}, name={row[1]}, tenant_id={row[2]}, created_by={row[3]}")
        else:
            print("    ❌ 表不存在")
            results["file"] = {"exists": False, "count": 0}

        # 4. 检查 tenant 表
        print("\n[4] 检查 tenant 表...")
        if check_table_exists(cursor, "tenant"):
            count = check_table_has_data(cursor, "tenant")
            print(f"    ✅ 表存在，记录数: {count}")
            results["tenant"] = {"exists": True, "count": count}

            if count > 0:
                cursor.execute("SELECT id, name FROM tenant LIMIT 5")
                rows = cursor.fetchall()
                print(f"    租户示例:")
                for row in rows:
                    print(f"      id={row[0]}, name={row[1]}")
        else:
            print("    ❌ 表不存在")
            results["tenant"] = {"exists": False, "count": 0}

        # 7. 获取用户邮箱信息用于测试
        print("\n[6] 获取用户邮箱信息...")
        cursor.execute("""
            SELECT id, email, nickname FROM user WHERE id IN (
                SELECT user_id FROM user_tenant WHERE role = 'normal'
            )
        """)
        normal_users = cursor.fetchall()
        if normal_users:
            print(f"    可用于测试的normal角色用户:")
            for u in normal_users:
                print(f"      - email: {u[1]}, nickname: {u[2]}, id: {u[0]}")

        # 也获取owner用户
        cursor.execute("""
            SELECT id, email, nickname FROM user LIMIT 5
        """)
        all_users = cursor.fetchall()
        print(f"\n    所有用户:")
        for u in all_users:
            cursor.execute("SELECT role, tenant_id FROM user_tenant WHERE user_id = %s", (u[0],))
            roles = cursor.fetchall()
            role_str = ", ".join([f"{r[0]}@{r[1][:8]}" for r in roles])
            print(f"      - email: {u[1]}, roles: {role_str}")
        print("\n" + "=" * 60)
        print("综合分析")
        print("=" * 60)

        issues = []

        if not results.get("team_permission_share", {}).get("exists"):
            issues.append("team_permission_share 表不存在")
        elif results.get("team_permission_share", {}).get("count", 0) == 0:
            issues.append("team_permission_share 表无数据 - 这是团队成员看不到共享文件夹的主要原因！")

        if not results.get("user_tenant", {}).get("exists"):
            issues.append("user_tenant 表不存在")
        elif results.get("user_tenant", {}).get("count", 0) == 0:
            issues.append("user_tenant 表无数据 - 团队成员未正确关联到租户")
        else:
            # 检查是否有非 owner 角色的用户
            cursor.execute("SELECT COUNT(*) FROM user_tenant WHERE role = 'normal'")
            normal_count = cursor.fetchone()[0]
            if normal_count == 0:
                issues.append("user_tenant 表中无 role='normal' 的记录 - 团队成员未以普通成员身份加入任何租户！")
                print(f"\n    ⚠️ 发现: user_tenant 表中所有用户的角色都是 'owner'，没有 'normal' 角色")
                print("    这意味着用户没有被邀请为团队成员，只能看到自己的文件")

        # 6. 详细分析 team_permission_share 和 user_tenant 的关联
        print("\n[5] 分析团队共享与用户关联...")
        cursor.execute("""
            SELECT
                tps.file_id,
                tps.tenant_id as shared_tenant_id,
                tps.permission_level,
                tps.is_enabled,
                f.name as file_name,
                f.created_by as file_owner
            FROM team_permission_share tps
            LEFT JOIN file f ON tps.file_id = f.id
            WHERE tps.is_enabled = 1
        """)
        shared_records = cursor.fetchall()
        print(f"    已启用的团队共享记录: {len(shared_records)}")
        for record in shared_records:
            print(f"      文件: {record[4]}, 共享给租户: {record[1]}, 权限: {record[2]}")

        # 检查哪些用户属于这些租户
        if shared_records:
            shared_tenant_ids = [r[1] for r in shared_records]
            placeholders = ','.join(['%s'] * len(shared_tenant_ids))
            cursor.execute(f"""
                SELECT
                    ut.user_id,
                    ut.tenant_id,
                    ut.role,
                    u.email as user_email
                FROM user_tenant ut
                LEFT JOIN user u ON ut.user_id = u.id
                WHERE ut.tenant_id IN ({placeholders}) AND ut.role = 'normal'
            """, shared_tenant_ids)
            normal_users = cursor.fetchall()
            print(f"\n    属于这些租户的普通成员(normal): {len(normal_users)}")
            if len(normal_users) == 0:
                issues.append("没有用户以 'normal' 角色加入被共享的租户 - 这是看不到共享文件夹的直接原因！")
            for user in normal_users:
                print(f"      用户: {user[3]}, 租户: {user[1]}, 角色: {user[2]}")

                # 模拟用户查询共享文件夹
                user_id = user[0]
                tenant_id = user[1]
                cursor.execute("""
                    SELECT
                        tps.file_id,
                        f.name as file_name,
                        tps.permission_level
                    FROM team_permission_share tps
                    LEFT JOIN file f ON tps.file_id = f.id
                    WHERE tps.tenant_id = %s
                      AND tps.is_enabled = 1
                      AND f.created_by != %s
                      AND f.tenant_id != %s
                """, (tenant_id, user_id, user_id))
                visible_shared = cursor.fetchall()
                print(f"        该用户应该能看到的共享文件夹:")
                for shared in visible_shared:
                    print(f"          - {shared[1]} (权限: {shared[2]})")

        if issues:
            print("\n发现的问题:")
            for i, issue in enumerate(issues, 1):
                print(f"  {i}. {issue}")
        else:
            print("\n✅ 数据层状态正常")

        cursor.close()

        return results

    except Exception as e:
        print(f"\n❌ 验证失败: {e}")
        import traceback
        traceback.print_exc()
        return None


if __name__ == "__main__":
    main()
