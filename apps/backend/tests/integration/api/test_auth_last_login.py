"""集成测试：验证登录时 last_login_at 字段的更新。"""

import asyncio
from datetime import datetime

import httpx
import pytest
from sqlalchemy import select
from src.common.utils.datetime_utils import utc_now
from src.models.user import User


class TestAuthLastLogin:
    """测试登录时 last_login_at 字段的更新。"""

    @pytest.mark.asyncio
    async def test_login_updates_last_login_at_in_database(
        self, postgres_async_client: httpx.AsyncClient, postgres_test_session
    ):
        """测试成功登录时 last_login_at 在数据库中被更新。"""
        # 注册新用户
        register_data = {
            "email": "lastlogin@example.com",
            "username": "lastloginuser",
            "password": "SecurePass123!",
            "first_name": "Last",
            "last_name": "Login",
        }

        response = await postgres_async_client.post("/api/v1/auth/register", json=register_data)
        assert response.status_code == 201

        # 验证邮箱（从数据库获取 token）
        from src.models.email_verification import EmailVerification, VerificationPurpose

        result = await postgres_test_session.execute(
            select(EmailVerification).where(
                EmailVerification.email == register_data["email"],
                EmailVerification.purpose == VerificationPurpose.EMAIL_VERIFY,
            )
        )
        verification = result.scalar_one()

        # 验证邮箱
        response = await postgres_async_client.get(f"/api/v1/auth/verify-email?token={verification.token}")
        assert response.status_code == 200

        # 检查用户初始状态
        result = await postgres_test_session.execute(select(User).where(User.email == register_data["email"]))
        user = result.scalar_one()
        assert user.last_login_at is None
        assert user.last_login_ip is None

        # 记录登录前的时间
        before_login = utc_now()

        # 等待一小段时间确保时间差异
        await asyncio.sleep(0.1)

        # 执行登录
        login_data = {
            "email": register_data["email"],
            "password": register_data["password"],
        }
        response = await postgres_async_client.post("/api/v1/auth/login", json=login_data)
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data

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
        first_login_ip = user.last_login_ip

        # 等待一小段时间
        await asyncio.sleep(0.1)

        # 第二次登录
        response = await postgres_async_client.post("/api/v1/auth/login", json=login_data)
        assert response.status_code == 200

        # 再次从数据库获取用户信息
        await postgres_test_session.refresh(user)

        # 验证 last_login_at 再次被更新
        assert user.last_login_at > first_login_at

        # 如果 IP 相同，应该保持不变或更新为相同值
        assert user.last_login_ip is not None

    @pytest.mark.asyncio
    async def test_failed_login_does_not_update_last_login_at(
        self, postgres_async_client: httpx.AsyncClient, postgres_test_session
    ):
        """测试登录失败时不更新 last_login_at。"""
        # 注册并验证用户
        register_data = {
            "email": "failedlogin@example.com",
            "username": "failedloginuser",
            "password": "SecurePass123!",
            "first_name": "Failed",
            "last_name": "Login",
        }

        response = await postgres_async_client.post("/api/v1/auth/register", json=register_data)
        assert response.status_code == 201

        # 验证邮箱
        from src.models.email_verification import EmailVerification, VerificationPurpose

        result = await postgres_test_session.execute(
            select(EmailVerification).where(
                EmailVerification.email == register_data["email"],
                EmailVerification.purpose == VerificationPurpose.EMAIL_VERIFY,
            )
        )
        verification = result.scalar_one()

        response = await postgres_async_client.get(f"/api/v1/auth/verify-email?token={verification.token}")
        assert response.status_code == 200

        # 成功登录一次以设置 last_login_at
        login_data = {
            "email": register_data["email"],
            "password": register_data["password"],
        }
        response = await postgres_async_client.post("/api/v1/auth/login", json=login_data)
        assert response.status_code == 200

        # 获取用户当前的 last_login_at
        result = await postgres_test_session.execute(select(User).where(User.email == register_data["email"]))
        user = result.scalar_one()
        original_last_login_at = user.last_login_at
        assert original_last_login_at is not None

        # 等待一小段时间
        await asyncio.sleep(0.1)

        # 使用错误密码尝试登录
        wrong_login_data = {
            "email": register_data["email"],
            "password": "WrongPassword123!",
        }
        response = await postgres_async_client.post("/api/v1/auth/login", json=wrong_login_data)
        assert response.status_code == 401

        # 刷新用户信息
        await postgres_test_session.refresh(user)

        # 验证 last_login_at 没有改变
        assert user.last_login_at == original_last_login_at

        # 验证 failed_login_attempts 增加
        assert user.failed_login_attempts == 1

    @pytest.mark.asyncio
    async def test_unverified_user_login_does_not_update_last_login_at(
        self, postgres_async_client: httpx.AsyncClient, postgres_test_session
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

        response = await postgres_async_client.post("/api/v1/auth/register", json=register_data)
        assert response.status_code == 201

        # 检查用户初始状态
        result = await postgres_test_session.execute(select(User).where(User.email == register_data["email"]))
        user = result.scalar_one()
        assert user.last_login_at is None
        assert not user.is_verified

        # 尝试登录
        login_data = {
            "email": register_data["email"],
            "password": register_data["password"],
        }
        response = await postgres_async_client.post("/api/v1/auth/login", json=login_data)
        assert response.status_code == 403
        error_detail = response.json()["detail"]
        # detail 可能是字符串或字典
        if isinstance(error_detail, dict):
            error_text = str(error_detail).lower()
        else:
            error_text = error_detail.lower()
        assert "verify" in error_text

        # 刷新用户信息
        await postgres_test_session.refresh(user)

        # 验证 last_login_at 仍然是 None
        assert user.last_login_at is None
        assert user.last_login_ip is None
