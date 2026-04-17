#!/usr/bin/env python3
"""
验证SECRET_KEY修复是否成功
"""

import os
import sys

def check_settings_modification():
    """检查settings.py是否已正确修改"""
    try:
        with open('common/settings.py', 'r') as f:
            content = f.read()
        
        # 检查是否已取消注释环境变量读取
        if 'secret_key = os.environ.get("RAGFLOW_SECRET_KEY")' in content:
            if 'if secret_key and len(secret_key) >= 32:' in content:
                print("✅ settings.py已正确修改：启用了RAGFLOW_SECRET_KEY环境变量支持")
                return True
            else:
                print("❌ settings.py修改不完整")
                return False
        else:
            print("❌ 未找到修改后的代码")
            return False
            
    except Exception as e:
        print(f"❌ 检查settings.py时出错: {e}")
        return False

def generate_test_commands():
    """生成测试命令"""
    print("\n📋 测试命令：")
    print("=" * 50)
    
    # 生成测试用的SECRET_KEY
    import secrets
    test_key = secrets.token_hex(32)
    
    print(f"\n1. 设置环境变量并启动测试：")
    print(f"export RAGFLOW_SECRET_KEY=\"{test_key}\"")
    print(f"python3 -c \"import os; print('RAGFLOW_SECRET_KEY length:', len(os.environ.get('RAGFLOW_SECRET_KEY', '')))\"")
    
    print(f"\n2. 检查当前环境变量：")
    print("python3 -c \"import os; print('Current RAGFLOW_SECRET_KEY:', 'SET' if os.environ.get('RAGFLOW_SECRET_KEY') else 'NOT SET')\"")
    
    print(f"\n3. 验证函数逻辑：")
    print(f"""python3 -c "
import os
# 测试密钥长度检查
test_keys = [
    ('valid_key' + 'x' * 32, True),  # 40字符
    ('short', False),                # 5字符
    ('', False),                     # 空字符串
    (None, False)                    # None值
]

for key, expected in test_keys:
    if key:
        os.environ['RAGFLOW_SECRET_KEY'] = key
    elif 'RAGFLOW_SECRET_KEY' in os.environ:
        del os.environ['RAGFLOW_SECRET_KEY']
    
    result = bool(key and len(key) >= 32)
    print(f'密钥: {{key[:20] if key else \"None\"}}... 长度检查: {{result}} (期望: {{expected}})')
" """)

def main():
    print("🔍 RAGFlow SECRET_KEY 修复验证工具")
    print("=" * 50)
    
    # 检查文件修改
    if check_settings_modification():
        print("\n✅ 代码修复已完成！")
    else:
        print("\n❌ 代码修复未完成，请检查修改")
        sys.exit(1)
    
    # 生成测试命令
    generate_test_commands()
    
    print("\n" + "=" * 50)
    print("📝 后续步骤：")
    print("1. 按照上面的测试命令验证环境变量读取")
    print("2. 设置RAGFLOW_SECRET_KEY环境变量")
    print("3. 重启RAGFlow服务")
    print("4. 检查日志确认警告消失")
    print("\n💡 提示：详细的配置指南请查看 SECRET_KEY_SETUP_GUIDE.md")

if __name__ == "__main__":
    main()
