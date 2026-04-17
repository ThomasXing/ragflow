# RAGFlow SECRET_KEY安全修复 - 最简解决方案

## 问题确认
✅ 日志中显示：`WARNING:root:SECURITY WARNING: Using auto-generated SECRET_KEY.`
✅ 已修复代码：`common/settings.py` 现在支持从环境变量读取 `RAGFLOW_SECRET_KEY`

## 立即执行的解决方案

### 方案1：快速修复（推荐）
```bash
# 1. 生成安全密钥
SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))")
echo "生成的SECRET_KEY: $SECRET_KEY"

# 2. 停止并删除当前容器
docker stop docker-ragflow-cpu-1
docker rm docker-ragflow-cpu-1

# 3. 创建新的容器并设置SECRET_KEY环境变量
cd /Users/thomasxing/workspace/2026/4月份计划/ragflow/docker
RAGFLOW_SECRET_KEY="$SECRET_KEY" docker-compose up -d

# 4. 验证修复
docker logs docker-ragflow-cpu-1 --tail 20 | grep -i "SECURITY WARNING"
# 如果不再显示警告，说明修复成功
```

### 方案2：仅设置环境变量（容器已运行）
```bash
# 1. 生成安全密钥
SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))")
echo "RAGFLOW_SECRET_KEY=$SECRET_KEY"

# 2. 在容器中设置环境变量（临时）
docker exec -e RAGFLOW_SECRET_KEY="$SECRET_KEY" docker-ragflow-cpu-1 /bin/sh -c 'echo "SECRET_KEY已设置，重启服务生效"'

# 3. 重启RAGFlow进程（需要在容器内部）
# 或者直接重启容器
docker restart docker-ragflow-cpu-1

# 4. 验证
docker logs docker-ragflow-cpu-1 --tail 20 | grep -i "SECURITY WARNING"
```

### 方案3：永久解决方案（修改docker-compose配置）
```yaml
# 编辑 docker/docker-compose.yml，在ragflow-cpu服务下添加环境变量：
services:
  ragflow-cpu:
    # ... 其他配置 ...
    environment:
      - RAGFLOW_SECRET_KEY=your_secret_key_here  # 添加这一行
```

## 验证修复是否成功

运行验证命令：
```bash
# 检查日志中的警告是否消失
docker logs docker-ragflow-cpu-1 2>&1 | grep -c "SECURITY WARNING: Using auto-generated SECRET_KEY"

# 如果返回0，说明修复成功
# 如果返回1或更多，说明警告仍然存在
```

## 推荐的SECRET_KEY值
```
RAGFLOW_SECRET_KEY=2013f1f73c04cbc01479e2e55e1800e1661c6e5f117935f76f98ccf711f3b1a2
```

## 重要提示
1. **生产环境必须设置**：使用自动生成的SECRET_KEY存在安全风险
2. **密钥长度**：至少32个字符，推荐64字符十六进制
3. **备份密钥**：妥善保存设置的SECRET_KEY
4. **所有环境统一**：开发、测试、生产环境使用不同的密钥

## 已完成的工作
✅ 修复了 `common/settings.py` 中的 `_get_or_create_secret_key()` 函数
✅ 现在支持从环境变量 `RAGFLOW_SECRET_KEY` 读取密钥
✅ 创建了配置指南 (`SECRET_KEY_SETUP_GUIDE.md`)
✅ 提供了多种设置方案

## 下一步
1. 选择上述任一方案设置SECRET_KEY
2. 重启RAGFlow服务
3. 验证警告不再出现
4. 将密钥安全地保存到生产环境配置中
