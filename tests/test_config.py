"""Config helpers."""
from __future__ import annotations

import json
import os
import shutil
import unittest
import uuid
from pathlib import Path
from unittest.mock import patch

from wire0.config import (
    DEFAULT_MODEL,
    get_api_key,
    get_model,
    mask_key,
    set_api_key,
    set_model,
)


class ConfigTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(os.environ["TEMP"]) / f"wire0_test_{uuid.uuid4().hex}"
        self.tmp.mkdir(parents=True, exist_ok=True)
        self.config_file = self.tmp / "config.json"
        self.patches = [
            patch("wire0.config.CONFIG_DIR", self.tmp),
            patch("wire0.config.CONFIG_FILE", self.config_file),
            patch("wire0.config.LEGACY_FILE", self.tmp / "legacy.json"),
        ]
        for p in self.patches:
            p.start()
        os.environ.pop("OPENROUTER_API_KEY", None)
        os.environ.pop("WIRE0_MODEL", None)

    def tearDown(self) -> None:
        for p in self.patches:
            p.stop()
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_default_model(self) -> None:
        self.assertEqual(get_model(), DEFAULT_MODEL)

    def test_set_and_get_model(self) -> None:
        set_model("anthropic/claude-sonnet-4")
        self.assertEqual(get_model(), "anthropic/claude-sonnet-4")
        data = json.loads(self.config_file.read_text(encoding="utf-8"))
        self.assertEqual(data["model"], "anthropic/claude-sonnet-4")

    def test_set_and_get_api_key(self) -> None:
        set_api_key("sk-or-test-key-12345678")
        self.assertEqual(get_api_key(), "sk-or-test-key-12345678")

    def test_mask_key(self) -> None:
        self.assertEqual(mask_key("sk-or-test-key-12345678"), "sk-o…5678")

    def test_legacy_migration(self) -> None:
        legacy = self.tmp / "legacy.json"
        legacy.write_text(
            json.dumps({"openrouter_api_key": "sk-or-legacy", "model": "test/model"}),
            encoding="utf-8",
        )
        with patch("wire0.config.LEGACY_FILE", legacy):
            from wire0.config import _migrate_legacy

            _migrate_legacy()
        self.assertTrue(self.config_file.exists())
        self.assertEqual(get_api_key(), "sk-or-legacy")
        self.assertEqual(get_model(), "test/model")


if __name__ == "__main__":
    unittest.main()
