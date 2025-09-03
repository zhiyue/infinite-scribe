import asyncio
import contextlib
import signal
from unittest.mock import AsyncMock, Mock, patch

import pytest

from launcher.signal_utils import register_shutdown_handler, wait_for_shutdown_signal


class TestSignalUtils:
    @pytest.mark.asyncio
    async def test_register_shutdown_handler_posix(self):
        """POSIX系统应使用loop.add_signal_handler，注册SIGINT和SIGTERM"""
        mock_loop = Mock()
        mock_callback = AsyncMock()

        with (
            patch("launcher.signal_utils.os.name", "posix"),
            patch("launcher.signal_utils.asyncio.get_running_loop", return_value=mock_loop),
        ):
            cleanup = register_shutdown_handler(mock_callback)

            # 验证注册了SIGINT和SIGTERM信号处理器（统一信号管理）
            assert mock_loop.add_signal_handler.call_count == 2

            # 检查调用的信号类型
            call_args = [call.args[0] for call in mock_loop.add_signal_handler.call_args_list]
            assert signal.SIGINT in call_args
            assert signal.SIGTERM in call_args

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
                with contextlib.suppress(asyncio.CancelledError):
                    await wait_task

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
            # 注册失败时应该返回None而不是抛出异常
            cleanup = register_shutdown_handler(mock_callback)

            # 应该返回None表示注册失败
            assert cleanup is None

    @pytest.mark.asyncio
    async def test_wait_for_shutdown_signal_with_keyboard_interrupt_fallback(self):
        """测试信号注册失败时的KeyboardInterrupt回退机制"""
        with patch("launcher.signal_utils.register_shutdown_handler") as mock_register:
            # 模拟信号注册失败（返回no-op函数）
            mock_register.return_value = lambda: None

            # 启动等待任务
            wait_task = asyncio.create_task(wait_for_shutdown_signal())

            # 等待一小段时间让函数进入等待状态
            await asyncio.sleep(0.01)

            # 模拟KeyboardInterrupt
            wait_task.cancel()

            # 等待任务完成（应该通过KeyboardInterrupt处理）
            with contextlib.suppress(asyncio.CancelledError):
                # 这是预期的，因为我们取消了任务
                await wait_task

    @pytest.mark.asyncio
    async def test_wait_for_shutdown_signal_cleanup_exception_handling(self):
        """测试cleanup过程中异常的处理"""
        with patch("launcher.signal_utils.register_shutdown_handler") as mock_register:
            mock_cleanup = Mock(side_effect=Exception("Cleanup failed"))
            mock_register.return_value = mock_cleanup
            captured_callback = None

            def capture_callback(callback):
                nonlocal captured_callback
                captured_callback = callback
                return mock_cleanup

            mock_register.side_effect = capture_callback

            wait_task = asyncio.create_task(wait_for_shutdown_signal())

            # 等待register被调用
            await asyncio.sleep(0.01)
            assert captured_callback is not None

            # 触发回调来完成等待
            await captured_callback()

            # 等待任务完成
            try:
                await asyncio.wait_for(wait_task, timeout=1.0)
            except TimeoutError:
                wait_task.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await wait_task

            # 验证cleanup被调用（即使失败了也应该被调用）
            mock_cleanup.assert_called_once()

    @pytest.mark.asyncio
    async def test_unified_signal_handling_sigterm(self):
        """测试SIGTERM信号的统一处理"""
        with patch("launcher.signal_utils.register_shutdown_handler") as mock_register:
            mock_cleanup = Mock()
            captured_callback = None

            def capture_callback(callback):
                nonlocal captured_callback
                captured_callback = callback
                return mock_cleanup

            mock_register.side_effect = capture_callback

            wait_task = asyncio.create_task(wait_for_shutdown_signal())

            # 等待register被调用
            await asyncio.sleep(0.01)
            assert captured_callback is not None

            # 模拟SIGTERM信号触发回调
            await captured_callback()

            # 等待任务完成
            try:
                await asyncio.wait_for(wait_task, timeout=1.0)
            except TimeoutError:
                wait_task.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await wait_task

            # 验证信号处理完成
            mock_cleanup.assert_called_once()

    @pytest.mark.asyncio
    async def test_signal_handler_cleanup_on_both_signals(self):
        """测试SIGINT和SIGTERM的cleanup处理"""
        mock_loop = Mock()
        mock_callback = AsyncMock()

        with (
            patch("launcher.signal_utils.os.name", "posix"),
            patch("launcher.signal_utils.asyncio.get_running_loop", return_value=mock_loop),
        ):
            cleanup = register_shutdown_handler(mock_callback)

            # 执行cleanup
            cleanup()

            # 验证两个信号都被清理
            assert mock_loop.remove_signal_handler.call_count == 2

            # 检查清理的信号类型
            cleanup_args = [call.args[0] for call in mock_loop.remove_signal_handler.call_args_list]
            assert signal.SIGINT in cleanup_args
            assert signal.SIGTERM in cleanup_args
