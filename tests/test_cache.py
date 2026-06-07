"""OpenRouter request building."""
from __future__ import annotations

import unittest

from wire0.cache import build_request, cache_stats


class CacheTests(unittest.TestCase):
    def test_build_request_has_tools_and_stream(self) -> None:
        body = build_request("test/model", "system", "workspace", [], [], "sess-1")
        self.assertEqual(body["model"], "test/model")
        self.assertTrue(body["stream"])
        self.assertTrue(body["parallel_tool_calls"])
        self.assertEqual(body["session_id"], "sess-1")
        self.assertEqual(body["messages"][0]["role"], "system")

    def test_cache_stats_empty(self) -> None:
        stats = cache_stats(None)
        self.assertEqual(stats, {"prompt": 0, "cached": 0, "written": 0})

    def test_cache_stats_from_usage(self) -> None:
        usage = {
            "prompt_tokens": 1000,
            "prompt_tokens_details": {"cached_tokens": 400, "cache_write_tokens": 50},
        }
        stats = cache_stats(usage)
        self.assertEqual(stats["prompt"], 1000)
        self.assertEqual(stats["cached"], 400)
        self.assertEqual(stats["written"], 50)


if __name__ == "__main__":
    unittest.main()
