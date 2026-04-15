#!/bin/bash
#
# RAGFlow 团队共享功能一键部署脚本
# 用法: ./deploy-team-share.sh [选项]
#
# 选项:
#   --build         构建前端和后端（默认）
#   --no-build      跳过构建，直接部署
#   --push          构建后推送镜像到仓库
#   --profile       指定 Docker profile (cpu/gpu)，默认 cpu
#   --env-file      指定环境变量文件，默认 .env
#   --skip-migration 跳过数据库迁移
#   -h, --help      显示帮助信息
#
# 示例:
#   ./deploy-team-share.sh                    # 标准部署
#   ./deploy-team-share.sh --push             # 构建并推送镜像
#   ./deploy-team-share.sh --profile gpu      # GPU 模式部署
#   ./deploy-team-share.sh --no-build         # 跳过构建直接部署
#

set -e

# ┌─────────────────────────────────────────────────────────────────┐
# │  配置变量                                                        │
# └─────────────────────────────────────────────────────────────────┘
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

# 默认配置
IMAGE_NAME="${IMAGE_NAME:-infiniflow/ragflow}"
IMAGE_TAG="${IMAGE_TAG:-team-share}"
BUILD_FRONTEND="${BUILD_FRONTEND:-true}"
PUSH_IMAGE="${PUSH_IMAGE:-false}"
DOCKER_PROFILE="${DOCKER_PROFILE:-cpu}"
ENV_FILE="${ENV_FILE:-${SCRIPT_DIR}/.env}"
SKIP_MIGRATION="${SKIP_MIGRATION:-false}"
PLATFORM="${PLATFORM:-linux/amd64}"

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# ┌─────────────────────────────────────────────────────────────────┐
# │  辅助函数                                                        │
# └─────────────────────────────────────────────────────────────────┘

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

show_banner() {
    echo ""
    echo "┌─────────────────────────────────────────────────────────────────┐"
    echo "│  RAGFlow 团队共享功能一键部署脚本                                │"
    echo "│  Version: 1.0.0                                                 │"
    echo "│  Date: $(date '+%Y-%m-%d %H:%M:%S')                                      │"
    echo "└─────────────────────────────────────────────────────────────────┘"
    echo ""
}

show_help() {
    cat << EOF
用法: $0 [选项]

选项:
  --build           构建前端和后端（默认）
  --no-build        跳过构建，直接部署
  --push            构建后推送镜像到仓库
  --profile PROFILE 指定 Docker profile (cpu/gpu)，默认 cpu
  --env-file FILE   指定环境变量文件，默认 .env
  --skip-migration  跳过数据库迁移
  --platform ARCH   指定构建平台 (linux/amd64/linux/arm64)，默认 linux/amd64
  -h, --help        显示帮助信息

环境变量:
  IMAGE_NAME        Docker 镜像名称，默认 infiniflow/ragflow
  IMAGE_TAG         Docker 镜像标签，默认 team-share
  PLATFORM          构建平台，默认 linux/amd64

示例:
  $0                                # 标准部署
  $0 --push                         # 构建并推送镜像
  $0 --profile gpu                  # GPU 模式部署
  $0 --no-build                     # 跳过构建直接部署
  $0 --platform linux/arm64         # ARM64 平台构建

EOF
}

check_prerequisites() {
    log_info "检查前置条件..."

    # 检查 Docker
    if ! command -v docker &> /dev/null; then
        log_error "Docker 未安装，请先安装 Docker"
        exit 1
    fi

    # 检查 Docker Compose
    if ! docker compose version &> /dev/null; then
        log_error "Docker Compose 未安装，请先安装 Docker Compose"
        exit 1
    fi

    # 检查 Node.js（前端构建需要）
    if [ "$BUILD_FRONTEND" = "true" ]; then
        if ! command -v node &> /dev/null; then
            log_error "Node.js 未安装，前端构建需要 Node.js >= 18.20.4"
            exit 1
        fi
    fi

    # 检查环境变量文件
    if [ ! -f "$ENV_FILE" ]; then
        log_error "环境变量文件不存在: $ENV_FILE"
        log_info "请复制 .env 模板并修改配置: cp .env.example .env"
        exit 1
    fi

    log_success "前置条件检查通过"
}

# ┌─────────────────────────────────────────────────────────────────┐
# │  构建阶段                                                        │
# └─────────────────────────────────────────────────────────────────┘

build_frontend() {
    log_info "开始构建前端..."

    cd "${PROJECT_ROOT}/web"

    # 安装依赖
    log_info "安装前端依赖..."
    npm install

    # 构建生产版本
    log_info "构建前端生产版本..."
    npm run build

    # 验证构建产物
    if [ ! -d "dist" ]; then
        log_error "前端构建失败，dist 目录不存在"
        exit 1
    fi

    log_success "前端构建完成: $(ls -lh dist/ | head -5)"
    cd "${PROJECT_ROOT}"
}

build_docker_image() {
    log_info "开始构建 Docker 镜像..."

    local full_image="${IMAGE_NAME}:${IMAGE_TAG}"

    log_info "镜像名称: ${full_image}"
    log_info "构建平台: ${PLATFORM}"

    cd "${PROJECT_ROOT}"

    # 构建 Docker 镜像
    docker build \
        --platform "${PLATFORM}" \
        -f Dockerfile \
        -t "${full_image}" \
        --build-arg BUILD_DATE="$(date -u +'%Y-%m-%dT%H:%M:%SZ')" \
        --build-arg VERSION="${IMAGE_TAG}" \
        .

    # 验证镜像
    if ! docker image inspect "${full_image}" &> /dev/null; then
        log_error "Docker 镜像构建失败"
        exit 1
    fi

    log_success "Docker 镜像构建完成: ${full_image}"

    # 显示镜像大小
    local image_size=$(docker image inspect "${full_image}" --format='{{.Size}}' | awk '{printf "%.2f GB", $1/1024/1024/1024}')
    log_info "镜像大小: ${image_size}"
}

push_docker_image() {
    if [ "$PUSH_IMAGE" != "true" ]; then
        return
    fi

    log_info "推送 Docker 镜像到仓库..."

    local full_image="${IMAGE_NAME}:${IMAGE_TAG}"

    # 检查是否已登录
    if ! docker info 2>/dev/null | grep -q "Username"; then
        log_warning "未登录 Docker Hub，正在尝试登录..."
        docker login
    fi

    docker push "${full_image}"

    log_success "镜像推送完成: ${full_image}"
}

# ┌─────────────────────────────────────────────────────────────────┐
# │  部署阶段                                                        │
# └─────────────────────────────────────────────────────────────────┘

run_database_migration() {
    if [ "$SKIP_MIGRATION" = "true" ]; then
        log_info "跳过数据库迁移"
        return
    fi

    log_info "执行数据库迁移..."

    cd "${SCRIPT_DIR}"

    # 检查 MySQL 是否运行
    if ! docker compose -f docker-compose-base.yml ps mysql 2>/dev/null | grep -q "running"; then
        log_info "启动 MySQL 服务..."
        docker compose -f docker-compose-base.yml up -d mysql
        log_info "等待 MySQL 启动..."
        sleep 30
    fi

    # 执行迁移脚本
    local migration_files=(
        "oceanbase/init.d/create_file_permission_share_table.sql"
        "oceanbase/init.d/create_team_permission_share_table.sql"
    )

    for migration_file in "${migration_files[@]}"; do
        if [ -f "${migration_file}" ]; then
            log_info "执行迁移: ${migration_file}"

            # 读取 MySQL 密码
            local mysql_password=$(grep -E "^MYSQL_PASSWORD=" "${ENV_FILE}" | cut -d'=' -f2)

            # 执行 SQL
            docker compose -f docker-compose-base.yml exec -T mysql \
                mysql -uroot -p"${mysql_password}" rag_flow < "${migration_file}" 2>/dev/null || true

            log_success "迁移完成: ${migration_file}"
        else
            log_warning "迁移文件不存在: ${migration_file}"
        fi
    done

    log_success "数据库迁移完成"
}

deploy_services() {
    log_info "部署服务..."

    cd "${SCRIPT_DIR}"

    # 停止现有服务
    log_info "停止现有服务..."
    docker compose --profile "${DOCKER_PROFILE}" down 2>/dev/null || true

    # 拉取基础镜像（可选）
    # docker compose -f docker-compose-base.yml pull

    # 启动基础服务
    log_info "启动基础服务..."
    docker compose -f docker-compose-base.yml up -d

    # 等待服务健康
    log_info "等待基础服务就绪..."
    sleep 20

    # 检查 MySQL 健康状态
    log_info "检查 MySQL 健康状态..."
    for i in {1..30}; do
        if docker compose -f docker-compose-base.yml ps mysql 2>/dev/null | grep -q "healthy"; then
            log_success "MySQL 已就绪"
            break
        fi
        if [ $i -eq 30 ]; then
            log_error "MySQL 启动超时"
            exit 1
        fi
        sleep 2
    done

    # 启动 RAGFlow 服务
    log_info "启动 RAGFlow 服务 (${DOCKER_PROFILE} 模式)..."
    docker compose --profile "${DOCKER_PROFILE}" up -d

    log_success "服务部署完成"
}

verify_deployment() {
    log_info "验证部署..."

    cd "${SCRIPT_DIR}"

    # 等待服务启动
    log_info "等待服务启动..."
    sleep 30

    # 检查容器状态
    log_info "容器状态:"
    docker compose --profile "${DOCKER_PROFILE}" ps

    # 健康检查
    log_info "执行健康检查..."

    local health_url="http://localhost:9380/api/health"
    local max_retries=10
    local retry=0

    while [ $retry -lt $max_retries ]; do
        if curl -sf "${health_url}" > /dev/null 2>&1; then
            log_success "服务健康检查通过"
            break
        fi

        retry=$((retry + 1))
        log_warning "健康检查失败，重试 (${retry}/${max_retries})..."
        sleep 5
    done

    if [ $retry -eq $max_retries ]; then
        log_error "健康检查失败，请检查日志: docker compose logs ragflow-${DOCKER_PROFILE}"
        exit 1
    fi

    # 显示访问信息
    echo ""
    echo "┌─────────────────────────────────────────────────────────────────┐"
    echo "│  部署成功！                                                      │"
    echo "├─────────────────────────────────────────────────────────────────┤"
    echo "│  Web UI:     http://localhost:80                                 │"
    echo "│  API:        http://localhost:9380                               │"
    echo "│  Admin API:  http://localhost:9381                               │"
    echo "├─────────────────────────────────────────────────────────────────┤"
    echo "│  查看日志:   docker compose logs -f ragflow-${DOCKER_PROFILE}   │"
    echo "│  停止服务:   docker compose --profile ${DOCKER_PROFILE} down    │"
    echo "└─────────────────────────────────────────────────────────────────┘"
    echo ""
}

# ┌─────────────────────────────────────────────────────────────────┐
# │  主函数                                                          │
# └─────────────────────────────────────────────────────────────────┘

main() {
    # 解析命令行参数
    while [[ $# -gt 0 ]]; do
        case $1 in
            --build)
                BUILD_FRONTEND="true"
                shift
                ;;
            --no-build)
                BUILD_FRONTEND="false"
                shift
                ;;
            --push)
                PUSH_IMAGE="true"
                shift
                ;;
            --profile)
                DOCKER_PROFILE="$2"
                shift 2
                ;;
            --env-file)
                ENV_FILE="$2"
                shift 2
                ;;
            --skip-migration)
                SKIP_MIGRATION="true"
                shift
                ;;
            --platform)
                PLATFORM="$2"
                shift 2
                ;;
            -h|--help)
                show_help
                exit 0
                ;;
            *)
                log_error "未知参数: $1"
                show_help
                exit 1
                ;;
        esac
    done

    show_banner

    # 检查前置条件
    check_prerequisites

    # 构建阶段
    if [ "$BUILD_FRONTEND" = "true" ]; then
        build_frontend
        build_docker_image
        push_docker_image
    fi

    # 部署阶段
    run_database_migration
    deploy_services

    # 验证阶段
    verify_deployment

    log_success "部署完成！团队共享功能已就绪。"
}

# 执行主函数
main "$@"
