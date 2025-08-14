#!/bin/bash

# Hoppscotch 集成脚本
# 用于导出 API 规范并生成 Hoppscotch 集合

set -e

# 颜色定义
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# 配置
BACKEND_URL="${BACKEND_URL:-http://localhost:8000}"
OUTPUT_DIR="./api-docs"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

echo -e "${GREEN}=== Hoppscotch 集成工具 ===${NC}"

# 检查后端服务是否运行
check_backend() {
    echo -e "${YELLOW}检查后端服务...${NC}"
    if curl -s "${BACKEND_URL}/health" > /dev/null; then
        echo -e "${GREEN}✓ 后端服务运行正常${NC}"
        return 0
    else
        echo -e "${RED}✗ 后端服务未运行${NC}"
        echo -e "${YELLOW}请先启动后端服务：${NC}"
        echo "cd apps/backend && uv run uvicorn src.api.main:app --reload"
        return 1
    fi
}

# 导出 OpenAPI 规范
export_openapi() {
    echo -e "${YELLOW}导出 OpenAPI 规范...${NC}"
    mkdir -p "$OUTPUT_DIR"
    
    # 下载 OpenAPI JSON
    curl -s "${BACKEND_URL}/openapi.json" > "$OUTPUT_DIR/openapi_${TIMESTAMP}.json"
    
    # 创建一个最新版本的链接
    ln -sf "openapi_${TIMESTAMP}.json" "$OUTPUT_DIR/openapi_latest.json"
    
    echo -e "${GREEN}✓ OpenAPI 规范已导出到: $OUTPUT_DIR/openapi_${TIMESTAMP}.json${NC}"
}

# 生成 Hoppscotch 集合
generate_hoppscotch_collection() {
    echo -e "${YELLOW}生成 Hoppscotch 集合配置...${NC}"
    
    # 创建环境配置文件
    cat > "$OUTPUT_DIR/hoppscotch_env.json" << EOF
{
  "name": "Infinite Scribe Dev",
  "variables": [
    {
      "key": "base_url",
      "value": "${BACKEND_URL}"
    },
    {
      "key": "api_version",
      "value": "v1"
    }
  ]
}
EOF

    # 创建导入说明
    cat > "$OUTPUT_DIR/IMPORT_GUIDE.md" << 'EOF'
# Hoppscotch 导入指南

## 方法 1：直接导入 OpenAPI（推荐）

1. 打开 Hoppscotch (https://hoppscotch.io)
2. 点击左侧 "Collections" 标签
3. 点击 "Import" 按钮
4. 选择 "OpenAPI" 格式
5. 上传 `openapi_latest.json` 文件
6. 所有 API 端点将自动导入

## 方法 2：使用环境变量

1. 在 Hoppscotch 中点击 "Environments" 
2. 导入 `hoppscotch_env.json`
3. 在请求中使用 `{{base_url}}` 变量

## 方法 3：实时同步（开发模式）

在开发时，你可以直接在 Hoppscotch 中输入 OpenAPI URL：
- URL: `http://localhost:8000/openapi.json`

这样可以实时获取最新的 API 定义。

## 常用端点

### 健康检查
- GET `{{base_url}}/health`

### 认证相关
- POST `{{base_url}}/api/v1/auth/register`
- POST `{{base_url}}/api/v1/auth/login`
- GET `{{base_url}}/api/v1/auth/profile`
- POST `{{base_url}}/api/v1/auth/password/reset`

## 认证配置

对于需要认证的端点，在 Headers 中添加：
```
Authorization: Bearer {{access_token}}
```

登录后将 token 保存到环境变量中使用。
EOF

    echo -e "${GREEN}✓ Hoppscotch 配置文件已生成${NC}"
}

# 显示使用说明
show_instructions() {
    echo -e "\n${GREEN}=== 集成完成 ===${NC}"
    echo -e "生成的文件："
    echo -e "  • $OUTPUT_DIR/openapi_latest.json - OpenAPI 规范"
    echo -e "  • $OUTPUT_DIR/hoppscotch_env.json - 环境配置"
    echo -e "  • $OUTPUT_DIR/IMPORT_GUIDE.md - 导入指南"
    echo -e "\n${YELLOW}下一步：${NC}"
    echo -e "1. 打开 https://hoppscotch.io"
    echo -e "2. 导入 OpenAPI 文件开始测试 API"
    echo -e "\n${YELLOW}提示：${NC}"
    echo -e "• 使用 Hoppscotch 浏览器扩展可以避免 CORS 问题"
    echo -e "• 或使用自托管版本：docker run -p 3000:3000 hoppscotch/hoppscotch"
    echo -e "• 也可以访问 ${BACKEND_URL}/openapi.yaml 获取 YAML 格式"
}

# 主流程
main() {
    # 解析命令行参数
    while [[ $# -gt 0 ]]; do
        case $1 in
            --url)
                BACKEND_URL="$2"
                shift 2
                ;;
            --output)
                OUTPUT_DIR="$2"
                shift 2
                ;;
            --help)
                echo "使用方法: $0 [选项]"
                echo "选项:"
                echo "  --url <URL>      后端服务 URL (默认: http://localhost:8000)"
                echo "  --output <DIR>   输出目录 (默认: ./api-docs)"
                echo "  --help          显示帮助信息"
                exit 0
                ;;
            *)
                echo "未知选项: $1"
                exit 1
                ;;
        esac
    done

    # 执行集成步骤
    if check_backend; then
        export_openapi
        generate_hoppscotch_collection
        show_instructions
    else
        exit 1
    fi
}

# 运行主函数
main "$@"