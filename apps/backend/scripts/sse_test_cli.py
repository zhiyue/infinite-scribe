#!/usr/bin/env python3
"""
SSE Testing CLI Tool

一个简单的命令行工具，用于测试前端 SSE 功能。
直接通过 Redis 发送 SSE 事件给指定用户，无需认证流程。

Usage:
    # 发送测试消息给用户 1
    python sse_test_cli.py send --user-id 1 --event-type "test.message" --data '{"message": "Hello World"}'

    # 运行演示模式，发送多个测试事件
    python sse_test_cli.py demo --user-id 1

    # 检查 Redis 中的用户事件历史
    python sse_test_cli.py history --user-id 1 --limit 5
"""

import argparse
import asyncio
import json
import logging
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

# Add the backend source to Python path
backend_src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(backend_src_path))

from src.db.redis import RedisService, redis_service
from src.schemas.sse import EventScope, create_sse_message
from src.services.sse import RedisSSEService

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


class SSETestClient:
    """简化的 SSE 测试客户端，直接通过 Redis 发送事件。"""

    def __init__(self):
        self.redis_service: RedisService | None = None
        self.sse_service: RedisSSEService | None = None

    async def __aenter__(self):
        """异步上下文管理器入口。"""
        # 初始化 Redis 服务
        self.redis_service = redis_service
        await self.redis_service.connect()

        # 初始化 SSE 服务
        self.sse_service = RedisSSEService(self.redis_service)
        await self.sse_service.init_pubsub_client()

        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口。"""
        if self.sse_service:
            await self.sse_service.close()
        if self.redis_service:
            await self.redis_service.disconnect()

    async def send_event(
        self,
        user_id: str,
        event_type: str,
        data: dict[str, Any],
        scope: EventScope = EventScope.USER,
    ) -> str:
        """发送 SSE 事件给指定用户。"""
        if not self.sse_service:
            raise RuntimeError("SSE service not initialized")

        # 创建 SSE 消息
        sse_message = create_sse_message(event_type=event_type, data=data, scope=scope)

        # 发布事件
        stream_id = await self.sse_service.publish_event(user_id, sse_message)

        logger.info(f"✅ 已发送事件 {event_type} 给用户 {user_id}, stream_id: {stream_id}")
        return stream_id

    async def get_user_events_history(self, user_id: str, limit: int = 10) -> list:
        """获取用户的 SSE 事件历史。"""
        if not self.sse_service:
            raise RuntimeError("SSE service not initialized")

        events = await self.sse_service.get_recent_events(user_id, since_id="-")
        return events[-limit:] if len(events) > limit else events


async def cmd_send(args):
    """发送测试 SSE 事件。"""
    try:
        data = json.loads(args.data)
    except json.JSONDecodeError as e:
        logger.error(f"❌ 无效的 JSON 数据: {e}")
        return

    scope = EventScope(args.scope) if args.scope else EventScope.USER

    async with SSETestClient() as client:
        stream_id = await client.send_event(user_id=args.user_id, event_type=args.event_type, data=data, scope=scope)

        print("✅ 事件发送成功!")
        print(f"   用户 ID: {args.user_id}")
        print(f"   事件类型: {args.event_type}")
        print(f"   流 ID: {stream_id}")
        print(f"   数据: {json.dumps(data, indent=2, ensure_ascii=False)}")


async def cmd_demo(args):
    """运行演示模式，发送多个测试事件。"""
    test_events = [
        {
            "event_type": "system.notification-sent",
            "data": {
                "level": "info",
                "title": "欢迎使用!",
                "message": "SSE 测试工具运行正常",
                "action_required": False,
            },
        },
        {
            "event_type": "task.progress-updated",
            "data": {
                "task_id": "demo-task-123",
                "progress": 25,
                "message": "正在处理你的请求...",
                "estimated_remaining": 15,
            },
        },
        {
            "event_type": "task.progress-updated",
            "data": {
                "task_id": "demo-task-123",
                "progress": 75,
                "message": "即将完成...",
                "estimated_remaining": 5,
            },
        },
        {
            "event_type": "task.status-changed",
            "data": {
                "task_id": "demo-task-123",
                "old_status": "running",
                "new_status": "completed",
                "timestamp": datetime.now(UTC).isoformat(),
                "reason": "任务已成功完成!",
            },
        },
        {
            "event_type": "novel.created",
            "data": {
                "id": "novel-demo-456",
                "title": "AI 编年史",
                "theme": "科幻",
                "status": "draft",
                "created_at": datetime.now(UTC).isoformat(),
            },
        },
    ]

    async with SSETestClient() as client:
        print(f"🎭 正在为用户 {args.user_id} 运行 SSE 演示")
        print(f"📤 将发送 {len(test_events)} 个测试事件，间隔 {args.interval} 秒...")

        for i, event in enumerate(test_events, 1):
            print(f"\n📨 [{i}/{len(test_events)}] 发送: {event['event_type']}")

            stream_id = await client.send_event(
                user_id=args.user_id, event_type=event["event_type"], data=event["data"]
            )

            print(f"   ✅ 已发送 (stream_id: {stream_id})")

            if i < len(test_events):  # 最后一个事件不等待
                print(f"   ⏱️  等待 {args.interval} 秒...")
                await asyncio.sleep(args.interval)

        print(f"\n🎉 演示完成! 已向用户 {args.user_id} 发送 {len(test_events)} 个事件")
        print("💡 请检查前端是否收到这些事件")


async def cmd_history(args):
    """查看用户的 SSE 事件历史。"""
    async with SSETestClient() as client:
        events = await client.get_user_events_history(args.user_id, args.limit)

        if not events:
            print(f"📭 用户 {args.user_id} 暂无 SSE 事件历史")
            return

        print(f"📚 用户 {args.user_id} 的最近 {len(events)} 个 SSE 事件:")
        print()

        for i, event in enumerate(events, 1):
            print(f"[{i}] ID: {event.id}")
            print(f"    事件: {event.event}")
            print(f"    作用域: {event.scope.value}")
            print(f"    数据: {json.dumps(event.data, indent=6, ensure_ascii=False)}")
            print()


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="SSE Testing CLI Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    # Global options
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Send command
    send_parser = subparsers.add_parser("send", help="发送单个测试 SSE 事件")
    send_parser.add_argument("--user-id", required=True, help="目标用户 ID")
    send_parser.add_argument("--event-type", required=True, help="事件类型 (例如: 'test.message')")
    send_parser.add_argument("--data", required=True, help="事件数据 (JSON 字符串)")
    send_parser.add_argument(
        "--scope",
        choices=["user", "session", "novel", "global"],
        default="user",
        help="事件作用域",
    )

    # Demo command
    demo_parser = subparsers.add_parser("demo", help="运行演示模式，发送多个测试事件")
    demo_parser.add_argument("--user-id", required=True, help="目标用户 ID")
    demo_parser.add_argument(
        "--interval",
        type=int,
        default=2,
        help="事件间隔时间（秒），默认: 2",
    )

    # History command
    history_parser = subparsers.add_parser("history", help="查看用户的 SSE 事件历史")
    history_parser.add_argument("--user-id", required=True, help="用户 ID")
    history_parser.add_argument(
        "--limit",
        type=int,
        default=10,
        help="显示最近的事件数量，默认: 10",
    )

    args = parser.parse_args()

    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)

    if not args.command:
        parser.print_help()
        return

    # Run the appropriate command
    try:
        if args.command == "send":
            asyncio.run(cmd_send(args))
        elif args.command == "demo":
            asyncio.run(cmd_demo(args))
        elif args.command == "history":
            asyncio.run(cmd_history(args))
    except KeyboardInterrupt:
        print("\n👋 操作已取消")
    except Exception as e:
        logger.error(f"❌ 执行失败: {e}")
        if args.debug:
            import traceback

            traceback.print_exc()


if __name__ == "__main__":
    main()
