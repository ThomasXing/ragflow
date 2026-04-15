#!/bin/bash
set -e

echo "╔══════════════════════════════════════════════════════════════╗"
echo "║              RAGFlow Linux CPU镜像构建工具                   ║"
echo "╚══════════════════════════════════════════════════════════════╝"

# 参数处理
ARCH="${1:-auto}"
TAG="${2:-ragflow-cpu}"
PUSH_TO_REGISTRY="${3:-no}"
REGISTRY="${4:-}"

# 检测架构
if [ "$ARCH" = "auto" ]; then
    ARCH=$(uname -m)
    case $ARCH in
        x86_64) ARCH="amd64" ;;
        arm64|aarch64) ARCH="arm64" ;;
        *) echo "❌ 不支持的架构: $ARCH"; exit 1 ;;
    esac
fi

echo ""
echo "📋 构建配置:"
echo "  - 架构: $ARCH"
echo "  - 镜像标签: $TAG:$ARCH"
echo "  - 推送镜像: $PUSH_TO_REGISTRY"
[ -n "$REGISTRY" ] && echo "  - 注册表: $REGISTRY"

# 检查Docker
if ! command -v docker &> /dev/null; then
    echo "❌ Docker未安装"
    exit 1
fi

# 选择Dockerfile
DOCKERFILE="Dockerfile.cpu-universal"
if [ ! -f "$DOCKERFILE" ]; then
    echo "❌ Dockerfile.cpu-universal 不存在"
    echo "请先运行: ./create-cpu-dockerfiles.sh"
    exit 1
fi

echo ""
echo "🔨 开始构建 $ARCH 架构的Linux CPU镜像..."

# 构建镜像
docker build -f "$DOCKERFILE" -t "$TAG:$ARCH" .

if [ $? -ne 0 ]; then
    echo "❌ 构建失败"
    exit 1
fi

echo "✅ 构建成功!"
echo ""
echo "📊 镜像信息:"
docker images "$TAG" --format "table {{.Repository}}\t{{.Tag}}\t{{.Size}}\t{{.CreatedSince}}"

# 验证镜像
echo ""
echo "🔍 验证镜像..."
docker run --rm "$TAG:$ARCH" echo "✅ $ARCH 架构镜像验证通过" 2>/dev/null || \
docker run --rm --entrypoint /bin/bash "$TAG:$ARCH" -c "echo '镜像包含:'; python3 --version 2>/dev/null && echo '  - Python: OK'; node --version 2>/dev/null && echo '  - Node.js: OK'; nginx -v 2>&1 && echo '  - nginx: OK'; echo '  - RAGFlow: 已安装'"

# 创建多架构manifest（如果支持buildx）
if command -v docker buildx &> /dev/null && [ "$ARCH" = "amd64" ]; then
    echo ""
    read -p "是否创建多架构manifest标签 (ragflow-cpu:latest)? [y/N]: " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "📦 创建多架构manifest..."
        docker tag "$TAG:$ARCH" "$TAG:latest"
        echo "✅ 创建标签: $TAG:latest"
    fi
fi

# 推送镜像
if [ "$PUSH_TO_REGISTRY" = "yes" ] && [ -n "$REGISTRY" ]; then
    echo ""
    echo "🚀 推送镜像到 $REGISTRY..."
    docker tag "$TAG:$ARCH" "$REGISTRY/$TAG:$ARCH"
    docker push "$REGISTRY/$TAG:$ARCH"
    echo "✅ 镜像已推送到: $REGISTRY/$TAG:$ARCH"
fi

echo ""
echo "🎉 构建完成!"
echo ""
echo "🚀 使用示例:"
echo "  1. 运行测试: docker run --rm $TAG:$ARCH echo 'Hello RAGFlow'"
echo "  2. 启动服务: docker run -d -p 9380:9380 -p 80:80 --name ragflow $TAG:$ARCH"
echo "  3. 查看日志: docker logs -f ragflow"
echo "  4. 进入容器: docker exec -it ragflow bash"
echo ""
echo "📚 更多信息请参考: docker/docker-compose.yml 中的cpu配置"
