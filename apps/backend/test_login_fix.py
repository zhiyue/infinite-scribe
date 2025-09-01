#!/usr/bin/env python3
"""测试登录修复后的响应。"""

import asyncio
import json

import httpx


async def test_login_fix():
    """测试登录修复是否解决了问题。"""
    base_url = "http://localhost:8000"
    test_email = "test_last_login@example.com"
    test_password = "TestPassword123!"

    print("🔍 测试登录修复")
    print("=" * 50)

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            # 测试登录
            print("登录中...")
            login_response = await client.post(
                f"{base_url}/api/v1/auth/login", json={"email": test_email, "password": test_password}
            )

            if login_response.status_code != 200:
                print(f"❌ 登录失败: {login_response.text}")
                return

            login_data = login_response.json()
            print("✅ 登录成功！")

            # 检查响应结构
            user_data = login_data.get("user", {})
            last_login_at = user_data.get("last_login_at")

            print("📋 用户数据结构检查:")
            print(f"   - 包含 user 字段: {'user' in login_data}")
            print(f"   - 包含 access_token: {'access_token' in login_data}")
            print(f"   - 包含 last_login_at: {'last_login_at' in user_data}")
            print(f"   - last_login_at 值: {last_login_at}")

            # 完整的用户数据
            print("\n📄 完整用户数据:")
            print(json.dumps(user_data, indent=2, default=str))

            return True

        except Exception as e:
            print(f"❌ 测试出错: {e}")
            return False


if __name__ == "__main__":
    success = asyncio.run(test_login_fix())
    if success:
        print("\n🎉 测试成功！现在可以尝试前端登录。")
    else:
        print("\n❌ 测试失败，需要进一步调试。")
