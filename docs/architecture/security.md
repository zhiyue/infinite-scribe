# Security

## 输入验证
*   **库:** Pydantic (后端), Zod/Yup (前端)。
*   **位置:** 前后端双重验证。后端验证是最后防线。
*   **规则:** 严格验证所有外部输入，白名单优先。

## 认证与授权 (Authentication & Authorization)
*   **方法 (API网关):** JWT。考虑 `Auth0`, `Keycloak` 或自定义实现。
*   **存储 (前端):** JWT存入安全的 `HttpOnly` Cookie。
*   **授权:** RBAC。API端点声明所需权限。
*   **密码:** 强哈希算法 (`bcrypt` 或 `Argon2`) 加盐存储。

## 密钥管理 (Secrets Management)
*   **开发:** `.env` 文件 (加入 `.gitignore`)。
*   **生产:** **必须**使用专用密钥管理服务 (HashiCorp Vault, AWS Secrets Manager等)。
*   **代码要求:** 严禁硬编码密钥，严禁日志中出现密钥。

## API安全
*   **速率限制:** API网关实现 (如 `slowapi` for FastAPI)。
*   **CORS策略:** API网关配置严格CORS。
*   **安全头:** API响应包含推荐安全头。
*   **HTTPS强制:** 生产环境流量必须HTTPS。

## 数据保护
*   **传输中加密:** 所有外部通信必须TLS/SSL (HTTPS)。
*   **静态加密 (后MVP):** 考虑对PG, Minio, Neo4j中的敏感数据进行静态加密。
*   **PII处理:** (如果适用) 遵循相关隐私法规。
*   **日志限制:** 敏感数据不入日志。

## 依赖安全
*   **扫描工具:** CI/CD集成漏洞扫描 (`npm audit`/`pnpm audit`, `pip-audit`/`Safety`)。
*   **更新策略:** 定期审查和更新依赖。
*   **审批流程:** 新依赖需安全评估。

## Security测试 (后MVP)
*   **SAST:** `Bandit` (Python), `ESLint`安全插件。
*   **DAST:** OWASP ZAP。
*   **渗透测试:** 定期第三方渗透测试。


