"""Low-write diagnostics that survive MatrixPortal resets."""

import time

import microcontroller
import supervisor

LOG_PATH = "/muni-diagnostics.log"


def _name(value):
    """Return a compact enum name without depending on enum formatting."""
    text = str(value)
    return text.rsplit(".", 1)[-1]


def _context():
    try:
        reset = _name(microcontroller.cpu.reset_reason)
    except Exception:
        reset = "UNAVAILABLE"
    try:
        run = _name(supervisor.runtime.run_reason)
    except Exception:
        run = "UNAVAILABLE"
    return reset, run


def _line(event, details):
    reset, run = _context()
    fields = [
        "t=" + str(int(time.monotonic())),
        "event=" + event,
        "reset=" + reset,
        "run=" + run,
    ]
    for key, value in details.items():
        fields.append(str(key) + "=" + str(value))
    return " ".join(fields) + "\n"


def record(event, **details):
    """Append one redacted diagnostic record; never take down the app."""
    line = _line(event, details)
    try:
        with open(LOG_PATH, "a") as log:
            log.write(line)
    except Exception as error:
        print("Diagnostics write failed: " + type(error).__name__)
    return line.rstrip()


def boot():
    """Persist and print the reset cause at the start of every run."""
    line = record("boot")
    print("MUNI " + line)
