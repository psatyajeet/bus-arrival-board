"""Configure the laptop preview and optionally fetch arrivals from 511."""

import os
import sys
import warnings
from getpass import GetPassWarning, getpass
from pathlib import Path
from tempfile import NamedTemporaryFile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from device.board_config import SettingsError, load_board_config
from muni_board.api import ApiError
from muni_board.cli import fetch_cycle
from muni_board.render import render_human
from muni_board.settings import PROJECT_ROOT


def prompt(label, default=""):
    suffix = f" [{default}]" if default else ""
    while True:
        value = input(f"{label}{suffix}: ").strip() or default
        if value:
            return value
        print("Enter a value to continue.")


def confirm(label):
    return input(f"{label} [y/N] ").strip().lower() in ("y", "yes")


def write_env(path, values, replace):
    with NamedTemporaryFile(
        mode="w", encoding="utf-8", dir=path.parent, prefix=".env-", delete=False
    ) as temp:
        temp_path = Path(temp.name)
        try:
            for key, value in values.items():
                temp.write(f'{key}="{value}"\n')
            temp.close()
            if replace:
                os.replace(temp_path, path)
            else:
                os.link(temp_path, path)
        finally:
            temp_path.unlink(missing_ok=True)


def main():
    path = PROJECT_ROOT / ".env"
    replace = path.exists() or path.is_symlink()
    try:
        if replace and not confirm(".env already exists. Replace it?"):
            print("Kept your existing .env.")
            return 0

        print("Request a 511 token at https://511.org/open-data/token")
        print("Look up your stops at https://511.org/travel/transit/stop-id")
        with warnings.catch_warnings():
            warnings.simplefilter("error", GetPassWarning)
            token = getpass("511 API token (hidden): ").strip()
        if not token:
            raise SettingsError("Enter your 511 API token.")

        values = {"TRANSIT_511_TOKEN": token}
        for number in (1, 2):
            print(f"\nRow {number}")
            prefix = f"BOARD_ROW{number}_"
            values[prefix + "AGENCY"] = prompt("511 agency ID", "SF")
            values[prefix + "STOP"] = prompt("511 stop ID")
            values[prefix + "ROUTE"] = prompt("Route ID (LineRef)")
            values[prefix + "LABEL"] = prompt("Display label (up to 4 characters)", f"ROW{number}")

        route = values["BOARD_ROW1_ROUTE"].upper()
        default_badge = route if len(route) <= 2 and route.isascii() and route.isalnum() else "RT"
        values["BOARD_BADGE"] = prompt("Header badge (up to 2 characters)", default_badge)
        values["BOARD_TITLE"] = prompt("Header title (up to 8 characters)", "BUS")
        values["BOARD_POLL_SECONDS"] = "150"
        settings = load_board_config(values.get)
        write_env(path, values, replace)
        print("Saved .env. Use the same board settings on your MatrixPortal.")

        if confirm("Fetch both stops from 511 now?"):
            settings.update(token=token, timeout_seconds=15)
            board, _, fresh = fetch_cycle(settings)
            print(render_human(board))
            if len(fresh) != len(settings["stops"]):
                return 1

    except GetPassWarning:
        print(
            "Run setup in an interactive terminal to enter your token privately.", file=sys.stderr
        )
        return 2
    except (SettingsError, OSError, ApiError) as error:
        print(f"Setup error: {error}", file=sys.stderr)
        return 1
    except (KeyboardInterrupt, EOFError):
        print("\nSetup canceled.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
