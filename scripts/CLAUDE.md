# Scripts Directory Rules

完整脚本说明参见 @scripts/README.md

## Development Standards
- kebab-case命名: `deploy-to-dev.sh`
- 包含 `--help` 选项和退出码
- 支持环境变量: `DEV_SERVER`, `TEST_MACHINE_IP`
- 可执行权限: `chmod +x`

## Integration Requirements
- 添加脚本 → 更新 `package.json` 和 `Makefile`
- 修改路径 → 搜索所有引用并更新
- 测试: 直接执行 + pnpm 命令都要工作

## Security Rules
- 禁止硬编码密码、API keys
- SSH key 认证，不用密码
- 验证输入防止注入攻击

## Debug Commands
```bash
bash -n script.sh           # 语法检查
bash -x script.sh            # 调试执行
rg "script-name" -t config   # 搜索引用
```