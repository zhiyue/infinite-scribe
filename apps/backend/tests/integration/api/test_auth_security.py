"""测试认证安全功能，包括登录失败次数跟踪和账户锁定机制。"""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.integration.api.auth_test_helpers import create_and_verify_test_user, get_user_by_email, perform_login


@pytest.mark.asyncio
async def test_login_with_failed_attempts_tracking(client: AsyncClient, db_session: AsyncSession):
    """测试登录失败尝试次数跟踪和返回剩余尝试次数。"""
    # 创建并验证测试用户
    user_data = await create_and_verify_test_user(
        client, db_session, username="securitytest", email="security@example.com"
    )

    # 测试第一次登录失败
    status_code, response_data = await perform_login(client, user_data["email"], "WrongPassword")
    assert status_code == 401
    error_detail = response_data["detail"]
    assert "remaining" in error_detail["message"].lower()
    assert error_detail["remaining_attempts"] == 4

    # 测试第二次登录失败
    status_code, response_data = await perform_login(client, user_data["email"], "WrongPassword")
    assert status_code == 401
    error_detail = response_data["detail"]
    assert error_detail["remaining_attempts"] == 3

    # 测试多次失败直到账户被锁定
    for _i in range(3):
        status_code, response_data = await perform_login(client, user_data["email"], "WrongPassword")

    # 最后一次应该返回账户锁定
    assert status_code == 423
    error_detail = response_data["detail"]
    assert "locked" in error_detail["message"].lower()
    assert "locked_until" in error_detail

    # 尝试用正确密码登录应该仍然失败（账户已锁定）
    status_code, response_data = await perform_login(client, user_data["email"], user_data["password"])
    assert status_code == 423


@pytest.mark.asyncio
async def test_failed_login_increments_counter(client: AsyncClient, db_session: AsyncSession):
    """测试失败登录会增加失败计数器。"""
    # 创建并验证测试用户
    user_data = await create_and_verify_test_user(
        client, db_session, username="countertest", email="counter@example.com"
    )

    # 获取初始用户状态
    user = await get_user_by_email(db_session, user_data["email"])
    assert user.failed_login_attempts == 0

    # 执行一次失败的登录
    status_code, response_data = await perform_login(client, user_data["email"], "WrongPassword")
    assert status_code == 401

    # 刷新用户数据并检查计数器
    await db_session.refresh(user)
    assert user.failed_login_attempts == 1

    # 再执行一次失败的登录
    status_code, response_data = await perform_login(client, user_data["email"], "WrongPassword")
    assert status_code == 401

    # 检查计数器再次增加
    await db_session.refresh(user)
    assert user.failed_login_attempts == 2


@pytest.mark.asyncio
async def test_successful_login_resets_failed_attempts(client: AsyncClient, db_session: AsyncSession):
    """测试成功登录会重置失败尝试次数。"""
    # 创建并验证测试用户
    user_data = await create_and_verify_test_user(client, db_session, username="resettest", email="reset@example.com")

    # 先进行几次失败的登录
    for _i in range(2):
        status_code, response_data = await perform_login(client, user_data["email"], "WrongPassword")
        assert status_code == 401

    # 确认失败次数增加
    user = await get_user_by_email(db_session, user_data["email"])
    assert user.failed_login_attempts == 2

    # 成功登录
    status_code, response_data = await perform_login(client, user_data["email"], user_data["password"])
    assert status_code == 200
    assert "access_token" in response_data

    # 检查失败次数被重置
    await db_session.refresh(user)
    assert user.failed_login_attempts == 0


@pytest.mark.asyncio
async def test_account_lockout_prevents_all_login_attempts(client: AsyncClient, db_session: AsyncSession):
    """测试账户锁定后阻止所有登录尝试（包括正确密码）。"""
    # 创建并验证测试用户
    user_data = await create_and_verify_test_user(
        client, db_session, username="lockouttest", email="lockout@example.com"
    )

    # 连续5次错误登录触发账户锁定
    for _i in range(5):
        status_code, response_data = await perform_login(client, user_data["email"], "WrongPassword")

    # 最后一次应该返回锁定状态
    assert status_code == 423

    # 验证用户状态
    user = await get_user_by_email(db_session, user_data["email"])
    assert user.is_locked
    assert user.locked_until is not None
    assert user.failed_login_attempts >= 5

    # 尝试用正确密码登录，应该被拒绝
    status_code, response_data = await perform_login(client, user_data["email"], user_data["password"])
    assert status_code == 423
    error_detail = response_data["detail"]
    assert "locked" in error_detail["message"].lower()

    # 尝试用错误密码登录，也应该被拒绝
    status_code, response_data = await perform_login(client, user_data["email"], "StillWrongPassword")
    assert status_code == 423


@pytest.mark.asyncio
async def test_lockout_error_includes_unlock_time(client: AsyncClient, db_session: AsyncSession):
    """测试锁定错误消息包含解锁时间信息。"""
    # 创建并验证测试用户
    user_data = await create_and_verify_test_user(
        client, db_session, username="unlocktime", email="unlocktime@example.com"
    )

    # 触发账户锁定
    for _i in range(5):
        status_code, response_data = await perform_login(client, user_data["email"], "WrongPassword")

    # 检查锁定响应包含解锁时间
    assert status_code == 423
    error_detail = response_data["detail"]
    assert "locked_until" in error_detail
    assert error_detail["locked_until"] is not None

    # 验证时间格式合理（应该是 ISO 格式的时间字符串）
    locked_until = error_detail["locked_until"]
    assert isinstance(locked_until, str)
    # 简单检查是否是 ISO 时间格式
    assert "T" in locked_until or " " in locked_until
