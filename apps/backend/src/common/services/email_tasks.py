"""邮件异步任务处理模块

提供邮件发送的异步任务包装器，支持重试和错误处理。
"""

import logging
from typing import Any

from fastapi import BackgroundTasks
from tenacity import retry, stop_after_attempt, wait_exponential

from src.common.services.email_service import email_service
from src.core.config import settings

logger = logging.getLogger(__name__)


class EmailTasks:
    """邮件异步任务处理类"""

    def __init__(self):
        """初始化邮件任务处理器"""
        self.max_retries = getattr(settings.auth, "email_max_retries", 3)
        self.retry_delay = getattr(settings.auth, "email_retry_delay_seconds", 60)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=60),
        reraise=False,
    )
    async def _send_email_with_retry(
        self,
        email_type: str,
        to_email: str,
        **kwargs: Any,
    ) -> bool:
        """带重试机制的邮件发送

        Args:
            email_type: 邮件类型（verification, password_reset, welcome）
            to_email: 收件人邮箱
            **kwargs: 其他邮件参数

        Returns:
            是否发送成功
        """
        try:
            logger.info(f"尝试发送 {email_type} 邮件到 {to_email}")

            # 根据邮件类型调用相应的发送方法
            if email_type == "verification":
                result = await email_service.send_verification_email(
                    to_email,
                    kwargs.get("user_name", ""),
                    kwargs.get("verification_url", ""),
                )
            elif email_type == "password_reset":
                result = await email_service.send_password_reset_email(
                    to_email,
                    kwargs.get("user_name", ""),
                    kwargs.get("reset_url", ""),
                )
            elif email_type == "welcome":
                result = await email_service.send_welcome_email(
                    to_email,
                    kwargs.get("user_name", ""),
                )
            else:
                logger.error(f"未知的邮件类型: {email_type}")
                return False

            if result:
                logger.info(f"成功发送 {email_type} 邮件到 {to_email}")
            else:
                logger.warning(f"发送 {email_type} 邮件到 {to_email} 失败")

            return result

        except Exception as e:
            logger.error(f"发送 {email_type} 邮件到 {to_email} 时出错: {e}")
            # 重新抛出异常以触发重试
            raise

    async def send_verification_email_async(
        self,
        background_tasks: BackgroundTasks,
        user_email: str,
        user_name: str,
        verification_url: str,
    ) -> None:
        """异步发送验证邮件

        Args:
            background_tasks: FastAPI 后台任务对象
            user_email: 用户邮箱
            user_name: 用户名称
            verification_url: 验证链接
        """
        background_tasks.add_task(
            self._send_email_with_retry,
            email_type="verification",
            to_email=user_email,
            user_name=user_name,
            verification_url=verification_url,
        )
        logger.info(f"已将验证邮件任务加入队列: {user_email}")

    async def send_password_reset_email_async(
        self,
        background_tasks: BackgroundTasks,
        user_email: str,
        user_name: str,
        reset_url: str,
    ) -> None:
        """异步发送密码重置邮件

        Args:
            background_tasks: FastAPI 后台任务对象
            user_email: 用户邮箱
            user_name: 用户名称
            reset_url: 重置链接
        """
        background_tasks.add_task(
            self._send_email_with_retry,
            email_type="password_reset",
            to_email=user_email,
            user_name=user_name,
            reset_url=reset_url,
        )
        logger.info(f"已将密码重置邮件任务加入队列: {user_email}")

    async def send_welcome_email_async(
        self,
        background_tasks: BackgroundTasks,
        user_email: str,
        user_name: str,
    ) -> None:
        """异步发送欢迎邮件

        Args:
            background_tasks: FastAPI 后台任务对象
            user_email: 用户邮箱
            user_name: 用户名称
        """
        background_tasks.add_task(
            self._send_email_with_retry,
            email_type="welcome",
            to_email=user_email,
            user_name=user_name,
        )
        logger.info(f"已将欢迎邮件任务加入队列: {user_email}")


# 创建全局实例
email_tasks = EmailTasks()
