#!/bin/bash

# 测试 OpenAPI 示例生成脚本

set -e

# 颜色定义
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}=== OpenAPI 示例测试 ===${NC}"

# 检查常用端点的示例
endpoints=(
    "ForgotPasswordRequest"
    "UserLoginRequest"
    "UserRegisterRequest"
)

for schema in "${endpoints[@]}"; do
    echo -e "\n${YELLOW}检查 $schema 的示例：${NC}"
    
    # 获取 schema 定义
    result=$(curl -s http://localhost:8000/openapi.json | jq ".components.schemas.$schema")
    
    # 检查是否有 examples
    if echo "$result" | jq -e '.examples' > /dev/null 2>&1; then
        echo -e "${GREEN}✓ 找到示例：${NC}"
        echo "$result" | jq '.examples[0]' | head -10
    else
        echo -e "✗ 没有找到示例"
    fi
    
    # 检查字段级别的 examples
    echo -e "\n字段级别的示例："
    echo "$result" | jq '.properties | to_entries[] | select(.value.examples != null) | {field: .key, examples: .value.examples}'
done

echo -e "\n${BLUE}=== Hoppscotch 导入建议 ===${NC}"
echo "1. 清除浏览器缓存或使用隐私模式"
echo "2. 重新导入最新的 openapi.json"
echo "3. 创建新请求时应该能看到预填充的数据"
echo "4. 如果仍然没有，手动点击 'Generate Example' 按钮"

echo -e "\n${YELLOW}测试请求示例：${NC}"
echo "curl -X POST http://localhost:8000/api/v1/auth/forgot-password \\"
echo "  -H 'Content-Type: application/json' \\"
echo "  -d '{\"email\": \"user@example.com\"}'"