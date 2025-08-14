# 邮件异步任务系统

## 任务背景
当前用户注册和密码重置流程中，邮件发送是同步进行的。这会导致：
- 用户等待时间过长
- 邮件服务故障会阻塞主流程
- 无法实现邮件发送的重试机制
- 影响系统的可扩展性

## 目标
1. 将邮件发送改为异步任务，不阻塞主流程
2. 提供邮件发送失败后的重试机制
3. 支持未来更多类型的异步任务（如数据导出、报告生成等）
4. 提升用户体验，即时响应用户请求

## 相关文件
- `/apps/backend/src/common/services/user_service.py` - 用户服务（注册、密码重置）
- `/apps/backend/src/common/services/email_service.py` - 邮件发送服务
- `/apps/backend/src/common/services/task_service.py` - 现有任务服务（可参考）
- `/apps/backend/src/api/routes/v1/auth_register.py` - 注册 API 路由

## 参考资料
- FastAPI BackgroundTasks 文档：https://fastapi.tiangolo.com/tutorial/background-tasks/
- Prefect 文档：https://docs.prefect.io/
- 项目已安装 Prefect：`prefect~=2.19.0`