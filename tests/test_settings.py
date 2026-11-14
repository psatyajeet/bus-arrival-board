import os
import tempfile
import tomllib
import unittest
from pathlib import Path
from unittest.mock import patch

from muni_board.settings import SettingsError, load_settings


class SettingsTests(unittest.TestCase):
    def test_loads_gitignored_env_file(self):
        with tempfile.TemporaryDirectory() as directory:
            env_file = Path(directory) / ".env"
            template = Path(".env.example").read_text(encoding="utf-8")
            env_file.write_text(
                template.replace("TRANSIT_511_TOKEN=", "TRANSIT_511_TOKEN='local-token'")
                .replace("BOARD_POLL_SECONDS=150", "BOARD_POLL_SECONDS=180")
                .replace("BOARD_ROW1_STOP=", "BOARD_ROW1_STOP=90001")
                .replace("BOARD_ROW2_STOP=", "BOARD_ROW2_STOP=stop:90002"),
                encoding="utf-8",
            )
            with patch.dict(os.environ, {}, clear=True):
                settings = load_settings(env_file)

        self.assertEqual("local-token", settings["token"])
        self.assertEqual(180, settings["poll_seconds"])
        self.assertEqual(["90001", "stop:90002"], [stop["stop_code"] for stop in settings["stops"]])

    def test_rejects_rate_limit_unsafe_interval(self):
        with tempfile.TemporaryDirectory() as directory:
            env_file = Path(directory) / ".env"
            env_file.write_text(
                "TRANSIT_511_TOKEN=local-token\nBOARD_POLL_SECONDS=75\n",
                encoding="utf-8",
            )
            with patch.dict(os.environ, {}, clear=True):
                with self.assertRaisesRegex(SettingsError, "at least 150"):
                    load_settings(env_file)

    def test_laptop_and_device_examples_use_the_same_board_settings(self):
        from device.board_config import load_board_config

        with patch.dict(os.environ, {}, clear=True):
            from muni_board.settings import load_env_file

            load_env_file(".env.example")
            os.environ.update(BOARD_ROW1_STOP="90001", BOARD_ROW2_STOP="90002")
            laptop = load_board_config(os.environ.get)
        device = tomllib.loads(Path("device/settings.toml.example").read_text(encoding="utf-8"))
        device.update(BOARD_ROW1_STOP="90001", BOARD_ROW2_STOP="90002")
        self.assertEqual(laptop, load_board_config(device.get))


if __name__ == "__main__":
    unittest.main()
