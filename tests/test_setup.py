"""Exercise the documented laptop configuration and firmware wiring with synthetic feeds."""

import importlib.util
import io
import json
import os
import sys
import tomllib
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from tempfile import TemporaryDirectory
from types import ModuleType, SimpleNamespace
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit

from muni_board.api import parse_511_time
from muni_board.cli import main
from tools import setup

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests/fixtures/stop_monitoring.json"
NOW = parse_511_time("2025-01-02T00:00:00Z")


class SetupTests(unittest.TestCase):
    def setUp(self):
        self.env = tomllib.loads((ROOT / "device/settings.toml.example").read_text())
        self.env.update(
            TRANSIT_511_TOKEN="test+token",
            BOARD_ROW1_AGENCY="AA",
            BOARD_ROW1_STOP="A:100",
            BOARD_ROW1_LABEL="NB",
            BOARD_ROW2_AGENCY="BB",
            BOARD_ROW2_STOP="B:200",
            BOARD_ROW2_ROUTE="77",
            BOARD_ROW2_LABEL="SB",
        )
        self.payload = json.loads(FIXTURE.read_text())
        self.received = []

    def respond(self, request):
        query = {key: values[0] for key, values in parse_qs(urlsplit(request).query).items()}
        self.assertEqual("test+token", query["api_key"])
        self.received.append((query["agency"], query["stopCode"]))
        return self.payload

    def test_new_user_can_pick_routes_and_generate_device_settings(self):
        from test_api import FakeResponse

        def urlopen(request, timeout):
            return FakeResponse(json.dumps(self.respond(request.full_url)).encode())

        with TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "device").mkdir()
            with (
                patch.object(setup, "PROJECT_ROOT", root),
                patch.dict(os.environ, {}, clear=True),
                patch("muni_board.api.urlopen", side_effect=urlopen),
                patch("tools.setup.time.time", return_value=NOW),
                redirect_stdout(io.StringIO()) as output,
            ):
                with (
                    patch("tools.setup.getpass", return_value="test+token"),
                    patch(
                        "builtins.input", side_effect=["AA", "A:100", "9", "1", "BB", "B:200", "2"]
                    ),
                ):
                    self.assertEqual(0, setup.main([]))

                with (
                    patch("tools.setup.getpass", return_value='local "Wi-Fi" password'),
                    patch("builtins.input", return_value="Home Wi-Fi"),
                ):
                    self.assertEqual(0, setup.main(["--board"]))

                with patch("builtins.input", return_value="n"):
                    self.assertEqual(0, setup.main([]))

            config = tomllib.loads((root / "device/settings.toml").read_text(encoding="utf-8"))
            self.assertEqual("38", config["BOARD_ROW1_ROUTE"])
            self.assertEqual("77", config["BOARD_ROW2_ROUTE"])
            self.assertEqual("B:200", config["BOARD_ROW2_STOP"])
            self.assertEqual(150, config["BOARD_POLL_SECONDS"])
            self.assertEqual("test+token", config["TRANSIT_511_TOKEN"])
            self.assertEqual('local "Wi-Fi" password', config["CIRCUITPY_WIFI_PASSWORD"])
            self.assertEqual([("AA", "A:100"), ("BB", "B:200")], self.received)
            self.assertIn("4 min to Library", output.getvalue())
            self.assertIn("2 min to Market", output.getvalue())
            self.assertNotIn("test+token", output.getvalue())
            self.assertNotIn('local "Wi-Fi" password', output.getvalue())

    def test_laptop_cli_uses_both_configured_agencies_stops_and_routes(self):
        from test_api import FakeResponse

        def urlopen(request, timeout):
            return FakeResponse(json.dumps(self.respond(request.full_url)).encode())

        env = {key: str(value) for key, value in self.env.items()}
        with (
            patch.dict(os.environ, env, clear=True),
            patch("muni_board.api.urlopen", side_effect=urlopen),
            patch("muni_board.cli.time.time", return_value=NOW),
            redirect_stdout(io.StringIO()) as output,
        ):
            self.assertEqual(0, main(["--json"]))

        directions = json.loads(output.getvalue())["directions"]
        self.assertEqual([("AA", "A:100"), ("BB", "B:200")], self.received)
        self.assertEqual(
            [4, 12],
            [int((arrival["eta_epoch"] - NOW) / 60) for arrival in directions["row1"]["arrivals"]],
        )
        self.assertEqual("SB", directions["row2"]["label"])
        self.assertEqual("77", directions["row2"]["arrivals"][0]["route"])

    def test_firmware_requests_rows_and_renders_cached_countdowns(self):
        modules = {
            name: ModuleType(name)
            for name in (
                "adafruit_connection_manager",
                "adafruit_requests",
                "board",
                "busio",
                "displayio",
                "framebufferio",
                "fontio",
                "microcontroller",
                "rgbmatrix",
                "terminalio",
                "adafruit_display_text.label",
                "adafruit_esp32spi",
                "digitalio",
                "watchdog",
                "diagnostics",
            )
        }
        for module, member in (
            ("fontio", "Glyph"),
            ("adafruit_display_text.label", "Label"),
            ("adafruit_esp32spi", "adafruit_esp32spi"),
            ("digitalio", "DigitalInOut"),
            ("watchdog", "WatchDogMode"),
            ("diagnostics", "boot"),
            ("diagnostics", "record"),
        ):
            setattr(modules[module], member, object())
        spec = importlib.util.spec_from_file_location("firmware", ROOT / "device/code.py")
        firmware = importlib.util.module_from_spec(spec)
        with (
            patch.dict(sys.modules, modules),
            patch.object(sys, "path", [str(ROOT / "device"), *sys.path]),
        ):
            spec.loader.exec_module(firmware)

        class Session:
            def get(session, url, **kwargs):
                payload = self.respond(url)
                return SimpleNamespace(status_code=200, json=lambda: payload, close=lambda: None)

        config = firmware.load_board_config(self.env.get)
        with redirect_stdout(io.StringIO()):
            cache = {
                row["key"]: firmware.fetch_stop(Session(), self.env["TRANSIT_511_TOKEN"], row)
                for row in config["stops"]
            }
        self.assertEqual([("AA", "A:100"), ("BB", "B:200")], self.received)
        with patch.object(firmware, "show") as show:
            firmware.render(config, cache, {"row1": 0, "row2": 0}, 65, False)
            show.assert_called_once_with(("2:55", "10"), ("DUE", ""), title="BUS")
            show.reset_mock()
            firmware.render(config, cache, {"row1": 0, "row2": None}, 65, True)
            show.assert_called_once_with(("2:55", "10"), ("NO DATA", ""), title="API ERR")

        self.payload["Siri"]["ServiceDelivery"]["Status"] = "false"
        with redirect_stdout(io.StringIO()), self.assertRaisesRegex(ValueError, "rejected"):
            firmware.fetch_stop(Session(), self.env["TRANSIT_511_TOKEN"], config["stops"][0])


if __name__ == "__main__":
    unittest.main()
