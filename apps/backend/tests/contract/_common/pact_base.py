"""Pact v3 工厂与路径常量。

使用 pact-python v3 (FFI) 顶层 Pact API：`from pact import Pact`。
由测试侧负责 pact.serve() 启动 mock，测试结束后由 fixture 写出 pact 文件。
"""

import os
import socket
from contextlib import closing
from pathlib import Path

from pact import Pact  # v3 顶层 API

BASE = Path(__file__).resolve().parent.parent
PACT_DIR = BASE / "external" / "clients" / "pacts"  # 统一输出目录
LOG_DIR = BASE / "external" / "clients" / "pact_logs"  # v3 不强依赖，但保留目录
PACT_DIR.mkdir(parents=True, exist_ok=True)
LOG_DIR.mkdir(parents=True, exist_ok=True)


def _free_port() -> int:
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as s:
        s.bind(("", 0))
        return s.getsockname()[1]


def new_pact(
    *,
    consumer: str,
    provider: str,
    spec: str = "V4",  # "V3" 或 "V4" 均可；HTTP 场景建议直接 V4
    pact_subdir: str | None = None,
) -> Pact:
    """
    返回已配置好的 v3 Pact 对象（不启动 mock）。
    - 你会在测试里用 `with pact.serve(hostname, port) as srv:` 启动内嵌 mock
    - 测试结束后需调用 pact.write_file(目录) 写 pact 文件
    """
    pact_dir = PACT_DIR
    if pact_subdir:
        pact_dir = PACT_DIR / "_runs" / pact_subdir
        pact_dir.mkdir(parents=True, exist_ok=True)

    # v3：构造 Pact 并设置规范版本
    p = Pact(consumer, provider).with_specification(spec)

    # 给调用方带上"写文件"的目标目录，便于 fixture 统一收尾
    p._pact_output_dir = pact_dir  # type: ignore # 简单附加属性，测试里用
    return p


def free_port_or_env() -> int:
    return int(os.getenv("PACT_PORT", "0")) or _free_port()
