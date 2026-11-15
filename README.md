# Transit Glow

A Wi-Fi connected 64×32 LED display for two Bay Area transit stops or routes,
powered by an Adafruit MatrixPortal M4 and the 511 SF Bay Stop Monitoring API.

![Render of the LED matrix showing eastbound and westbound route 38 countdowns](docs/board-preview.png)

Firmware layout rendered with sample arrivals. The first number in each row is
the next arrival in minutes and seconds. The second is the following arrival
in whole minutes. `DUE` means less than a minute.

## Start here

You can try your own stops on a computer before buying the LED panel. Transit
Glow uses 511 SF Bay, so start with two Bay Area stops.

### Get your 511 token and stop IDs

1. Request a free 511 token. It works like a password for your requests. Agree
   to the terms on 511’s form and follow the email instructions.
   [Request a 511 token](https://511.org/open-data/token)
2. For each stop, choose the agency, route, direction, and stop in the lookup
   tool. Write down the number in the **Stop ID** box. Check the direction if
   your two stops share an intersection. [Look up a stop ID](https://511.org/travel/transit/stop-id)
3. For San Francisco Muni, the agency code is `SF`. For another agency, get
   its code from 511’s operator list. [511 agency lookup](https://511.org/open-data/faqs#where-do-i-find-transit-operator-ids)

### Try it on your computer

1. Install Python 3.11 or newer. On Windows, choose **Add Python to PATH** if
   the installer offers it. [Download Python](https://www.python.org/downloads/)
2. On the GitHub project page, choose **Code → Download ZIP** and unzip it.
3. Open a terminal in the unzipped folder. On a Mac, open Terminal, type
   `cd ` with a space, drag the folder into the window, and press Return.
   On Windows, open the folder in File Explorer, click the address bar, type
   `powershell`, and press Enter.
4. Run the setup command. On Windows, use `py -3 tools/setup.py`.

   ```sh
   python3 tools/setup.py
   ```

Paste your 511 token when the script asks. The terminal will keep it hidden
as you type. For each of your two rows, enter the stop ID and pick a route
from the list 511 returns. The script saves your choices and shows the next
arrivals. Compare those with your transit app during service. Use
`python3 -m muni_board` for another one-time check, or
`py -3 -m muni_board` on Windows.

If 511 has no route list, enter the route from your transit map and check
again during service. If the script shows a request error, check the token,
agency code, and stop ID. Rerun setup to correct a choice. It asks before
replacing your existing settings.

### Buy the parts

Get the **Adafruit Matrix Portal Starter Kit #4812**, a USB-C cable that
carries data, and a stand or mount. The kit includes the **MatrixPortal M4**,
64×32 LED panel, diffuser, and power supply. [Shopping checklist](SHOPPING_CHECKLIST.md)

## Set up the display

1. With power disconnected, attach the M4 to the panel’s HUB75 input and
   connect panel power as shown in [Adafruit’s assembly guide](https://learn.adafruit.com/adafruit-matrixportal-m4/prep-the-matrixportal).
   Check the stock demo when the panel first powers on.
2. Connect through a USB-C data cable. Double-press reset and copy the
   [MatrixPortal M4 CircuitPython UF2](https://circuitpython.org/board/matrixportal_m4/)
   onto `MATRIXBOOT`. The original build used CircuitPython 10.2.1.
   The drive should reappear as `CIRCUITPY`.
3. Download Adafruit’s [CircuitPython library bundle](https://circuitpython.org/libraries)
   matching your CircuitPython major version. Copy these files and folders from
   the bundle’s `lib/` into `CIRCUITPY/lib/`:

   - `adafruit_bitmap_font/`
   - `adafruit_bus_device/`
   - `adafruit_display_text/`
   - `adafruit_esp32spi/`
   - `adafruit_connection_manager.mpy`
   - `adafruit_requests.mpy`
   - `adafruit_ticks.mpy`

4. Run `python3 tools/setup.py --board` from the same folder
   (`py -3 tools/setup.py --board` on Windows). Enter your 2.4 GHz Wi-Fi
   network name and password in the terminal. The script reuses your saved
   stops and token. Drag the resulting `device/settings.toml` onto the root
   of the `CIRCUITPY` drive. Keep this file private.
5. Copy `device/board_config.py`, `device/board_layout.py`,
   `device/diagnostics.py`, and `device/muni_logic.py` into the root of
   `CIRCUITPY`. Copy `device/code.py` there last. It runs automatically.
6. Follow the [bench checklist](BUILD_CHECKLIST.md) to verify arrivals,
   Wi-Fi recovery, and standalone power before mounting it.

If the screen says `SETUP`, the USB serial console names the missing or
invalid setting. For `CONNECT` or `WIFI!`, check the 2.4 GHz network and
[AirLift firmware instructions](https://learn.adafruit.com/adafruit-matrixportal-m4/updating-esp32-firmware).
`API ERR` indicates a failed refresh. `STALE` marks aged cached data and
`NO DATA` appears when the cache has expired or a row has yet to load.
On macOS or Linux, `python3 tools/capture_serial.py --device YOUR_SERIAL_PORT`
records USB logs in `var/serial.log`.

## Get help from ChatGPT or Claude

Copy this prompt into a new chat. If the assistant cannot open GitHub, upload
this README to the chat.

> Help me set up Transit Glow using https://github.com/psatyajeet/transit-glow.
> I’m new to this. Start by asking me what computer I use and which two transit
> stops or public intersections, routes, and directions I want on the display.
> Give me one step at a time, with the exact buttons to click or command to run.
> Use the project’s setup script to check arrivals on my computer before we
> shop. If you can’t verify a stop ID, walk me through the official 511 lookup.
> Ask me what I see after each step. I’ll enter my 511 token and Wi-Fi
> password in my own terminal. Never ask me to paste either into chat.

<details>
<summary>Manual setup, troubleshooting, and polling limits</summary>

Copy `.env.example` to `.env` and fill in the token, agency codes, stop IDs,
and routes. Match route IDs to the case-sensitive `LineRef` returned by 511.
Row labels support up to four letters, digits, spaces, or hyphens. The header
has a two-character badge and an eight-character title. The device template
is available at `device/settings.toml.example`.

For troubleshooting, `python3 -m muni_board --save-raw var/511` saves the
responses locally as `row1.json` and `row2.json`. Look for
`MonitoredVehicleJourney.LineRef`, `DirectionRef`, and `DestinationName`.
Use `--matrix` for a text preview, `--json` for the board model, or
`--watch` for repeated refreshes. Run
`python3 -m unittest discover -s tests -v` for offline tests.

One display uses two requests every 150 seconds, or about 48 per hour.
The default limit is 60 per hour per token. Stop any laptop watch loop
before starting a board on the same token. If 511 has approved an increased
quota, set `BOARD_POLL_SECONDS` as low as 30 in `.env` before generating board
settings. At 30 seconds, two stops use about 240 requests per hour. A quota
of 300 per hour leaves room for setup and occasional other calls. For an
already installed board, update `board_config.py` on `CIRCUITPY` before
changing the interval. [511 API limits](https://511.org/open-data/transit)

</details>

[Data provided by 511.org](https://511.org).
The preview uses the [Terminus bitmap font shipped with CircuitPython](https://github.com/adafruit/circuitpython/blob/10.2.1/tools/fonts/ter-u12n.bdf).
