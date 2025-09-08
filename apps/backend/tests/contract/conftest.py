# tests/contract/conftest.py  —— pact.v3 版本
import json
import os
import shutil

import pytest
from tests.contract._common.pact_base import (
    PACT_DIR,
    new_pact,
)

# 映射不同 provider 的“客户端构造器”
CLIENT_BUILDERS = {
    "ollama-api": lambda base_url: _build_ollama(base_url),
}


def _build_ollama(base_url: str):
    from src.external.clients.embedding.ollama import OllamaEmbeddingProvider

    return OllamaEmbeddingProvider(
        base_url=base_url,
        model="dengcao/Qwen3-Embedding-0.6B:F16",
    )


@pytest.fixture
def pact(request):
    """
    提供一个 v3 Pact 对象（不并行）。
    用例结束时：写到临时目录，并增量合并进最终 pact 文件（无 _runs/、无会后聚合）。
    """
    mark = request.node.get_closest_marker("pact_pair")
    if not mark:
        pytest.skip("missing @pytest.mark.pact_pair(...) on test")

    consumer = mark.kwargs.get("consumer", "infinite-scribe-backend")
    provider = mark.kwargs["provider"]

    p = new_pact(
        consumer=consumer,
        provider=provider,
        spec=os.getenv("PACT_SPEC", "V4"),  # 可用 V3 或 V4；HTTP 场景直接 V4 即可
        pact_subdir=None,
    )
    try:
        yield p
    finally:
        # v3：写临时文件并合并到最终 pact
        import tempfile
        from pathlib import Path

        tmpdir = tempfile.mkdtemp(prefix="pact_tmp_")
        try:
            p.write_file(tmpdir, overwrite=True)
            tmp = Path(tmpdir)
            candidates = list(tmp.glob("*.json"))
            if candidates:
                new_doc = json.loads(candidates[0].read_text())

                consumer_name = new_doc["consumer"]["name"]
                provider_name = new_doc["provider"]["name"]
                final_path = PACT_DIR / f"{consumer_name}-{provider_name}.json"

                def _state_key(inter: dict):
                    if "providerStates" in inter and isinstance(inter["providerStates"], list):
                        names = [s.get("name", "") for s in inter["providerStates"]]
                        return "|".join(names) if names else None
                    return inter.get("providerState")

                def _has_matchers(io: dict) -> bool:
                    if not isinstance(io, dict):
                        return False
                    if "matchingRules" in io:
                        return True
                    for k in ("body", "contents"):
                        v = io.get(k)
                        if isinstance(v, dict) and "matchingRules" in v:
                            return True
                    return False

                def _choose(a: dict | None, b: dict | None) -> dict | None:
                    if a is None:
                        return b
                    if b is None:
                        return a
                    a_m = _has_matchers(a.get("request", {})) or _has_matchers(a.get("response", {}))
                    b_m = _has_matchers(b.get("request", {})) or _has_matchers(b.get("response", {}))
                    if b_m and not a_m:
                        return b
                    return a

                if final_path.exists():
                    acc = json.loads(final_path.read_text())
                else:
                    acc = {
                        "consumer": new_doc["consumer"],
                        "provider": new_doc["provider"],
                        "interactions": [],
                        "metadata": new_doc.get("metadata", {"pactSpecification": {"version": "4.0"}}),
                    }

                index = {
                    (i.get("description", ""), _state_key(i)): idx for idx, i in enumerate(acc.get("interactions", []))
                }
                for inter in new_doc.get("interactions", []):
                    key = (inter.get("description", ""), _state_key(inter))
                    if key in index:
                        prev = acc["interactions"][index[key]]
                        acc["interactions"][index[key]] = _choose(prev, inter)
                    else:
                        acc["interactions"].append(inter)
                        index[key] = len(acc["interactions"]) - 1

                final_path.parent.mkdir(parents=True, exist_ok=True)
                final_path.write_text(json.dumps(acc, ensure_ascii=False, indent=2))
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)


@pytest.fixture
def external_client_builder(request):
    """返回 builder(base_url)->client 的工厂，测试在 pact.serve() 后调用。"""
    mark = request.node.get_closest_marker("pact_pair")
    if not mark:
        pytest.skip("missing @pytest.mark.pact_pair(...) on test")
    provider = mark.kwargs["provider"]
    builder = CLIENT_BUILDERS[provider]
    return builder
