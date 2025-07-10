"""
示例：如何修改后端认证端点以支持端对端测试

这是一个示例文件，展示最小化的修改方案
"""

# ========== 示例 1：修改 UserResponse Schema ==========
# 在 src/api/schemas/auth.py 中添加可选字段

from pydantic import BaseModel, Field
from typing import Optional

class UserResponse(BaseModel):
    """用户响应模型"""
    id: str
    username: str
    email: str
    is_verified: bool
    # ... 其他字段
    
    # 仅在测试环境返回的字段
    verification_token: Optional[str] = Field(None, exclude=True)
    
    class Config:
        orm_mode = True
        
        @staticmethod
        def schema_extra(schema: dict, model) -> None:
            # 在生产环境中隐藏测试字段
            if not settings.TESTING:
                props = schema.get('properties', {})
                props.pop('verification_token', None)


# ========== 示例 2：修改注册端点 ==========
# 在 src/api/routes/v1/auth_register.py 中

from src.core.config import settings

@router.post("/register", response_model=UserResponse)
async def register(
    user_data: UserCreate,
    db: AsyncSession = Depends(get_db),
):
    # ... 现有的注册逻辑
    
    # 创建用户
    user = await user_service.create_user(user_data)
    
    # 发送验证邮件
    verification = await email_service.send_verification_email(user)
    
    # 构建响应
    response = UserResponse.from_orm(user)
    
    # 在测试环境中包含验证令牌
    if settings.TESTING and settings.get("TEST_RETURN_TOKENS", False):
        response.verification_token = verification.token
    
    return response


# ========== 示例 3：添加测试中间件 ==========
# 在 src/middleware/test_helpers.py 中

from fastapi import Request
from fastapi.responses import JSONResponse

class TestMiddleware:
    """测试辅助中间件"""
    
    def __init__(self, app):
        self.app = app
    
    async def __call__(self, request: Request, call_next):
        # 只在测试环境启用
        if not settings.TESTING:
            return await call_next(request)
        
        # 添加测试标头
        response = await call_next(request)
        response.headers["X-Test-Environment"] = "true"
        
        # 如果是注册请求，可以在响应中注入额外数据
        if request.url.path == "/api/v1/auth/register" and request.method == "POST":
            # 这里可以修改响应以包含测试数据
            pass
        
        return response


# ========== 示例 4：使用装饰器模式 ==========
# 创建一个测试装饰器

def test_mode_response(func):
    """在测试模式下增强响应"""
    async def wrapper(*args, **kwargs):
        result = await func(*args, **kwargs)
        
        if settings.TESTING:
            # 增强响应数据
            if hasattr(result, "__dict__"):
                # 如果是注册响应，添加验证令牌
                if "email" in result.__dict__:
                    # 从数据库获取令牌
                    db = kwargs.get("db")
                    if db:
                        verification = await get_latest_verification_token(
                            db, result.email
                        )
                        if verification:
                            result.verification_token = verification.token
        
        return result
    
    return wrapper


# 使用装饰器
@router.post("/register")
@test_mode_response
async def register(user_data: UserCreate, db: AsyncSession = Depends(get_db)):
    # 原有逻辑保持不变
    pass


# ========== 示例 5：配置文件示例 ==========
# 在 src/core/config.py 中

from pydantic import BaseSettings, Field

class Settings(BaseSettings):
    # 基础配置
    PROJECT_NAME: str = "Infinite Scribe"
    API_VERSION: str = "v1"
    
    # 测试相关配置
    TESTING: bool = Field(False, env="TESTING")
    TEST_RETURN_TOKENS: bool = Field(False, env="TEST_RETURN_TOKENS")
    TEST_SKIP_EMAIL_VERIFICATION: bool = Field(False, env="TEST_SKIP_EMAIL_VERIFICATION")
    TEST_AUTO_VERIFY_EMAIL: bool = Field(False, env="TEST_AUTO_VERIFY_EMAIL")
    
    # 测试数据清理
    TEST_DATA_PREFIX: str = Field("e2e_test_", env="TEST_DATA_PREFIX")
    TEST_AUTO_CLEANUP: bool = Field(True, env="TEST_AUTO_CLEANUP")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


# ========== 使用建议 ==========
"""
1. 选择最适合项目架构的方案
2. 确保测试配置不会意外启用在生产环境
3. 使用环境变量控制测试特性
4. 定期清理测试数据
5. 在 CI/CD 中使用独立的测试数据库

环境变量配置示例（.env.test）:
TESTING=true
TEST_RETURN_TOKENS=true
TEST_AUTO_VERIFY_EMAIL=false
POSTGRES_DB=infinite_scribe_test
"""