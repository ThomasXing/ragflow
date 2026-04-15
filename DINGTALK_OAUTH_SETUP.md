# RAGFlow 钉钉 OAuth 登录集成指南

## 已完成配置

我已经为 RAGFlow 集成了钉钉 OAuth 登录功能。以下是已完成的配置：

### 1. 新增钉钉 OAuth 客户端类
**文件**: `api/apps/auth/dingtalk.py`
- 实现了 `DingTalkOAuthClient` 类，继承自 `OAuthClient`
- 配置了钉钉 OAuth 2.0 的 API 端点
- 实现了用户信息获取和标准化处理

### 2. 注册钉钉客户端到认证系统
**文件**: `api/apps/auth/__init__.py`
- 在 `CLIENT_TYPES` 中添加了 `"dingtalk": DingTalkOAuthClient`
- 确保系统能识别并使用钉钉认证客户端

### 3. 更新配置文件
**文件**: `conf/service_conf.yaml`
```yaml
oauth:
  dingtalk:
    type: "dingtalk"
    display_name: "钉钉登录"
    icon: "dingtalk"
    client_id: "${DINGTALK_APP_KEY}"
    client_secret: "${DINGTALK_APP_SECRET}"
    redirect_uri: "http://localhost:80/v1/user/oauth/callback/dingtalk"
    scope: "openid profile"
```

### 4. 更新 Docker 配置模板
**文件**: `docker/service_conf.yaml.template`
- 添加了相同的钉钉 OAuth 配置

### 5. 添加环境变量
**文件**: `docker/.env`
```bash
# 钉钉 OAuth 配置
DINGTALK_APP_KEY=your_dingtalk_app_key_here
DINGTALK_APP_SECRET=your_dingtalk_app_secret_here
```

## 钉钉开放平台配置步骤

### 第一步：创建钉钉应用
1. 访问 [钉钉开放平台](https://open.dingtalk.com/)
2. 登录并进入"应用开发" > "企业内部应用" 或 "扫码登录应用"
3. 创建新应用，选择"小程序/网页应用"
4. 记录应用的 `AppKey` 和 `AppSecret`

### 第二步：配置 OAuth 信息
1. 在应用详情页，找到"开发管理" > "开发信息"
2. 在"安全设置"中配置"授权回调地址"：
   - 本地开发：`http://localhost:80/v1/user/oauth/callback/dingtalk`
   - 生产环境：`https://your-domain.com/v1/user/oauth/callback/dingtalk`

### 第三步：设置应用权限
1. 在"权限管理"中，为应用添加以下权限：
   - 成员信息读权限
   - 手机号码信息读权限
   - 邮箱等个人信息读权限
2. 提交申请并等待审批

## 环境配置

### 本地开发环境
1. 更新 `.env` 文件中的钉钉配置：
```bash
# 钉钉 OAuth 配置
DINGTALK_APP_KEY=your_actual_app_key
DINGTALK_APP_SECRET=your_actual_app_secret
```

2. 确保回调地址配置正确：
```yaml
redirect_uri: "http://localhost:80/v1/user/oauth/callback/dingtalk"
```

### 生产环境配置
1. 修改 `service_conf.yaml` 中的回调地址：
```yaml
redirect_uri: "https://your-domain.com/v1/user/oauth/callback/dingtalk"
```

2. 更新环境变量：
```bash
DINGTALK_APP_KEY=production_app_key
DINGTALK_APP_SECRET=production_app_secret
```

## 测试钉钉登录

### 启动服务
```bash
# 启动依赖服务
docker compose -f docker/docker-compose-base.yml up -d

# 启动后端服务
source .venv/bin/activate
export PYTHONPATH=$(pwd)
bash docker/launch_backend_service.sh

# 启动前端服务
cd web
npm install
npm run dev
```

### 测试步骤
1. 访问 RAGFlow 登录页面：`http://localhost:3000/login`
2. 应该能看到"钉钉登录"按钮
3. 点击按钮，跳转到钉钉授权页面
4. 扫码或输入钉钉账号授权
5. 授权成功后回调到 RAGFlow，完成登录

## 故障排除

### 常见问题
1. **回调地址不匹配**
   - 确保钉钉开放平台配置的回调地址与 `redirect_uri` 完全一致
   - 包括协议（http/https）、域名、端口和路径

2. **Scope 权限不足**
   - 检查钉钉应用是否申请了正确的权限
   - 确保 `scope` 设置正确：`openid profile`

3. **用户信息获取失败**
   - 检查钉钉应用的权限是否已审批通过
   - 确认 `AppKey` 和 `AppSecret` 正确

4. **网络连接问题**
   - 确保服务器能访问钉钉 API 端点
   - 检查防火墙设置

### 调试日志
查看 RAGFlow 日志了解详细错误信息：
```bash
# 查看后端日志
tail -f logs/ragflow_server.log

# 查看 Docker 容器日志
docker logs -f ragflow-server
```

## 钉钉 API 参考

### OAuth 2.0 端点
- **授权地址**: `https://login.dingtalk.com/oauth2/auth`
- **Token 地址**: `https://api.dingtalk.com/v1.0/oauth2/userAccessToken`
- **用户信息地址**: `https://api.dingtalk.com/v1.0/contact/users/me`

### 用户信息响应格式
```json
{
  "nick": "张三",
  "unionid": "xxxx",
  "openid": "xxxx",
  "main_org_auth_high_level": true,
  "avatar_url": "https://xxx",
  "email": "zhangsan@example.com"
}
```

### Scope 说明
- `openid`: 获取用户的 OpenID
- `profile`: 获取用户的基本信息（昵称、头像等）
- 可选：`corp`（企业信息）、`contact`（通讯录权限）等

## 安全注意事项

1. **保护 AppSecret**
   - 不要在代码中硬编码 AppSecret
   - 使用环境变量管理
   - 定期轮换密钥

2. **回调地址验证**
   - 确保回调地址配置正确
   - 使用 HTTPS 生产环境
   - 防止回调地址伪造攻击

3. **State 参数**
   - RAGFlow 自动生成和验证 state 参数
   - 防止 CSRF 攻击

4. **用户隐私**
   - 仅请求必要的权限
   - 妥善存储用户信息
   - 遵守数据保护法规

## 扩展功能

### 1. 钉钉企业内应用
如果需要支持企业内部应用，可以修改配置：
```yaml
oauth:
  dingtalk_corp:
    type: "dingtalk"
    display_name: "钉钉企业登录"
    client_id: "${DINGTALK_CORP_APP_KEY}"
    client_secret: "${DINGTALK_CORP_APP_SECRET}"
    authorization_url: "https://login.dingtalk.com/oauth2/auth"
    token_url: "https://oapi.dingtalk.com/sns/gettoken"
    userinfo_url: "https://oapi.dingtalk.com/sns/getuserinfo_bycode"
    redirect_uri: "https://your-domain.com/v1/user/oauth/callback/dingtalk_corp"
    scope: "snsapi_login"
```

### 2. 多租户支持
可以通过不同的钉钉应用配置支持多个组织：
```yaml
oauth:
  dingtalk_org1:
    type: "dingtalk"
    display_name: "组织1钉钉登录"
    client_id: "${DINGTALK_ORG1_KEY}"
    client_secret: "${DINGTALK_ORG1_SECRET}"
    redirect_uri: "https://your-domain.com/v1/user/oauth/callback/dingtalk_org1"

  dingtalk_org2:
    type: "dingtalk"
    display_name: "组织2钉钉登录"
    client_id: "${DINGTALK_ORG2_KEY}"
    client_secret: "${DINGTALK_ORG2_SECRET}"
    redirect_uri: "https://your-domain.com/v1/user/oauth/callback/dingtalk_org2"
```

## 总结

RAGFlow 现已支持钉钉 OAuth 登录功能。用户可以通过钉钉账号快速登录系统，享受便捷的单点登录体验。配置完成后，钉钉登录选项将自动显示在登录页面。

如需进一步自定义钉钉用户信息处理，可以修改 `api/apps/auth/dingtalk.py` 中的 `normalize_user_info` 方法。