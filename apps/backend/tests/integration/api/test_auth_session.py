"""测试认证会话管理功能，包括Redis缓存和令牌刷新。"""

import json

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from src.common.services.jwt_service import jwt_service
from src.db.redis import redis_service
from tests.integration.api.auth_test_helpers import (
    create_and_verify_test_user,
    perform_login,
    perform_logout,
    perform_token_refresh,
)


@pytest.mark.asyncio
async def test_session_redis_caching(client: AsyncClient, db_session: AsyncSession):
    """测试 Session Redis 缓存功能。"""
    # 确保 Redis 连接
    await redis_service.connect()

    # 创建并验证测试用户
    user_data = await create_and_verify_test_user(client, db_session, username="cachetest", email="cache@example.com")

    # 登录以创建 session
    status_code, response_data = await perform_login(client, user_data["email"], user_data["password"])
    assert status_code == 200
    access_token = response_data["access_token"]

    # 从 access token 中提取 JTI
    payload = jwt_service.verify_token(access_token, "access")
    jti = payload["jti"]

    # 检查 session 是否被缓存到 Redis
    cache_key = f"session:jti:{jti}"
    cached_data = await redis_service.get(cache_key)
    assert cached_data is not None

    # 验证缓存的数据
    session_data = json.loads(cached_data)
    assert session_data["jti"] == jti
    assert session_data["is_active"] is True

    # 登出
    logout_status, logout_response = await perform_logout(client, access_token)
    assert logout_status == 200

    # 检查缓存是否被清除
    cached_data = await redis_service.get(cache_key)
    assert cached_data is None


@pytest.mark.asyncio
async def test_token_refresh_with_session_update(client: AsyncClient, db_session: AsyncSession):
    """测试令牌刷新时的 Session 更新和缓存更新。"""
    # 创建并验证测试用户
    user_data = await create_and_verify_test_user(
        client, db_session, username="refreshtest", email="refresh@example.com"
    )

    # 登录
    status_code, response_data = await perform_login(client, user_data["email"], user_data["password"])
    assert status_code == 200
    old_access_token = response_data["access_token"]
    old_refresh_token = response_data["refresh_token"]

    # 刷新令牌
    refresh_status, refresh_data = await perform_token_refresh(client, old_access_token, old_refresh_token)
    assert refresh_status == 200

    new_access_token = refresh_data["access_token"]
    new_refresh_token = refresh_data["refresh_token"]

    # 验证新旧令牌不同
    assert new_access_token != old_access_token
    assert new_refresh_token != old_refresh_token

    # 验证旧的 access token 被加入黑名单
    # 旧的 access token 应该已经被黑名单化，所以验证会失败
    from jose.exceptions import JWTError

    with pytest.raises(JWTError):  # JWT token revocation error
        jwt_service.verify_token(old_access_token, "access")

    # 或者我们可以从旧令牌中提取 JTI（不验证）来检查黑名单
    from jose import jwt as jose_jwt

    old_payload = jose_jwt.decode(old_access_token, "", options={"verify_signature": False})
    old_jti = old_payload["jti"]
    assert jwt_service.is_token_blacklisted(old_jti)

    # 验证新的 session 被缓存
    new_payload = jwt_service.verify_token(new_access_token, "access")
    new_jti = new_payload["jti"]
    cache_key = f"session:jti:{new_jti}"
    cached_data = await redis_service.get(cache_key)
    assert cached_data is not None


@pytest.mark.asyncio
async def test_session_cache_consistency_after_multiple_refreshes(client: AsyncClient, db_session: AsyncSession):
    """测试多次令牌刷新后会话缓存的一致性。"""
    # 创建并验证测试用户
    user_data = await create_and_verify_test_user(
        client, db_session, username="multirefresh", email="multirefresh@example.com"
    )

    # 初始登录
    status_code, response_data = await perform_login(client, user_data["email"], user_data["password"])
    assert status_code == 200

    current_access_token = response_data["access_token"]
    current_refresh_token = response_data["refresh_token"]

    # 记录所有生成的JTI
    generated_jtis = []

    # 连续刷新3次
    for _i in range(3):
        # 刷新令牌
        refresh_status, refresh_data = await perform_token_refresh(client, current_access_token, current_refresh_token)
        assert refresh_status == 200

        # 更新当前令牌
        current_access_token = refresh_data["access_token"]
        current_refresh_token = refresh_data["refresh_token"]

        # 提取并记录JTI
        payload = jwt_service.verify_token(current_access_token, "access")
        jti = payload["jti"]
        generated_jtis.append(jti)

        # 验证当前session被缓存
        cache_key = f"session:jti:{jti}"
        cached_data = await redis_service.get(cache_key)
        assert cached_data is not None

        # 验证缓存数据的正确性
        session_data = json.loads(cached_data)
        assert session_data["jti"] == jti
        assert session_data["is_active"] is True

    # 验证所有JTI都不相同
    assert len(set(generated_jtis)) == 3

    # 最终登出
    logout_status, logout_response = await perform_logout(client, current_access_token)
    assert logout_status == 200

    # 验证最后的session缓存被清除
    final_jti = generated_jtis[-1]
    cache_key = f"session:jti:{final_jti}"
    cached_data = await redis_service.get(cache_key)
    assert cached_data is None


@pytest.mark.asyncio
async def test_concurrent_sessions_independent_caching(client: AsyncClient, db_session: AsyncSession):
    """测试并发会话的独立缓存。"""
    # 创建并验证测试用户
    user_data = await create_and_verify_test_user(
        client, db_session, username="concurrent", email="concurrent@example.com"
    )

    # 创建第一个会话
    status_code1, response_data1 = await perform_login(client, user_data["email"], user_data["password"])
    assert status_code1 == 200
    access_token1 = response_data1["access_token"]

    # 创建第二个会话
    status_code2, response_data2 = await perform_login(client, user_data["email"], user_data["password"])
    assert status_code2 == 200
    access_token2 = response_data2["access_token"]

    # 提取两个会话的JTI
    payload1 = jwt_service.verify_token(access_token1, "access")
    payload2 = jwt_service.verify_token(access_token2, "access")
    jti1 = payload1["jti"]
    jti2 = payload2["jti"]

    # 验证JTI不同
    assert jti1 != jti2

    # 验证两个会话都被缓存
    cache_key1 = f"session:jti:{jti1}"
    cache_key2 = f"session:jti:{jti2}"

    cached_data1 = await redis_service.get(cache_key1)
    cached_data2 = await redis_service.get(cache_key2)

    assert cached_data1 is not None
    assert cached_data2 is not None

    # 验证缓存数据的独立性
    session_data1 = json.loads(cached_data1)
    session_data2 = json.loads(cached_data2)

    assert session_data1["jti"] == jti1
    assert session_data2["jti"] == jti2
    assert session_data1["jti"] != session_data2["jti"]

    # 登出第一个会话
    logout_status1, _ = await perform_logout(client, access_token1)
    assert logout_status1 == 200

    # 验证第一个会话缓存被清除，第二个会话缓存仍然存在
    cached_data1_after = await redis_service.get(cache_key1)
    cached_data2_after = await redis_service.get(cache_key2)

    assert cached_data1_after is None
    assert cached_data2_after is not None

    # 登出第二个会话
    logout_status2, _ = await perform_logout(client, access_token2)
    assert logout_status2 == 200

    # 验证第二个会话缓存也被清除
    cached_data2_final = await redis_service.get(cache_key2)
    assert cached_data2_final is None
