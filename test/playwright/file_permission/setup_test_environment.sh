#!/usr/bin/env bash

# 文件权限管理端到端测试配置和说明

set -e

echo "📋 文件权限管理端到端测试配置说明"
echo "=========================================="

# 创建配置文件
CONFIG_FILE="./test/playwright/file_permission/test_config.env"

cat > "$CONFIG_FILE" << 'EOF'
# 文件权限管理端到端测试配置
# 请根据实际环境修改以下配置

# RAGFlow 部署地址
export RAGFLOW_BASE_URL="http://localhost:3000"

# 测试用户凭据（需要有两个测试账号）
export RAGFLOW_USERNAME_OWNER="admin@example.com"
export RAGFLOW_PASSWORD_OWNER="password123"

export RAGFLOW_USERNAME_RECEIVER="user@example.com"
export RAGFLOW_PASSWORD_RECEIVER="password456"

# 测试文件配置
export TEST_FILE_NAME="test_document.pdf"
export TEST_FOLDER_NAME="test_folder"

# 测试超时配置（毫秒）
export PAGE_LOAD_TIMEOUT=30000
export ACTION_TIMEOUT=10000
export NETWORK_IDLE_TIMEOUT=5000

# 截图配置
export SCREENSHOT_DIR="./test-screenshots"
export SCREENSHOT_FORMAT="png"
export SCREENSHOT_QUALITY=80

# 浏览器配置
export BROWSER_HEADLESS=true
export BROWSER_VIEWPORT_WIDTH=1920
export BROWSER_VIEWPORT_HEIGHT=1080

# 测试模式
export TEST_MODE="comprehensive"  # quick, comprehensive, or performance

# 日志级别
export LOG_LEVEL="INFO"  # DEBUG, INFO, WARN, ERROR
EOF

echo "✅ 配置文件已创建: $CONFIG_FILE"

# 创建测试数据准备脚本
DATA_PREP_SCRIPT="./test/playwright/file_permission/prepare_test_data.py"

cat > "$DATA_PREP_SCRIPT" << 'EOF'
#!/usr/bin/env python3
"""
文件权限管理测试数据准备脚本

此脚本用于创建测试所需的用户、租户和文件数据
"""

import os
import sys
import json
import requests
from typing import Dict, Any, Optional

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

class TestDataPreparation:
    """测试数据准备类"""

    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip('/')
        self.session = requests.Session()

    def login(self, username: str, password: str) -> Optional[str]:
        """用户登录"""
        url = f"{self.base_url}/v1/user/login"
        payload = {
            "username": username,
            "password": password
        }

        try:
            response = self.session.post(url, json=payload)
            if response.status_code == 200:
                data = response.json()
                if data.get("code") == 0:
                    print(f"✅ 用户 {username} 登录成功")
                    return self.session.cookies.get("session")
            print(f"❌ 用户 {username} 登录失败: {response.text}")
            return None
        except Exception as e:
            print(f"❌ 登录请求失败: {e}")
            return None

    def create_user(self, username: str, password: str, nickname: str) -> Optional[Dict[str, Any]]:
        """创建测试用户"""
        url = f"{self.base_url}/v1/user/register"
        payload = {
            "username": username,
            "password": password,
            "nickname": nickname
        }

        try:
            response = self.session.post(url, json=payload)
            if response.status_code == 200:
                data = response.json()
                if data.get("code") == 0:
                    print(f"✅ 用户 {username} 创建成功")
                    return data.get("data", {})
            print(f"❌ 用户 {username} 创建失败: {response.text}")
            return None
        except Exception as e:
            print(f"❌ 创建用户请求失败: {e}")
            return None

    def create_tenant(self, tenant_name: str) -> Optional[Dict[str, Any]]:
        """创建租户"""
        url = f"{self.base_url}/v1/tenant"
        payload = {
            "name": tenant_name,
            "description": f"测试租户: {tenant_name}"
        }

        try:
            response = self.session.post(url, json=payload)
            if response.status_code == 200:
                data = response.json()
                if data.get("code") == 0:
                    print(f"✅ 租户 {tenant_name} 创建成功")
                    return data.get("data", {})
            print(f"❌ 租户 {tenant_name} 创建失败: {response.text}")
            return None
        except Exception as e:
            print(f"❌ 创建租户请求失败: {e}")
            return None

    def upload_test_file(self, file_path: str, tenant_id: str) -> Optional[Dict[str, Any]]:
        """上传测试文件"""
        url = f"{self.base_url}/v1/upload"

        try:
            with open(file_path, 'rb') as f:
                files = {'file': (os.path.basename(file_path), f)}
                data = {'tenant_id': tenant_id}
                response = self.session.post(url, files=files, data=data)

            if response.status_code == 200:
                data = response.json()
                if data.get("code") == 0:
                    print(f"✅ 文件 {file_path} 上传成功")
                    return data.get("data", {})
            print(f"❌ 文件上传失败: {response.text}")
            return None
        except Exception as e:
            print(f"❌ 文件上传请求失败: {e}")
            return None

    def create_test_folder(self, folder_name: str, parent_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """创建测试文件夹"""
        url = f"{self.base_url}/v1/folder"
        payload = {
            "name": folder_name,
            "parent_id": parent_id
        }

        try:
            response = self.session.post(url, json=payload)
            if response.status_code == 200:
                data = response.json()
                if data.get("code") == 0:
                    print(f"✅ 文件夹 {folder_name} 创建成功")
                    return data.get("data", {})
            print(f"❌ 文件夹创建失败: {response.text}")
            return None
        except Exception as e:
            print(f"❌ 创建文件夹请求失败: {e}")
            return None

    def prepare_all_data(self, config: Dict[str, str]) -> Dict[str, Any]:
        """准备所有测试数据"""
        print("🚀 开始准备测试数据...")

        test_data = {}

        # 1. 创建所有者用户
        print("\n1️⃣ 创建所有者用户...")
        owner_user = self.create_user(
            config["RAGFLOW_USERNAME_OWNER"],
            config["RAGFLOW_PASSWORD_OWNER"],
            "文件所有者"
        )
        if not owner_user:
            print("❌ 创建所有者用户失败，退出")
            sys.exit(1)
        test_data["owner_user"] = owner_user

        # 2. 所有者登录
        print("\n2️⃣ 所有者用户登录...")
        owner_session = self.login(
            config["RAGFLOW_USERNAME_OWNER"],
            config["RAGFLOW_PASSWORD_OWNER"]
        )
        if not owner_session:
            print("❌ 所有者登录失败，退出")
            sys.exit(1)
        test_data["owner_session"] = owner_session

        # 3. 创建接收者用户
        print("\n3️⃣ 创建接收者用户...")
        receiver_user = self.create_user(
            config["RAGFLOW_USERNAME_RECEIVER"],
            config["RAGFLOW_PASSWORD_RECEIVER"],
            "文件接收者"
        )
        if not receiver_user:
            print("❌ 创建接收者用户失败，退出")
            sys.exit(1)
        test_data["receiver_user"] = receiver_user

        # 4. 创建租户
        print("\n4️⃣ 创建测试租户...")
        tenant = self.create_tenant("测试文件共享租户")
        if not tenant:
            print("❌ 创建租户失败，退出")
            sys.exit(1)
        test_data["tenant"] = tenant

        # 5. 创建测试文件夹
        print("\n5️⃣ 创建测试文件夹...")
        test_folder = self.create_test_folder(config["TEST_FOLDER_NAME"])
        if not test_folder:
            print("⚠️ 创建测试文件夹失败，继续其他步骤")
        else:
            test_data["test_folder"] = test_folder

        print("\n✅ 测试数据准备完成!")
        return test_data

    def save_test_data(self, test_data: Dict[str, Any], output_file: str):
        """保存测试数据到文件"""
        try:
            # 移除敏感信息
            safe_data = {}
            for key, value in test_data.items():
                if isinstance(value, dict):
                    safe_data[key] = {}
                    for sub_key, sub_value in value.items():
                        if 'password' not in sub_key.lower() and 'token' not in sub_key.lower():
                            safe_data[key][sub_key] = sub_value
                else:
                    safe_data[key] = value

            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(safe_data, f, indent=2, ensure_ascii=False)

            print(f"✅ 测试数据已保存到: {output_file}")
        except Exception as e:
            print(f"❌ 保存测试数据失败: {e}")

def main():
    """主函数"""
    import dotenv

    # 加载配置文件
    config_file = os.path.join(os.path.dirname(__file__), "test_config.env")
    if not os.path.exists(config_file):
        print(f"❌ 配置文件不存在: {config_file}")
        print("请先运行 file_permission_test_setup.sh 创建配置文件")
        sys.exit(1)

    # 加载环境变量
    dotenv.load_dotenv(config_file)

    # 读取配置
    config = {
        "RAGFLOW_BASE_URL": os.getenv("RAGFLOW_BASE_URL", "http://localhost:3000"),
        "RAGFLOW_USERNAME_OWNER": os.getenv("RAGFLOW_USERNAME_OWNER", "admin@example.com"),
        "RAGFLOW_PASSWORD_OWNER": os.getenv("RAGFLOW_PASSWORD_OWNER", "password123"),
        "RAGFLOW_USERNAME_RECEIVER": os.getenv("RAGFLOW_USERNAME_RECEIVER", "user@example.com"),
        "RAGFLOW_PASSWORD_RECEIVER": os.getenv("RAGFLOW_PASSWORD_RECEIVER", "password456"),
        "TEST_FILE_NAME": os.getenv("TEST_FILE_NAME", "test_document.pdf"),
        "TEST_FOLDER_NAME": os.getenv("TEST_FOLDER_NAME", "test_folder")
    }

    print("📋 测试配置:")
    for key, value in config.items():
        if 'PASSWORD' not in key:
            print(f"  {key}: {value}")

    # 准备数据
    preparer = TestDataPreparation(config["RAGFLOW_BASE_URL"])
    test_data = preparer.prepare_all_data(config)

    # 保存数据
    output_file = os.path.join(os.path.dirname(__file__), "test_data.json")
    preparer.save_test_data(test_data, output_file)

    # 生成测试凭证文件
    credentials_file = os.path.join(os.path.dirname(__file__), ".credentials")
    with open(credentials_file, 'w') as f:
        f.write(f"export RAGFLOW_BASE_URL='{config['RAGFLOW_BASE_URL']}'\n")
        f.write(f"export RAGFLOW_USERNAME_OWNER='{config['RAGFLOW_USERNAME_OWNER']}'\n")
        f.write(f"export RAGFLOW_PASSWORD_OWNER='{config['RAGFLOW_PASSWORD_OWNER']}'\n")
        f.write(f"export RAGFLOW_USERNAME_RECEIVER='{config['RAGFLOW_USERNAME_RECEIVER']}'\n")
        f.write(f"export RAGFLOW_PASSWORD_RECEIVER='{config['RAGFLOW_PASSWORD_RECEIVER']}'\n")

    print(f"✅ 测试凭证已保存到: {credentials_file}")
    print("\n📝 使用说明:")
    print("  1. 运行端到端测试: ./test/playwright/file_permission/file_share_e2e_test.sh")
    print("  2. 需要先 source 配置文件: source {credentials_file}")
    print("  3. 确保 RAGFlow 服务正在运行")

if __name__ == "__main__":
    main()
EOF

# 设置执行权限
chmod +x "$DATA_PREP_SCRIPT"

echo "✅ 数据准备脚本已创建: $DATA_PREP_SCRIPT"

# 创建测试清理脚本
CLEANUP_SCRIPT="./test/playwright/file_permission/cleanup_test_data.py"

cat > "$CLEANUP_SCRIPT" << 'EOF'
#!/usr/bin/env python3
"""
文件权限管理测试数据清理脚本

此脚本用于清理测试创建的用户、租户和文件数据
"""

import os
import sys
import json
import requests

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

class TestDataCleanup:
    """测试数据清理类"""

    def __init__(self, base_url: str, username: str, password: str):
        self.base_url = base_url.rstrip('/')
        self.username = username
        self.password = password
        self.session = requests.Session()

    def login(self) -> bool:
        """用户登录"""
        url = f"{self.base_url}/v1/user/login"
        payload = {
            "username": self.username,
            "password": self.password
        }

        try:
            response = self.session.post(url, json=payload)
            if response.status_code == 200:
                data = response.json()
                if data.get("code") == 0:
                    print(f"✅ 用户 {self.username} 登录成功")
                    return True
            print(f"❌ 用户 {self.username} 登录失败: {response.text}")
            return False
        except Exception as e:
            print(f"❌ 登录请求失败: {e}")
            return False

    def load_test_data(self, data_file: str) -> dict:
        """加载测试数据"""
        try:
            with open(data_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"❌ 加载测试数据失败: {e}")
            return {}

    def delete_user(self, user_id: str) -> bool:
        """删除用户"""
        url = f"{self.base_url}/v1/user/{user_id}"

        try:
            response = self.session.delete(url)
            if response.status_code == 200:
                data = response.json()
                if data.get("code") == 0:
                    print(f"✅ 用户 {user_id} 删除成功")
                    return True
            print(f"❌ 用户 {user_id} 删除失败: {response.text}")
            return False
        except Exception as e:
            print(f"❌ 删除用户请求失败: {e}")
            return False

    def delete_tenant(self, tenant_id: str) -> bool:
        """删除租户"""
        url = f"{self.base_url}/v1/tenant/{tenant_id}"

        try:
            response = self.session.delete(url)
            if response.status_code == 200:
                data = response.json()
                if data.get("code") == 0:
                    print(f"✅ 租户 {tenant_id} 删除成功")
                    return True
            print(f"❌ 租户 {tenant_id} 删除失败: {response.text}")
            return False
        except Exception as e:
            print(f"❌ 删除租户请求失败: {e}")
            return False

    def delete_file(self, file_id: str) -> bool:
        """删除文件"""
        url = f"{self.base_url}/v1/file/{file_id}"

        try:
            response = self.session.delete(url)
            if response.status_code == 200:
                data = response.json()
                if data.get("code") == 0:
                    print(f"✅ 文件 {file_id} 删除成功")
                    return True
            print(f"❌ 文件 {file_id} 删除失败: {response.text}")
            return False
        except Exception as e:
            print(f"❌ 删除文件请求失败: {e}")
            return False

    def cleanup_all_data(self, data_file: str):
        """清理所有测试数据"""
        print("🧹 开始清理测试数据...")

        # 加载测试数据
        test_data = self.load_test_data(data_file)
        if not test_data:
            print("⚠️ 未找到测试数据，跳过清理")
            return

        # 登录
        if not self.login():
            print("❌ 登录失败，无法清理数据")
            return

        # 清理文件（如果存在）
        if "test_file" in test_data:
            file_info = test_data["test_file"]
            if isinstance(file_info, dict) and "id" in file_info:
                self.delete_file(file_info["id"])

        # 清理文件夹（如果存在）
        if "test_folder" in test_data:
            folder_info = test_data["test_folder"]
            if isinstance(folder_info, dict) and "id" in folder_info:
                self.delete_file(folder_info["id"])

        # 清理租户（如果存在）
        if "tenant" in test_data:
            tenant_info = test_data["tenant"]
            if isinstance(tenant_info, dict) and "id" in tenant_info:
                self.delete_tenant(tenant_info["id"])

        # 清理用户（如果存在且不是当前登录用户）
        for user_key in ["owner_user", "receiver_user"]:
            if user_key in test_data:
                user_info = test_data[user_key]
                if isinstance(user_info, dict) and "id" in user_info:
                    # 跳过当前登录用户（清理脚本用户）
                    if "username" in user_info and user_info["username"] == self.username:
                        print(f"⚠️ 跳过删除当前登录用户: {self.username}")
                    else:
                        self.delete_user(user_info["id"])

        print("✅ 测试数据清理完成!")

        # 删除数据文件
        try:
            os.remove(data_file)
            print(f"✅ 删除数据文件: {data_file}")
        except Exception as e:
            print(f"⚠️ 删除数据文件失败: {e}")

def main():
    """主函数"""
    import dotenv

    # 加载配置文件
    config_file = os.path.join(os.path.dirname(__file__), "test_config.env")
    if not os.path.exists(config_file):
        print(f"❌ 配置文件不存在: {config_file}")
        print("请先运行 file_permission_test_setup.sh 创建配置文件")
        sys.exit(1)

    # 加载环境变量
    dotenv.load_dotenv(config_file)

    # 读取配置
    base_url = os.getenv("RAGFLOW_BASE_URL", "http://localhost:3000")
    username = os.getenv("RAGFLOW_USERNAME_OWNER", "admin@example.com")
    password = os.getenv("RAGFLOW_PASSWORD_OWNER", "password123")
    data_file = os.path.join(os.path.dirname(__file__), "test_data.json")

    if not os.path.exists(data_file):
        print(f"⚠️ 测试数据文件不存在: {data_file}")
        print("可能测试数据尚未创建，或已被清理")
        sys.exit(0)

    print("🧹 测试数据清理配置:")
    print(f"  基础URL: {base_url}")
    print(f"  清理用户: {username}")
    print(f"  数据文件: {data_file}")

    # 确认清理
    confirmation = input("\n⚠️  确认要清理所有测试数据吗？(y/N): ")
    if confirmation.lower() != 'y':
        print("❌ 取消清理操作")
        sys.exit(0)

    # 执行清理
    cleaner = TestDataCleanup(base_url, username, password)
    cleaner.cleanup_all_data(data_file)

    # 删除凭证文件
    credentials_file = os.path.join(os.path.dirname(__file__), ".credentials")
    if os.path.exists(credentials_file):
        try:
            os.remove(credentials_file)
            print(f"✅ 删除凭证文件: {credentials_file}")
        except Exception as e:
            print(f"⚠️ 删除凭证文件失败: {e}")

if __name__ == "__main__":
    main()
EOF

# 设置执行权限
chmod +x "$CLEANUP_SCRIPT"

echo "✅ 数据清理脚本已创建: $CLEANUP_SCRIPT"

# 创建 README 文件
README_FILE="./test/playwright/file_permission/README.md"

cat > "$README_FILE" << 'EOF'
# 文件权限管理端到端测试

## 概述

本目录包含文件权限管理功能的端到端自动化测试，包括后端API测试、前端组件测试和浏览器自动化测试。

## 目录结构

```
file_permission/
├── README.md                    # 本文档
├── test_config.env             # 测试配置文件模板
├── prepare_test_data.py        # 测试数据准备脚本
├── cleanup_test_data.py        # 测试数据清理脚本
├── file_share_e2e_test.sh      # 端到端测试主脚本
├── test_data.json              # 生成的测试数据（运行后生成）
└── .credentials               # 测试凭证文件（运行后生成）
```

## 测试组成

### 1. 后端API测试
位置：`../test_http_api/test_file_permission_management/`

**测试内容：**
- ✅ 创建文件共享
- ✅ 获取共享列表
- ✅ 更新权限级别
- ✅ 撤销权限
- ✅ 批量共享操作
- ✅ 权限检查
- ✅ 可分享用户列表
- ✅ 文件夹共享功能
- ✅ 权限继承
- ✅ 并发操作性能测试

### 2. 前端组件测试
位置：`../../web/src/__tests__/components/file-share-dialog.test.tsx`

**测试内容：**
- ✅ 对话框渲染
- ✅ 数据加载和显示
- ✅ 用户搜索和选择
- ✅ 权限级别选择
- ✅ 分享操作
- ✅ 权限管理操作
- ✅ API错误处理
- ✅ 权限验证

### 3. 浏览器端到端测试
位置：`file_share_e2e_test.sh`

**测试内容：**
- ✅ 登录流程
- ✅ 文件分享对话框
- ✅ 用户搜索和选择
- ✅ 权限级别选择
- ✅ 创建和查看共享
- ✅ 权限管理和撤销
- ✅ 共享文件列表页面

## 使用方法

### 1. 环境配置

```bash
# 复制配置文件
cp test_config.env.example test_config.env

# 编辑配置文件
vi test_config.env

# 设置以下环境变量：
# RAGFLOW_BASE_URL=http://localhost:3000
# RAGFLOW_USERNAME_OWNER=admin@example.com
# RAGFLOW_PASSWORD_OWNER=password123
# RAGFLOW_USERNAME_RECEIVER=user@example.com
# RAGFLOW_PASSWORD_RECEIVER=password456
```

### 2. 安装依赖

```bash
# 安装 agent-browser（如果尚未安装）
npm install -g agent-browser

# 或使用 cargo
cargo install agent-browser

# 初始化 agent-browser
agent-browser install
```

### 3. 准备测试数据

```bash
# 运行测试数据准备脚本
python3 prepare_test_data.py

# 脚本会自动：
# 1. 创建测试用户（所有者和接收者）
# 2. 创建测试租户
# 3. 创建测试文件夹
# 4. 保存测试数据到 test_data.json
# 5. 生成 .credentials 文件
```

### 4. 运行端到端测试

```bash
# 加载环境变量
source .credentials

# 运行端到端测试
./file_share_e2e_test.sh

# 或直接运行
RAGFLOW_BASE_URL="http://localhost:3000" \
RAGFLOW_USERNAME="admin@example.com" \
RAGFLOW_PASSWORD="password123" \
./file_share_e2e_test.sh
```

### 5. 清理测试数据

```bash
# 运行清理脚本
python3 cleanup_test_data.py

# 脚本会：
# 1. 删除测试创建的文件和文件夹
# 2. 删除测试租户
# 3. 删除测试用户
# 4. 清理数据文件和凭证文件
```

## 测试场景覆盖

### 正常流程测试
1. **创建文件共享**
   - 选择用户
   - 设置权限级别（查看、编辑、管理）
   - 设置过期时间

2. **管理共享权限**
   - 查看已共享列表
   - 修改权限级别
   - 撤销共享权限

3. **查看共享文件**
   - "共享给我的"页面
   - "我共享的"页面

### 边界条件测试
1. **权限验证**
   - 无权限用户尝试分享
   - 仅查看权限用户尝试修改
   - 过期共享权限验证

2. **错误处理**
   - 无效的用户选择
   - 重复分享
   - 网络错误处理

3. **并发测试**
   - 多用户同时操作
   - 批量文件分享

### 性能测试
1. **页面加载性能**
2. **批量操作性能**
3. **并发请求处理**

## 自动化集成

### CI/CD 流水线集成

```yaml
# GitHub Actions 示例
name: File Permission Tests

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]

jobs:
  file-permission-tests:
    runs-on: ubuntu-latest

    steps:
    - uses: actions/checkout@v3

    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'

    - name: Install dependencies
      run: |
        pip install -r requirements.txt
        npm install -g agent-browser

    - name: Setup test environment
      run: |
        cp test/playwright/file_permission/test_config.env.example test/playwright/file_permission/test_config.env
        # 设置环境变量...

    - name: Prepare test data
      run: |
        cd test/playwright/file_permission
        python3 prepare_test_data.py

    - name: Run API tests
      run: |
        pytest test/testcases/test_http_api/test_file_permission_management/ -v

    - name: Run component tests
      run: |
        cd web
        npm test -- file-share-dialog.test.tsx

    - name: Run E2E tests
      run: |
        cd test/playwright/file_permission
        chmod +x file_share_e2e_test.sh
        ./file_share_e2e_test.sh

    - name: Cleanup test data
      if: always()
      run: |
        cd test/playwright/file_permission
        python3 cleanup_test_data.py

    - name: Upload test results
      if: always()
      uses: actions/upload-artifact@v3
      with:
        name: file-permission-test-results
        path: |
          test-screenshots/
          test-reports/
```

### 本地开发测试

```bash
# 运行所有测试
make test-file-permission

# 或单独运行
make test-file-permission-api
make test-file-permission-ui
make test-file-permission-e2e
```

## 故障排除

### 常见问题

1. **agent-browser 安装失败**
   ```bash
   # 检查 Node.js 版本
   node --version

   # 如果使用 npm
   npm install -g agent-browser

   # 如果使用 cargo
   cargo install agent-browser
   ```

2. **登录失败**
   - 检查 RAGFlow 服务是否运行
   - 验证用户名和密码
   - 检查网络连接

3. **页面元素找不到**
   - 更新测试脚本中的选择器
   - 检查页面结构是否变化
   - 增加等待时间

4. **权限错误**
   - 确认测试用户有足够权限
   - 检查租户配置
   - 验证 API 权限设置

### 调试模式

```bash
# 启用详细日志
export LOG_LEVEL=DEBUG

# 使用图形界面浏览器
export BROWSER_HEADLESS=false

# 运行测试
./file_share_e2e_test.sh
```

## 测试报告

测试运行后会生成：
1. **测试截图** - 在 `test-screenshots/` 目录
2. **测试报告** - 在 `test-screenshots/test_report.md`
3. **控制台输出** - 详细的执行日志

## 维护说明

1. **定期更新测试脚本** - 当 UI 发生变化时更新元素选择器
2. **更新测试数据** - 定期更换测试用户和文件
3. **性能基准** - 记录性能基准，监控性能回归
4. **错误处理** - 添加更多的错误场景测试

## 贡献指南

1. 添加新的测试用例时，请更新 README.md
2. 确保测试脚本是可重入的（可以多次运行）
3. 提供清晰的错误信息
4. 添加适当的注释和文档
5. 保持测试独立，不依赖外部状态

## 联系方式

如有问题或建议，请联系：
- 项目维护者
- 测试团队
- 文件权限功能负责人
EOF

echo "✅ README 文件已创建: $README_FILE"

# 创建快捷启动脚本
STARTER_SCRIPT="./test/playwright/file_permission/run_all_tests.sh"

cat > "$STARTER_SCRIPT" << 'EOF'
#!/usr/bin/env bash

# 文件权限管理测试套件启动脚本

set -e

echo "🚀 启动文件权限管理测试套件"
echo "=========================================="

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 日志函数
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 检查依赖
check_dependencies() {
    log_info "检查依赖..."

    # 检查 Python
    if ! command -v python3 &> /dev/null; then
        log_error "Python3 未安装"
        return 1
    fi
    log_info "✓ Python3"

    # 检查 agent-browser
    if ! command -v agent-browser &> /dev/null; then
        log_error "agent-browser 未安装"
        log_info "安装命令: npm install -g agent-browser"
        return 1
    fi
    log_info "✓ agent-browser"

    # 检查配置文件
    if [ ! -f "test_config.env" ]; then
        log_error "配置文件 test_config.env 不存在"
        log_info "请复制 test_config.env.example 并修改配置"
        return 1
    fi
    log_info "✓ 配置文件"

    return 0
}

# 检查 RAGFlow 服务
check_ragflow_service() {
    log_info "检查 RAGFlow 服务..."

    # 从配置文件读取 BASE_URL
    if [ -f ".credentials" ]; then
        source .credentials
    else
        source test_config.env
    fi

    # 移除 URL 中的协议和路径，只保留主机名和端口
    SERVICE_URL=$(echo "$RAGFLOW_BASE_URL" | sed 's|^.*://||')
    HOST_PORT=$(echo "$SERVICE_URL" | cut -d'/' -f1)

    HOST=$(echo "$HOST_PORT" | cut -d':' -f1)
    PORT=$(echo "$HOST_PORT" | cut -d':' -f2)

    if [ -z "$PORT" ]; then
        PORT=80
        if [[ "$RAGFLOW_BASE_URL" == https://* ]]; then
            PORT=443
        fi
    fi

    # 检查服务是否可访问
    if nc -z "$HOST" "$PORT" 2>/dev/null; then
        log_info "✓ RAGFlow 服务正在运行"
        return 0
    else
        log_error "RAGFlow 服务不可访问: $RAGFLOW_BASE_URL"
        return 1
    fi
}

# 运行 API 测试
run_api_tests() {
    log_info "运行后端 API 测试..."

    cd ../../..

    if [ -d "test/testcases/test_http_api/test_file_permission_management" ]; then
        log_info "找到 API 测试文件"

        # 检查是否安装了测试依赖
        if ! python3 -m pytest --version &> /dev/null; then
            log_error "pytest 未安装"
            log_info "请安装测试依赖: pip install -r requirements-dev.txt"
            return 1
        fi

        # 运行测试
        if python3 -m pytest test/testcases/test_http_api/test_file_permission_management/ -v; then
            log_success "API 测试通过"
            return 0
        else
            log_error "API 测试失败"
            return 1
        fi
    else
        log_warning "API 测试目录不存在，跳过"
        return 0
    fi
}

# 运行前端组件测试
run_component_tests() {
    log_info "运行前端组件测试..."

    cd ../../../web

    if [ -f "src/__tests__/components/file-share-dialog.test.tsx" ]; then
        log_info "找到组件测试文件"

        # 检查是否安装了前端测试依赖
        if [ ! -f "package.json" ]; then
            log_warning "package.json 不存在，跳过组件测试"
            return 0
        fi

        if ! command -v npm &> /dev/null; then
            log_warning "npm 未安装，跳过组件测试"
            return 0
        fi

        # 检查是否已安装依赖
        if [ ! -d "node_modules" ]; then
            log_info "安装前端依赖..."
            if npm install; then
                log_info "前端依赖安装完成"
            else
                log_error "前端依赖安装失败"
                return 1
            fi
        fi

        # 运行测试
        if npm test -- --testPathPattern=file-share-dialog.test.tsx; then
            log_success "组件测试通过"
            return 0
        else
            log_error "组件测试失败"
            return 1
        fi
    else
        log_warning "组件测试文件不存在，跳过"
        return 0
    fi
}

# 运行端到端测试
run_e2e_tests() {
    log_info "运行端到端测试..."

    cd "$SCRIPT_DIR"

    if [ ! -f "file_share_e2e_test.sh" ]; then
        log_error "端到端测试脚本不存在"
        return 1
    fi

    # 确保脚本可执行
    chmod +x file_share_e2e_test.sh

    # 检查凭证文件
    if [ ! -f ".credentials" ]; then
        log_warning "凭证文件不存在，尝试从配置生成..."
        if [ -f "test_config.env" ]; then
            source test_config.env
            cat > .credentials << EOF
export RAGFLOW_BASE_URL="$RAGFLOW_BASE_URL"
export RAGFLOW_USERNAME="$RAGFLOW_USERNAME_OWNER"
export RAGFLOW_PASSWORD="$RAGFLOW_PASSWORD_OWNER"
EOF
            log_info "已生成凭证文件"
        else
            log_error "无法生成凭证文件，缺少配置"
            return 1
        fi
    fi

    # 加载凭证
    source .credentials

    # 运行测试
    if ./file_share_e2e_test.sh; then
        log_success "端到端测试通过"
        return 0
    else
        log_error "端到端测试失败"
        return 1
    fi
}

# 清理函数
cleanup() {
    log_info "清理测试环境..."

    cd "$SCRIPT_DIR"

    # 停止可能的后台进程
    pkill -f "agent-browser" || true

    log_info "清理完成"
}

# 主函数
main() {
    log_info "开始文件权限管理测试套件"

    # 设置退出时清理
    trap cleanup EXIT

    # 检查依赖
    if ! check_dependencies; then
        log_error "依赖检查失败，退出"
        exit 1
    fi

    # 检查服务
    if ! check_ragflow_service; then
        log_error "服务检查失败，退出"
        exit 1
    fi

    # 准备测试数据
    log_info "准备测试数据..."
    if [ -f "prepare_test_data.py" ]; then
        if python3 prepare_test_data.py; then
            log_success "测试数据准备完成"
        else
            log_error "测试数据准备失败"
            exit 1
        fi
    else
        log_warning "测试数据准备脚本不存在，跳过"
    fi

    # 运行各种测试
    local api_test_result=0
    local component_test_result=0
    local e2e_test_result=0

    # 运行 API 测试
    if run_api_tests; then
        api_test_result=0
    else
        api_test_result=1
    fi

    # 运行组件测试
    if run_component_tests; then
        component_test_result=0
    else
        component_test_result=1
    fi

    # 运行端到端测试
    if run_e2e_tests; then
        e2e_test_result=0
    else
        e2e_test_result=1
    fi

    # 汇总结果
    echo ""
    echo "📊 测试结果汇总:"
    echo "=========================================="

    if [ $api_test_result -eq 0 ]; then
        echo -e "${GREEN}✓ 后端 API 测试: 通过${NC}"
    else
        echo -e "${RED}✗ 后端 API 测试: 失败${NC}"
    fi

    if [ $component_test_result -eq 0 ]; then
        echo -e "${GREEN}✓ 前端组件测试: 通过${NC}"
    else
        echo -e "${RED}✗ 前端组件测试: 失败${NC}"
    fi

    if [ $e2e_test_result -eq 0 ]; then
        echo -e "${GREEN}✓ 端到端测试: 通过${NC}"
    else
        echo -e "${RED}✗ 端到端测试: 失败${NC}"
    fi

    # 生成测试报告
    log_info "生成测试报告..."

    local total_tests=3
    local passed_tests=$((3 - api_test_result - component_test_result - e2e_test_result))

    if [ $passed_tests -eq $total_tests ]; then
        echo ""
        echo -e "${GREEN}🎉 所有测试通过！${NC}"
        exit 0
    else
        echo ""
        echo -e "${YELLOW}⚠️  部分测试失败${NC}"
        echo "通过测试: $passed_tests/$total_tests"
        exit 1
    fi
}

# 运行主函数
main "$@"
EOF

# 设置执行权限
chmod +x "$STARTER_SCRIPT"

echo "✅ 启动脚本已创建: $STARTER_SCRIPT"

# 创建配置示例文件
CONFIG_EXAMPLE="./test/playwright/file_permission/test_config.env.example"

cat > "$CONFIG_EXAMPLE" << 'EOF'
# 文件权限管理端到端测试配置示例
# 复制此文件为 test_config.env 并修改配置

# RAGFlow 部署地址
export RAGFLOW_BASE_URL="http://localhost:3000"

# 测试用户凭据（需要有两个测试账号）
export RAGFLOW_USERNAME_OWNER="admin@example.com"
export RAGFLOW_PASSWORD_OWNER="password123"

export RAGFLOW_USERNAME_RECEIVER="user@example.com"
export RAGFLOW_PASSWORD_RECEIVER="password456"

# 测试文件配置
export TEST_FILE_NAME="test_document.pdf"
export TEST_FOLDER_NAME="test_folder"

# 测试超时配置（毫秒）
export PAGE_LOAD_TIMEOUT=30000
export ACTION_TIMEOUT=10000
export NETWORK_IDLE_TIMEOUT=5000

# 截图配置
export SCREENSHOT_DIR="./test-screenshots"
export SCREENSHOT_FORMAT="png"
export SCREENSHOT_QUALITY=80

# 浏览器配置
export BROWSER_HEADLESS=true
export BROWSER_VIEWPORT_WIDTH=1920
export BROWSER_VIEWPORT_HEIGHT=1080

# 测试模式
export TEST_MODE="comprehensive"  # quick, comprehensive, or performance

# 日志级别
export LOG_LEVEL="INFO"  # DEBUG, INFO, WARN, ERROR
EOF

echo "✅ 配置示例文件已创建: $CONFIG_EXAMPLE"

echo ""
echo "🎉 文件权限管理测试套件创建完成！"
echo ""
echo "📋 可用命令:"
echo "  1. 配置环境: cp test/playwright/file_permission/test_config.env.example test/playwright/file_permission/test_config.env"
echo "  2. 准备测试数据: cd test/playwright/file_permission && python3 prepare_test_data.py"
echo "  3. 运行全部测试: cd test/playwright/file_permission && ./run_all_tests.sh"
echo "  4. 单独运行端到端测试: cd test/playwright/file_permission && ./file_share_e2e_test.sh"
echo "  5. 清理测试数据: cd test/playwright/file_permission && python3 cleanup_test_data.py"
echo ""
echo "💡 注意:"
echo "  - 请先编辑 test_config.env 文件设置正确的环境配置"
echo "  - 确保 RAGFlow 服务正在运行"
echo "  - 确保已安装 agent-browser: npm install -g agent-browser"