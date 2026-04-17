# RAGFlow SECRET_KEY 安全修复指南

## 问题描述
RAGFlow当前使用自动生成的SECRET_KEY，这在生产环境中存在安全风险。日志中显示警告：
```
WARNING:root:SECURITY WARNING: Using auto-generated SECRET_KEY.
```

## 修复完成
✅ 已修复 `common/settings.py` 中的 `_get_or_create_secret_key()` 函数
现在会优先从以下位置读取SECRET_KEY：
1. 环境变量 `RAGFLOW_SECRET_KEY`
2. 配置文件 `service_conf.yaml` 中的 `ragflow.secret_key` 字段
3. 如果以上都没有设置，才会使用自动生成的密钥并显示警告

## 设置安全的SECRET_KEY

### 方法1：通过环境变量设置（推荐）

**生成安全的SECRET_KEY（至少32个字符）：**
```bash
# 生成64字符的十六进制密钥（32字节）
python3 -c "import secrets; print(secrets.token_hex(32))"
```

**设置环境变量：**
```bash
export RAGFLOW_SECRET_KEY=你的安全密钥
```

**对于Docker容器：**
1. 停止当前容器：
```bash
docker stop docker-ragflow-cpu-1
```

2. 编辑 `docker/.env` 文件，添加：
```
RAGFLOW_SECRET_KEY=你的安全密钥
```

3. 重新启动容器：
```bash
docker start docker-ragflow-cpu-1
```

### 方法2：通过配置文件设置

编辑 `conf/service_conf.yaml` 文件，在 `ragflow` 配置部分添加：
```yaml
ragflow:
  secret_key: "你的安全密钥"
  host: 0.0.0.0
  http_port: 9380
```

## 验证修复

重启RAGFlow服务后，检查日志：
```bash
docker logs docker-ragflow-cpu-1 | grep -i "SECURITY WARNING"
```

如果修复成功，**不会**再显示以下警告：
```
WARNING:root:SECURITY WARNING: Using auto-generated SECRET_KEY.
```

## 最佳实践

1. **生产环境**：必须设置固定的SECRET_KEY
2. **密钥长度**：至少32个字符（推荐64个字符的十六进制字符串）
3. **密钥生成**：使用加密安全的随机生成器
4. **密钥管理**：
   - 不要将密钥提交到版本控制系统
   - 使用环境变量管理密钥
   - 定期更换密钥（建议每6个月）

## 示例密钥
```
# 64字符十六进制示例
RAGFLOW_SECRET_KEY=23b30d3dcf86e4ce115783cd75a0e2e311b75026c48eacb671ca4bdc519dcf47

# 或使用其他加密安全的随机字符串
RAGFLOW_SECRET_KEY=$(openssl rand -base64 48 | tr -d '\n')
```

## 故障排除

1. **警告仍然存在**：检查环境变量是否已正确设置并生效
2. **服务启动失败**：检查密钥长度是否符合要求（≥32字符）
3. **配置不生效**：确保修改的是正确的配置文件，并已重启服务

## 注意事项
- SECRET_KEY用于会话加密和令牌签名
- 在生产环境中使用自动生成的密钥可能导致安全漏洞
- 请确保所有环境（开发、测试、生产）使用不同的SECRET_KEY
