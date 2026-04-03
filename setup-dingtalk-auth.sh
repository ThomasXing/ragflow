#!/bin/bash

# RAGFlow 钉钉 OAuth 快速配置脚本
# 用法: ./setup-dingtalk-auth.sh YOUR_APP_KEY YOUR_APP_SECRET YOUR_DOMAIN

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== RAGFlow 钉钉 OAuth 配置工具 ===${NC}\n"

# 检查参数
if [ $# -lt 3 ]; then
    echo -e "${YELLOW}使用方法:${NC}"
    echo "  $0 APP_KEY APP_SECRET DOMAIN"
    echo ""
    echo -e "${YELLOW}参数说明:${NC}"
    echo "  APP_KEY     钉钉应用的 AppKey"
    echo "  APP_SECRET  钉钉应用的 AppSecret"
    echo "  DOMAIN      您的域名（用于生产环境）"
    echo ""
    echo -e "${YELLOW}示例:${NC}"
    echo "  本地开发: $0 ding1234567890 abcdefg123456 localhost"
    echo "  生产环境: $0 ding1234567890 abcdefg123456 your-domain.com"
    echo ""
    exit 1
fi

APP_KEY=$1
APP_SECRET=$2
DOMAIN=$3

echo -e "${YELLOW}配置信息:${NC}"
echo "  AppKey: $APP_KEY"
echo "  AppSecret: $APP_SECRET"
echo "  域名: $DOMAIN"
echo ""

# 备份原始文件
backup_file() {
    local file=$1
    if [ -f "$file" ]; then
        cp "$file" "${file}.backup.$(date +%Y%m%d%H%M%S)"
        echo -e "${GREEN}✓ 已备份:${NC} $file"
    fi
}

# 更新配置文件
update_config() {
    echo -e "${YELLOW}更新配置文件...${NC}"

    # 1. 更新 conf/service_conf.yaml
    backup_file "conf/service_conf.yaml"

    # 检查是否已有 oauth 配置
    if grep -q "^oauth:" "conf/service_conf.yaml"; then
        echo -e "${GREEN}✓ 已找到 oauth 配置，添加钉钉配置${NC}"

        # 检查是否已有 dingtalk 配置
        if grep -q "^\s*dingtalk:" "conf/service_conf.yaml"; then
            echo -e "${YELLOW}⚠ 已存在钉钉配置，将更新${NC}"
            # 这里可以添加更新逻辑，暂时只提示
        else
            # 在 oauth: 下方添加钉钉配置
            sed -i '' '/^oauth:/a\
  dingtalk:\
    type: "dingtalk"\
    display_name: "钉钉登录"\
    icon: "dingtalk"\
    client_id: "'"${APP_KEY}"'"\
    client_secret: "'"${APP_SECRET}"'"\
    redirect_uri: "https://'"${DOMAIN}"'/v1/user/oauth/callback/dingtalk"\
    scope: "openid profile"' "conf/service_conf.yaml"
            echo -e "${GREEN}✓ 已添加钉钉配置到 service_conf.yaml${NC}"
        fi
    else
        echo -e "${YELLOW}⚠ 未找到 oauth 配置，将添加完整配置${NC}"

        # 在合适的位置添加完整配置
        # 查找合适的插入位置（在 # oauth: 注释之前）
        if grep -q "# oauth:" "conf/service_conf.yaml"; then
            sed -i '' '/# oauth:/i\
oauth:\
  dingtalk:\
    type: "dingtalk"\
    display_name: "钉钉登录"\
    icon: "dingtalk"\
    client_id: "'"${APP_KEY}"'"\
    client_secret: "'"${APP_SECRET}"'"\
    redirect_uri: "https://'"${DOMAIN}"'/v1/user/oauth/callback/dingtalk"\
    scope: "openid profile"' "conf/service_conf.yaml"
        else
            # 如果没有注释，添加到文件末尾
            echo -e "\n# 钉钉 OAuth 配置\noauth:\n  dingtalk:\n    type: \"dingtalk\"\n    display_name: \"钉钉登录\"\n    icon: \"dingtalk\"\n    client_id: \"${APP_KEY}\"\n    client_secret: \"${APP_SECRET}\"\n    redirect_uri: \"https://${DOMAIN}/v1/user/oauth/callback/dingtalk\"\n    scope: \"openid profile\"" >> "conf/service_conf.yaml"
        fi
        echo -e "${GREEN}✓ 已添加完整 oauth 配置${NC}"
    fi

    # 2. 更新 docker/service_conf.yaml.template
    backup_file "docker/service_conf.yaml.template"

    # 使用环境变量模板
    sed -i '' 's/client_id: ".*"/client_id: "${DINGTALK_APP_KEY}"/' "docker/service_conf.yaml.template"
    sed -i '' 's/client_secret: ".*"/client_secret: "${DINGTALK_APP_SECRET}"/' "docker/service_conf.yaml.template"
    sed -i '' 's|redirect_uri: ".*"|redirect_uri: "${DINGTALK_REDIRECT_URI}"|' "docker/service_conf.yaml.template"
    echo -e "${GREEN}✓ 已更新 Docker 配置模板${NC}"

    # 3. 更新 docker/.env
    backup_file "docker/.env"

    # 添加或更新环境变量
    if grep -q "^DINGTALK_APP_KEY=" "docker/.env"; then
        sed -i '' "s/^DINGTALK_APP_KEY=.*/DINGTALK_APP_KEY=${APP_KEY}/" "docker/.env"
        sed -i '' "s/^DINGTALK_APP_SECRET=.*/DINGTALK_APP_SECRET=${APP_SECRET}/" "docker/.env"
    else
        echo -e "\n# 钉钉 OAuth 配置\nDINGTALK_APP_KEY=${APP_KEY}\nDINGTALK_APP_SECRET=${APP_SECRET}\nDINGTALK_REDIRECT_URI=https://${DOMAIN}/v1/user/oauth/callback/dingtalk" >> "docker/.env"
    fi
    echo -e "${GREEN}✓ 已更新环境变量${NC}"
}

# 验证配置
validate_config() {
    echo -e "${YELLOW}验证配置...${NC}"

    # 检查必要的文件
    required_files=(
        "api/apps/auth/dingtalk.py"
        "conf/service_conf.yaml"
        "docker/.env"
    )

    for file in "${required_files[@]}"; do
        if [ -f "$file" ]; then
            echo -e "${GREEN}✓ 文件存在:${NC} $file"
        else
            echo -e "${RED}✗ 文件缺失:${NC} $file"
            exit 1
        fi
    done

    # 检查配置语法
    if python3 -m py_compile "api/apps/auth/dingtalk.py" 2>/dev/null; then
        echo -e "${GREEN}✓ Python 语法检查通过${NC}"
    else
        echo -e "${RED}✗ Python 语法检查失败${NC}"
        exit 1
    fi

    echo -e "${GREEN}✓ 配置验证通过${NC}"
}

# 生成钉钉开放平台配置指南
generate_dingtalk_guide() {
    echo -e "${YELLOW}生成钉钉开放平台配置指南...${NC}"

    cat > "钉钉开放平台配置说明.txt" << EOF
钉钉开放平台配置指南
====================

请按照以下步骤在钉钉开放平台配置您的应用：

1. 访问钉钉开放平台
   地址: https://open.dingtalk.com/

2. 创建应用
   - 登录后进入"应用开发" > "企业内部应用"
   - 点击"创建应用"
   - 选择"小程序/网页应用"

3. 应用信息
   - 应用名称: RAGFlow (或自定义名称)
   - 应用描述: RAGFlow 单点登录

4. 开发信息配置
   - AppKey: $APP_KEY
   - AppSecret: $APP_SECRET

5. 安全设置
   - 进入"开发管理" > "开发信息"
   - 在"安全设置"中添加"授权回调地址":

     生产环境: https://${DOMAIN}/v1/user/oauth/callback/dingtalk

     测试环境: http://localhost:80/v1/user/oauth/callback/dingtalk
     (如果使用其他端口，请相应修改)

6. 权限申请
   - 进入"权限管理"
   - 添加以下权限：
     * 成员信息读权限
     * 手机号码信息读权限
     * 邮箱等个人信息读权限
   - 提交申请并等待审批

7. 应用发布
   - 完成配置后，点击"发布"
   - 等待钉钉管理员审批

8. 测试登录
   - 访问您的 RAGFlow 实例
   - 点击"钉钉登录"按钮
   - 使用钉钉扫码或输入账号密码登录

重要提示:
- 确保回调地址与配置文件中的 redirect_uri 完全一致
- 包括协议(http/https)、域名、端口和路径
- 生产环境必须使用 HTTPS
- 本地开发可以使用 HTTP

EOF

    echo -e "${GREEN}✓ 已生成配置指南: 钉钉开放平台配置说明.txt${NC}"
}

# 显示下一步操作
show_next_steps() {
    echo -e "\n${GREEN}=== 配置完成！ ===${NC}\n"
    echo -e "${YELLOW}下一步操作:${NC}"
    echo "1. 按照 '钉钉开放平台配置说明.txt' 的指南配置钉钉应用"
    echo "2. 更新钉钉开放平台的回调地址: https://${DOMAIN}/v1/user/oauth/callback/dingtalk"
    echo "3. 重启 RAGFlow 服务使配置生效:"
    echo "   docker compose down"
    echo "   docker compose up -d"
    echo "4. 测试钉钉登录功能"
    echo ""
    echo -e "${YELLOW}测试步骤:${NC}"
    echo "1. 访问 RAGFlow 登录页面"
    echo "2. 点击 '钉钉登录' 按钮"
    echo "3. 使用钉钉扫码或输入账号登录"
    echo "4. 验证登录是否成功"
    echo ""
    echo -e "${YELLOW}故障排除:${NC}"
    echo "- 检查回调地址配置是否正确"
    echo "- 查看日志: docker logs -f ragflow-server"
    echo "- 验证网络连接和防火墙设置"
}

# 主执行流程
main() {
    echo -e "${YELLOW}开始配置钉钉 OAuth...${NC}"

    update_config
    echo ""

    validate_config
    echo ""

    generate_dingtalk_guide
    echo ""

    show_next_steps
}

# 执行主函数
main