"""集成测试：验证登录时 last_login_at 字段的更新。"""

import asyncio
from datetime import datetime

import httpx
import pytest
from src.common.utils.datetime_utils import utc_now
from tests.integration.api.auth_test_helpers import (
    create_and_verify_test_user_with_registration,
    get_user_by_email,
    perform_login,
)


class TestAuthLastLogin:
    """测试登录时 last_login_at 字段的更新。"""

    @pytest.mark.asyncio
    async def test_login_updates_last_login_at_in_database(
        self, async_client: httpx.AsyncClient, postgres_test_session
    ):
        """测试成功登录时 last_login_at 在数据库中被更新。"""
        # 创建并验证测试用户
        register_data = await create_and_verify_test_user_with_registration(
            async_client,
            postgres_test_session,
            username="lastloginuser",
            email="lastlogin@example.com",
            password="SecurePass123!",
            first_name="Last",
            last_name="Login",
        )

        # 检查用户初始状态
        user = await get_user_by_email(postgres_test_session, register_data["email"])
        assert user.last_login_at is None
        assert user.last_login_ip is None

        # 记录登录前的时间
        before_login = utc_now()

        # 等待一小段时间确保时间差异
        await asyncio.sleep(0.1)

        # 执行登录
        status_code, response_data = await perform_login(
            async_client, register_data["email"], register_data["password"]
        )
        assert status_code == 200
        assert "access_token" in response_data
        assert "refresh_token" in response_data

        # 从数据库重新获取用户信息
        await postgres_test_session.refresh(user)

        # 验证 last_login_at 被更新
        assert user.last_login_at is not None
        assert isinstance(user.last_login_at, datetime)
        assert user.last_login_at > before_login

        # 验证 last_login_ip 被更新（在测试环境中可能是 testclient）
        assert user.last_login_ip is not None

        # 记录第一次登录时间
        first_login_at = user.last_login_at

        # 等待一小段时间
        await asyncio.sleep(0.1)

        # 第二次登录
        status_code, response_data = await perform_login(
            async_client, register_data["email"], register_data["password"]
        )
        assert status_code == 200

        # 再次从数据库获取用户信息
        await postgres_test_session.refresh(user)

        # 验证 last_login_at 再次被更新
        assert user.last_login_at > first_login_at

        # 如果 IP 相同，应该保持不变或更新为相同值
        assert user.last_login_ip is not None

    @pytest.mark.asyncio
    async def test_failed_login_does_not_update_last_login_at(
        self, async_client: httpx.AsyncClient, postgres_test_session
    ):
        """测试登录失败时不更新 last_login_at。"""
        # 创建并验证测试用户
        register_data = await create_and_verify_test_user_with_registration(
            async_client,
            postgres_test_session,
            username="failedloginuser",
            email="failedlogin@example.com",
            password="SecurePass123!",
            first_name="Failed",
            last_name="Login",
        )

        # 成功登录一次以设置 last_login_at
        status_code, response_data = await perform_login(
            async_client, register_data["email"], register_data["password"]
        )
        assert status_code == 200

        # 获取用户当前的 last_login_at
        user = await get_user_by_email(postgres_test_session, register_data["email"])
        original_last_login_at = user.last_login_at
        assert original_last_login_at is not None

        # 等待一小段时间
        await asyncio.sleep(0.1)

        # 使用错误密码尝试登录
        status_code, response_data = await perform_login(async_client, register_data["email"], "WrongPassword123!")
        assert status_code == 401

        # 刷新用户信息
        await postgres_test_session.refresh(user)

        # 验证 last_login_at 没有改变
        assert user.last_login_at == original_last_login_at

        # 验证 failed_login_attempts 增加
        assert user.failed_login_attempts == 1

    @pytest.mark.asyncio
    async def test_unverified_user_login_does_not_update_last_login_at(
        self, async_client: httpx.AsyncClient, postgres_test_session
    ):
        """测试未验证用户登录时不更新 last_login_at。"""
        # 注册新用户但不验证邮箱
        register_data = {
            "email": "unverified@example.com",
            "username": "unverifieduser",
            "password": "SecurePass123!",
            "first_name": "Unverified",
            "last_name": "User",
        }

        response = await async_client.post("/api/v1/auth/register", json=register_data)
        assert response.status_code == 201

        # 检查用户初始状态
        user = await get_user_by_email(postgres_test_session, register_data["email"])
        assert user.last_login_at is None
        assert not user.is_verified

        # 尝试登录
        status_code, response_data = await perform_login(
            async_client, register_data["email"], register_data["password"]
        )
        assert status_code == 403
        error_detail = response_data["detail"]
        # detail 可能是字符串或字典
        error_text = str(error_detail).lower() if isinstance(error_detail, dict) else error_detail.lower()
        assert "verify" in error_text

        # 刷新用户信息
        await postgres_test_session.refresh(user)

        # 验证 last_login_at 仍然是 None
        assert user.last_login_at is None
        assert user.last_login_ip is None
