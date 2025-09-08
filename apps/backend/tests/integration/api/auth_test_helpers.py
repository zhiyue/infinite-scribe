"""认证测试的公共辅助函数。"""

from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from src.common.services.user.user_service import UserService
from src.models.email_verification import EmailVerification, VerificationPurpose
from src.models.user import User


async def create_and_verify_test_user(
    client: AsyncClient,
    db_session: AsyncSession,
    username: str = "testuser",
    email: str = "test@example.com",
    password: str = "ValidPass123!",
    first_name: str = "Test",
    last_name: str = "User",
) -> dict:
    """创建并验证测试用户的辅助函数。

    Args:
        client: HTTP客户端
        db_session: 数据库会话
        username: 用户名
        email: 邮箱
        password: 密码
        first_name: 名
        last_name: 姓

    Returns:
        包含用户数据的字典
    """
    # 创建测试用户
    user_service = UserService()
    user_data = {
        "username": username,
        "email": email,
        "password": password,
        "first_name": first_name,
        "last_name": last_name,
    }
    result = await user_service.register_user(db_session, user_data)
    assert result["success"]

    # 验证邮箱（跳过邮件验证步骤）
    stmt = select(User).where(User.email == email)
    user = (await db_session.execute(stmt)).scalar_one()
    user.is_verified = True
    await db_session.commit()

    return user_data


async def create_and_verify_test_user_with_registration(
    client: AsyncClient,
    db_session: AsyncSession,
    username: str = "testuser",
    email: str = "test@example.com",
    password: str = "ValidPass123!",
    first_name: str = "Test",
    last_name: str = "User",
) -> dict:
    """通过API注册并验证测试用户的辅助函数。

    Args:
        client: HTTP客户端
        db_session: 数据库会话
        username: 用户名
        email: 邮箱
        password: 密码
        first_name: 名
        last_name: 姓

    Returns:
        包含用户数据的字典
    """
    # 注册新用户
    register_data = {
        "username": username,
        "email": email,
        "password": password,
        "first_name": first_name,
        "last_name": last_name,
    }

    response = await client.post("/api/v1/auth/register", json=register_data)
    assert response.status_code == 201

    # 验证邮箱（从数据库获取 token）
    result = await db_session.execute(
        select(EmailVerification).where(
            EmailVerification.email == email,
            EmailVerification.purpose == VerificationPurpose.EMAIL_VERIFY,
        )
    )
    verification = result.scalar_one()

    # 验证邮箱
    response = await client.get(f"/api/v1/auth/verify-email?token={verification.token}")
    assert response.status_code == 200

    return register_data


async def get_user_by_email(db_session: AsyncSession, email: str) -> User:
    """根据邮箱获取用户。

    Args:
        db_session: 数据库会话
        email: 用户邮箱

    Returns:
        用户对象
    """
    stmt = select(User).where(User.email == email)
    user = (await db_session.execute(stmt)).scalar_one()
    return user


async def perform_login(
    client: AsyncClient,
    email: str,
    password: str,
) -> tuple[int, dict]:
    """执行登录操作。

    Args:
        client: HTTP客户端
        email: 邮箱
        password: 密码

    Returns:
        元组：(状态码, 响应数据)
    """
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    return response.status_code, response.json()


async def perform_logout(client: AsyncClient, access_token: str) -> tuple[int, dict]:
    """执行登出操作。

    Args:
        client: HTTP客户端
        access_token: 访问令牌

    Returns:
        元组：(状态码, 响应数据)
    """
    headers = {"Authorization": f"Bearer {access_token}"}
    response = await client.post("/api/v1/auth/logout", headers=headers)
    return response.status_code, response.json()


async def perform_token_refresh(
    client: AsyncClient,
    access_token: str,
    refresh_token: str,
) -> tuple[int, dict]:
    """执行令牌刷新操作。

    Args:
        client: HTTP客户端
        access_token: 访问令牌
        refresh_token: 刷新令牌

    Returns:
        元组：(状态码, 响应数据)
    """
    headers = {"Authorization": f"Bearer {access_token}"}
    response = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_token},
        headers=headers,
    )
    return response.status_code, response.json()
