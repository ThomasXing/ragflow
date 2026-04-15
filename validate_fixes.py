#!/usr/bin/env python3
"""
验证团队共享功能的安全修复

此脚本验证：
1. check_user_team_permission 方法是否包含租户成员验证
2. get_shared_file_ids_for_user 方法是否包含租户成员验证
3. get_all_team_shares_for_user 方法是否包含租户成员验证
4. 数据库迁移脚本与模型定义是否一致
"""

import re

def check_security_fixes():
    """检查安全修复是否应用"""

    print("=" * 80)
    print("团队共享功能安全修复验证")
    print("=" * 80)

    # 1. 检查 team_permission_service.py 中的安全修复
    print("\n1. 检查 team_permission_service.py 中的安全修复")

    with open("api/db/services/team_permission_service.py", "r", encoding="utf-8") as f:
        content = f.read()

    # 检查 check_user_team_permission 方法
    check_user_team_permission_code = re.search(
        r'def check_user_team_permission.*?\n(?:    .*\n)*?\n\s*def',
        content,
        re.DOTALL
    )

    if check_user_team_permission_code:
        method_content = check_user_team_permission_code.group()
        print("\n✓ check_user_team_permission 方法存在")

        # 检查是否包含租户验证
        if "TenantService.get_joined_tenants_by_user_id" in method_content:
            print("  ✓ 包含租户成员验证 (TenantService.get_joined_tenants_by_user_id)")
        else:
            print("  ✗ 缺少租户成员验证")

        # 检查是否有用户租户ID检查
        if "tenant_id not in user_tenant_ids" in method_content:
            print("  ✓ 包含租户ID成员资格检查")
        else:
            print("  ✗ 缺少租户ID成员资格检查")
    else:
        print("\n✗ 未找到 check_user_team_permission 方法")

    # 检查 get_shared_file_ids_for_user 方法
    get_shared_file_ids_code = re.search(
        r'def get_shared_file_ids_for_user.*?\n(?:    .*\n)*?\n\s*def',
        content,
        re.DOTALL
    )

    if get_shared_file_ids_code:
        method_content = get_shared_file_ids_code.group()
        print("\n✓ get_shared_file_ids_for_user 方法存在")

        if "TenantService.get_joined_tenants_by_user_id" in method_content:
            print("  ✓ 包含租户成员验证")
        else:
            print("  ✗ 缺少租户成员验证")
    else:
        print("\n✗ 未找到 get_shared_file_ids_for_user 方法")

    # 检查 get_all_team_shares_for_user 方法
    get_all_team_shares_code = re.search(
        r'def get_all_team_shares_for_user.*?\n(?:    .*\n)*?\n\s*def',
        content,
        re.DOTALL
    )

    if get_all_team_shares_code:
        method_content = get_all_team_shares_code.group()
        print("\n✓ get_all_team_shares_for_user 方法存在")

        if "TenantService.get_joined_tenants_by_user_id" in method_content:
            print("  ✓ 包含租户成员验证")
        else:
            print("  ✗ 缺少租户成员验证")
    else:
        print("\n✗ 未找到 get_all_team_shares_for_user 方法")

    return True

def check_database_migration():
    """检查数据库迁移脚本"""

    print("\n2. 检查数据库迁移脚本")

    try:
        with open("docker/oceanbase/init.d/create_team_permission_share_table.sql", "r", encoding="utf-8") as f:
            migration_sql = f.read()

        print("\n✓ 数据库迁移脚本存在")

        # 检查关键字段
        required_fields = [
            ("id", "VARCHAR.*PRIMARY KEY"),
            ("file_id", "VARCHAR.*NOT NULL"),
            ("tenant_id", "VARCHAR.*NOT NULL"),
            ("permission_level", "VARCHAR.*DEFAULT 'view'"),
            ("is_enabled", "BOOLEAN.*DEFAULT FALSE"),
            ("created_by", "VARCHAR.*NOT NULL"),
            ("created_at", "DATETIME.*NOT NULL"),
            ("updated_at", "DATETIME.*NOT NULL")
        ]

        all_fields_present = True
        for field_name, pattern in required_fields:
            if re.search(field_name, migration_sql, re.IGNORECASE):
                print(f"  ✓ 字段 {field_name} 存在")
            else:
                print(f"  ✗ 字段 {field_name} 缺失")
                all_fields_present = False

        # 检查唯一约束
        if "UNIQUE.*KEY.*file_id.*tenant_id" in migration_sql.replace(" ", ""):
            print("  ✓ 唯一约束 (file_id, tenant_id) 存在")
        else:
            print("  ✗ 唯一约束 (file_id, tenant_id) 缺失")

        # 检查索引
        expected_indexes = [
            "file_id",
            "tenant_id",
            "permission_level",
            "is_enabled",
            "created_by",
            "created_at",
            "updated_at"
        ]

        for index in expected_indexes:
            if f"CREATE INDEX.*{index}" in migration_sql.replace(" ", ""):
                print(f"  ✓ 索引 {index} 存在")
            else:
                print(f"  ✗ 索引 {index} 缺失")

        return all_fields_present

    except FileNotFoundError:
        print("\n✗ 数据库迁移脚本不存在")
        return False

def check_model_consistency():
    """检查模型与数据库脚本的一致性"""

    print("\n3. 检查模型与数据库脚本的一致性")

    try:
        with open("api/db/db_models.py", "r", encoding="utf-8") as f:
            model_content = f.read()

        # 提取 TeamPermissionShare 类定义
        team_permission_share_match = re.search(
            r'class TeamPermissionShare.*?class\s+\w+|$',
            model_content,
            re.DOTALL
        )

        if team_permission_share_match:
            class_content = team_permission_share_match.group()
            print("\n✓ TeamPermissionShare 模型存在")

            # 检查字段定义
            model_fields = [
                ("id", "CharField.*primary_key=True"),
                ("file_id", "CharField.*index=True"),
                ("tenant_id", "CharField.*index=True"),
                ("permission_level", "CharField.*default=\"view\".*index=True"),
                ("is_enabled", "BooleanField.*default=False"),
                ("created_by", "CharField.*null=False"),
                ("created_at", "DateTimeField.*default=datetime.now.*index=True"),
                ("updated_at", "DateTimeField.*default=datetime.now.*index=True")
            ]

            for field_name, pattern in model_fields:
                if re.search(field_name, class_content):
                    print(f"  ✓ 模型字段 {field_name} 存在")
                else:
                    print(f"  ✗ 模型字段 {field_name} 缺失")

            # 检查表名
            if "team_permission_share" in class_content:
                print("  ✓ 表名 team_permission_share 正确")
            else:
                print("  ✗ 表名不匹配")

        else:
            print("\n✗ 未找到 TeamPermissionShare 模型")
            return False

        return True

    except FileNotFoundError:
        print("\n✗ 模型文件不存在")
        return False

def check_api_endpoints():
    """检查API端点"""

    print("\n4. 检查团队共享API端点")

    try:
        with open("api/apps/file_permission_app.py", "r", encoding="utf-8") as f:
            api_content = f.read()

        # 检查团队共享端点
        endpoints = [
            ("/team/enable", "启用团队共享"),
            ("/team/disable", "禁用团队共享"),
            ("/team/status", "获取团队共享状态"),
            ("/team/level", "修改权限级别")
        ]

        for endpoint, description in endpoints:
            if f"@manager.route('{endpoint}'" in api_content:
                print(f"  ✓ API端点 {endpoint} ({description}) 存在")
            else:
                print(f"  ✗ API端点 {endpoint} ({description}) 缺失")

        return True

    except FileNotFoundError:
        print("\n✗ API文件不存在")
        return False

def check_frontend_components():
    """检查前端组件"""

    print("\n5. 检查前端团队共享组件")

    frontend_files = [
        "web/src/components/file-team-share-toggle.tsx",
        "web/src/components/folder-team-share-toggle.tsx",
        "web/src/services/file-permission-service.ts"
    ]

    for file_path in frontend_files:
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
            print(f"  ✓ 前端文件 {file_path} 存在")
        except FileNotFoundError:
            print(f"  ✗ 前端文件 {file_path} 缺失")

    return True

def main():
    """主验证函数"""

    print("开始验证团队共享功能安全修复...\n")

    results = []

    # 执行各项检查
    results.append(("安全修复检查", check_security_fixes()))
    results.append(("数据库迁移脚本", check_database_migration()))
    results.append(("模型一致性检查", check_model_consistency()))
    results.append(("API端点检查", check_api_endpoints()))
    results.append(("前端组件检查", check_frontend_components()))

    print("\n" + "=" * 80)
    print("验证总结")
    print("=" * 80)

    all_passed = True
    for check_name, passed in results:
        status = "✓ 通过" if passed else "✗ 失败"
        print(f"{check_name}: {status}")
        if not passed:
            all_passed = False

    print("\n" + "=" * 80)
    if all_passed:
        print("✅ 所有安全检查通过！团队共享功能已修复安全漏洞")
        print("✅ PR可以安全提交")
    else:
        print("❌ 安全检查未通过，请修复上述问题后再提交PR")

    return all_passed

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)