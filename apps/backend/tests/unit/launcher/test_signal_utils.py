import asyncio
import signal
from unittest.mock import AsyncMock, Mock, patch

import pytest

from launcher.signal_utils import register_shutdown_handler, wait_for_shutdown_signal


class TestSignalUtils:
    @pytest.mark.asyncio
    async def test_register_shutdown_handler_posix(self):
        """POSIX系统应使用loop.add_signal_handler，只注册SIGINT"""
        mock_loop = Mock()
        mock_callback = AsyncMock()

        with (
            patch("launcher.signal_utils.os.name", "posix"),
            patch("launcher.signal_utils.asyncio.get_running_loop", return_value=mock_loop),
        ):
            cleanup = register_shutdown_handler(mock_callback)

            # 验证只注册了SIGINT信号处理器（避免与agents冲突）
            mock_loop.add_signal_handler.assert_called_once()
            assert mock_loop.add_signal_handler.call_args.args[0] == signal.SIGINT

            # 清理
            cleanup()

    @pytest.mark.asyncio
    async def test_register_shutdown_handler_windows(self):
        """Windows系统应使用signal.signal回退"""
        mock_callback = AsyncMock()

        with patch("launcher.signal_utils.os.name", "nt"), patch("launcher.signal_utils.signal.signal") as mock_signal:
            cleanup = register_shutdown_handler(mock_callback)

            # 验证注册了SIGINT信号处理器
            mock_signal.assert_called_once()
            assert mock_signal.call_args[0][0] == signal.SIGINT

            # 清理
            cleanup()

    @pytest.mark.asyncio
    async def test_signal_callback_safe_execution(self):
        """信号回调应安全执行"""
        callback_executed = asyncio.Event()
        mock_loop = Mock()

        async def test_callback():
            callback_executed.set()

        with (
            patch("launcher.signal_utils.os.name", "posix"),
            patch("launcher.signal_utils.asyncio.get_running_loop", return_value=mock_loop),
        ):
            cleanup = register_shutdown_handler(test_callback)

            # 获取注册的回调函数
            registered_callback = mock_loop.add_signal_handler.call_args.args[1]

            # 执行回调
            registered_callback()

            # 验证通过call_soon_threadsafe安全调度
            mock_loop.call_soon_threadsafe.assert_called_once()
            cleanup()

    @pytest.mark.asyncio
    async def test_wait_for_shutdown_signal_integration(self):
        """集成测试：等待关闭信号"""
        with patch("launcher.signal_utils.register_shutdown_handler") as mock_register:
            mock_cleanup = Mock()
            captured_callback = None

            def capture_callback(callback):
                nonlocal captured_callback
                captured_callback = callback
                return mock_cleanup

            mock_register.side_effect = capture_callback

            # 启动等待任务
            wait_task = asyncio.create_task(wait_for_shutdown_signal())

            # 等待register被调用并获取回调
            await asyncio.sleep(0.01)
            assert captured_callback is not None

            # 模拟信号触发回调
            await captured_callback()

            # 等待任务完成
            try:
                await asyncio.wait_for(wait_task, timeout=1.0)
            except TimeoutError:
                wait_task.cancel()
                # 确保finally块执行
                try:
                    await wait_task
                except asyncio.CancelledError:
                    pass

            # 验证清理被调用
            mock_cleanup.assert_called_once()

    @pytest.mark.asyncio
    async def test_signal_registration_failure_handling(self):
        """测试信号注册失败的处理"""
        mock_callback = AsyncMock()

        with (
            patch("launcher.signal_utils.os.name", "posix"),
            patch("launcher.signal_utils.asyncio.get_running_loop", side_effect=RuntimeError("No loop")),
        ):
            # 应该返回空清理函数而不是抛出异常
            cleanup = register_shutdown_handler(mock_callback)

            # 清理函数应该可以安全调用
            cleanup()
