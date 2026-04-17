#!/usr/bin/env python3
"""
修复RAGFlow SECRET_KEY安全警告问题
1. 修改common/settings.py文件中的_get_or_create_secret_key函数
2. 生成并设置安全的SECRET_KEY环境变量
"""

import os
import secrets
import sys
from datetime import date

def fix_settings_py():
    """修复settings.py文件中的_get_or_create_secret_key函数"""
    settings_path = "common/settings.py"
    
    if not os.path.exists(settings_path):
        print(f"错误：找不到文件 {settings_path}")
        return False
    
    with open(settings_path, 'r') as f:
        content = f.read()
    
    # 查找_get_or_create_secret_key函数
    import os
    import secrets
    from datetime import date
    
    # 找到要替换的部分
    old_function = '''def _get_or_create_secret_key():
    # secret_key = os.environ.get("RAGFLOW_SECRET_KEY")
    # if secret_key and len(secret_key) >= 32:
    #     return secret_key
    #
    # # Check if there's a configured secret key
    # configured_key = get_base_config(RAG_FLOW_SERVICE_NAME, {}).get("secret_key")
    # if configured_key and configured_key != str(date.today()) and len(configured_key) >= 32:
    #     return configured_key

    # Generate a new secure key and warn about it
    import logging

    generated_key = secrets.token_hex(32)
    secret_key = REDIS_CONN.get_or_create_secret_key("ragflow:system:secret_key", generated_key)
    logging.warning("SECURITY WARNING: Using auto-generated SECRET_KEY.")
    return secret_key'''
    
    new_function = '''def _get_or_create_secret_key():
    secret_key = os.environ.get("RAGFLOW_SECRET_KEY")
    if secret_key and len(secret_key) >= 32:
        return secret_key

    # Check if there's a configured secret key
    configured_key = get_base_config(RAG_FLOW_SERVICE_NAME, {}).get("secret_key")
    if configured_key and configured_key != str(date.today()) and len(configured_key) >= 32:
        return configured_key

    # Generate a new secure key and warn about it
    import logging

    generated_key = secrets.token_hex(32)
    secret_key = REDIS_CONN.get_or_create_secret_key("ragflow:system:secret_key", generated_key)
    logging.warning("SECURITY WARNING: Using auto-generated SECRET_KEY.")
    return secret_key'''
    
    if old_function in content:
        content = content.replace(old_function, new_function)
        with open(settings_path, 'w') as f:
            f.write(content)
        print("✓ 已成功修改 common/settings.py 文件")
        return True
    else:
        print("⚠️ 找不到要替换的函数定义，可能代码结构已更改")
        return False

def generate_secret_key():
    """生成安全的SECRET_KEY"""
    secret_key = secrets.token_hex(32)
    print(f"生成的SECRET_KEY: {secret_key}")
    print(f"长度: {len(secret_key)} 字符")
    return secret_key

def create_env_template():
    """创建环境变量设置指南"""
    secret_key = generate_secret_key()
    
    template = f"""
# RAGFlow SECRET_KEY 配置指南

## 方法1：通过环境变量设置
在启动RAGFlow前，设置环境变量：
export RAGFLOW_SECRET_KEY="{secret_key}"

## 方法2：在Docker容器中设置
1. 停止当前容器：
docker stop docker-ragflow-cpu-1

2. 添加环境变量到docker/.env文件：
RAGFLOW_SECRET_KEY={secret_key}

3. 重启容器：
docker start docker-ragflow-cpu-1

## 方法3：在服务配置中设置
在 conf/service_conf.yaml 文件中添加：
ragflow:
  secret_key: "{secret_key}"
  host: 0.0.0.0
  http_port: 9380

## 验证方法
重启服务后，检查日志不再显示：
"SECURITY WARNING: Using auto-generated SECRET_KEY."
"""
    
    with open("SECRET_KEY_SETUP.md", "w") as f:
        f.write(template)
    
    print("\n✓ 已创建 SECRET_KEY_SETUP.md 文件")
    print("请按照指南配置SECRET_KEY，然后重启RAGFlow服务")

def main():
    print("=" * 60)
    print("RAGFlow SECRET_KEY 安全修复工具")
    print("=" * 60)
    
    # 1. 修复settings.py
    print("\n[步骤1] 修复 common/settings.py 文件...")
    if fix_settings_py():
        print("  设置已应用")
    else:
        print("  修复失败，请手动检查")
        sys.exit(1)
    
    # 2. 生成SECRET_KEY并创建配置指南
    print("\n[步骤2] 生成安全SECRET_KEY...")
    create_env_template()
    
    # 3. 显示重启指令
    print("\n[步骤3] 下一步操作:")
    print("  1. 按照 SECRET_KEY_SETUP.md 中的指南配置SECRET_KEY")
    print("  2. 重启RAGFlow服务使配置生效")
    print("  3. 验证日志中不再显示安全警告")
    print("\n[重要] 重启服务命令:")
    print("  docker restart docker-ragflow-cpu-1")
    
    print("\n" + "=" * 60)
    print("修复完成！")
    print("=" * 60)

if __name__ == "__main__":
    main()
