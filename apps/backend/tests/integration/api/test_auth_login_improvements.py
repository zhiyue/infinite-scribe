"""测试认证登录改进功能。"""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.common.services.user_service import UserService
from src.common.services.session_service import session_service
from src.common.services.redis_service import redis_service
from src.core.config import settings


@pytest.mark.asyncio
async def test_login_with_failed_attempts_tracking(client: AsyncClient, db_session: AsyncSession):
    """测试登录失败尝试次数跟踪和返回剩余尝试次数。"""
    # 创建测试用户
    user_service = UserService()
    user_data = {
        "username": "testuser",
        "email": "test@example.com",
        "password": "ValidPass123!",
        "first_name": "Test",
        "last_name": "User",
    }
    result = await user_service.register_user(db_session, user_data)
    assert result["success"]
    
    # 验证邮箱（跳过邮件验证步骤）
    from sqlalchemy import select
    from src.models.user import User
    stmt = select(User).where(User.email == user_data["email"])
    user = (await db_session.execute(stmt)).scalar_one()
    user.is_verified = True
    await db_session.commit()
    
    # 测试第一次登录失败
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": user_data["email"], "password": "WrongPassword"},
    )
    assert response.status_code == 401
    error_detail = response.json()["detail"]
    assert "remaining" in error_detail["message"].lower()
    assert error_detail["remaining_attempts"] == 4
    
    # 测试第二次登录失败
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": user_data["email"], "password": "WrongPassword"},
    )
    assert response.status_code == 401
    error_detail = response.json()["detail"]
    assert error_detail["remaining_attempts"] == 3
    
    # 测试多次失败直到账户被锁定
    for i in range(3):
        response = await client.post(
            "/api/v1/auth/login",
            json={"email": user_data["email"], "password": "WrongPassword"},
        )
    
    # 最后一次应该返回账户锁定
    assert response.status_code == 423
    error_detail = response.json()["detail"]
    assert "locked" in error_detail["message"].lower()
    assert "locked_until" in error_detail
    
    # 尝试用正确密码登录应该仍然失败（账户已锁定）
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": user_data["email"], "password": user_data["password"]},
    )
    assert response.status_code == 423


@pytest.mark.asyncio
async def test_session_redis_caching(client: AsyncClient, db_session: AsyncSession):
    """测试 Session Redis 缓存功能。"""
    # 确保 Redis 连接
    await redis_service.connect()
    
    # 创建并验证测试用户
    user_service = UserService()
    user_data = {
        "username": "cachetest",
        "email": "cache@example.com",
        "password": "ValidPass123!",
        "first_name": "Cache",
        "last_name": "Test",
    }
    result = await user_service.register_user(db_session, user_data)
    assert result["success"]
    
    # 验证邮箱
    from sqlalchemy import select
    from src.models.user import User
    stmt = select(User).where(User.email == user_data["email"])
    user = (await db_session.execute(stmt)).scalar_one()
    user.is_verified = True
    await db_session.commit()
    
    # 登录以创建 session
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": user_data["email"], "password": user_data["password"]},
    )
    assert response.status_code == 200
    data = response.json()
    access_token = data["access_token"]
    
    # 从 access token 中提取 JTI
    from src.common.services.jwt_service import jwt_service
    payload = jwt_service.verify_token(access_token, "access")
    jti = payload["jti"]
    
    # 检查 session 是否被缓存到 Redis
    cache_key = f"session:jti:{jti}"
    cached_data = await redis_service.get(cache_key)
    assert cached_data is not None
    
    # 验证缓存的数据
    import json
    session_data = json.loads(cached_data)
    assert session_data["jti"] == jti
    assert session_data["is_active"] == True
    
    # 登出
    headers = {"Authorization": f"Bearer {access_token}"}
    response = await client.post("/api/v1/auth/logout", headers=headers)
    assert response.status_code == 200
    
    # 检查缓存是否被清除
    cached_data = await redis_service.get(cache_key)
    assert cached_data is None


@pytest.mark.asyncio
async def test_token_refresh_with_session_update(client: AsyncClient, db_session: AsyncSession):
    """测试令牌刷新时的 Session 更新和缓存更新。"""
    # 创建并验证测试用户
    user_service = UserService()
    user_data = {
        "username": "refreshtest",
        "email": "refresh@example.com",
        "password": "ValidPass123!",
        "first_name": "Refresh",
        "last_name": "Test",
    }
    result = await user_service.register_user(db_session, user_data)
    assert result["success"]
    
    # 验证邮箱
    from sqlalchemy import select
    from src.models.user import User
    stmt = select(User).where(User.email == user_data["email"])
    user = (await db_session.execute(stmt)).scalar_one()
    user.is_verified = True
    await db_session.commit()
    
    # 登录
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": user_data["email"], "password": user_data["password"]},
    )
    assert response.status_code == 200
    data = response.json()
    old_access_token = data["access_token"]
    old_refresh_token = data["refresh_token"]
    
    # 刷新令牌
    headers = {"Authorization": f"Bearer {old_access_token}"}
    response = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": old_refresh_token},
        headers=headers,
    )
    assert response.status_code == 200
    
    new_data = response.json()
    new_access_token = new_data["access_token"]
    new_refresh_token = new_data["refresh_token"]
    
    # 验证新旧令牌不同
    assert new_access_token != old_access_token
    assert new_refresh_token != old_refresh_token
    
    # 验证旧的 access token 被加入黑名单
    from src.common.services.jwt_service import jwt_service
    old_payload = jwt_service.verify_token(old_access_token, "access")
    old_jti = old_payload["jti"]
    assert jwt_service.is_token_blacklisted(old_jti)
    
    # 验证新的 session 被缓存
    new_payload = jwt_service.verify_token(new_access_token, "access")
    new_jti = new_payload["jti"]
    cache_key = f"session:jti:{new_jti}"
    cached_data = await redis_service.get(cache_key)
    assert cached_data is not None