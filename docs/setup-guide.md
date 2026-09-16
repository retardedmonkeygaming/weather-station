# Setup Guide — wiring, pins, and the first-run wizard

From bare board to running station in three stages: wire, install, wizard.

---

## 1. Hardware wiring (Raspberry Pi)

### 1602A LCD (4-bit mode)

| LCD pin | Connects to | BCM (default) |
|---|---|---|
| VSS (GND) | GND | — |
| VDD (5V) | 5V | — |
| V0 (contrast) | Middle leg of a 10k trim pot between 5V and GND | — |
| RS | GPIO | 21 (env default 22) |
| RW | GND (write-only) | — |
| EN | GPIO | 17 |
| D4 | GPIO | 25 |
| D5 | GPIO | 24 |
| D6 | GPIO | 23 |
| D7 | GPIO | 18 |
| A (backlight +) | 5V via 220Ω | — |
| K (backlight −) | GND | — |

> The defaults in `.env.example` match the classic wiring diagram
> (`LCD_RS=22`); the wizard ships with 21 pre-filled. Either is fine — what
> matters is that the wizard values match your physical wiring.

### DHT11

| DHT11 pin | Connects to |
|---|---|
| VCC | 3.3V |
| DATA | GPIO 4 (default) + 10k pull-up to 3.3V |
| GND | GND |

### Button

One leg to **GPIO 27** (default), other leg to **3.3V** — the code uses
`pull_up=False` with an internal pull-down.

### Buzzer

Positive leg to **GPIO 2** (default), negative to GND.

### Optional: contrast PWM (Guest Mode dimming)

Wire the LCD **V0** through an RC filter (e.g. 4.7kΩ + 1µF) to a spare BCM
pin and set `LCD_CONTRAST_PIN=<bcm>` in `.env`. Without it, Guest Mode dims
via the backlight instead.

---

## 2. Install

```bash
sudo apt update && sudo apt install -y python3-venv espeak
git clone <your-repo> weather-station && cd weather-station
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python main.py
```

---

## 3. The setup wizard, step by step

Open `http://<pi-ip>:8000/` → you are redirected to `/setup`
(sign in `admin` / `admin`).

**Step 1 — LCD Pins.** Six number fields (RS, EN, D4–D7). BCM numbering,
0–27, each must be unique. Server-side validation rejects duplicates with
a per-field error message.

**Step 2 — Sensors & Actuators.** DHT11 data pin, button pin, buzzer pin.

**Step 3 — Discord (optional).** Five fields:

- **Bot token** — from the [Developer Portal](https://discord.com/developers/applications) (see the [Discord Guide](discord-guide.md))
- **Live-update channel ID** — weather cards posted on data change
- **Alarm-reminder channel ID** — daily alarm reminders + the boot status card (falls back to the live channel)
- **Admin role name** — members with this role may use admin commands
- **Weather image URL** — attached to weather-card embeds (auto placeholder if blank)

**Step 4 — Review & Save.** A summary pre block shows exactly what will be
written. Saving:

1. Writes `.env` (pins + Discord keys), updating existing lines in place
2. Mirrors the pin numbers into `config.py` as code defaults
3. Creates any missing project directories
4. Returns a link straight to the dashboard

Then **restart** (`Ctrl+C` → `python main.py`) so the pins take effect.

> **Idempotency guarantee:** run the wizard as many times as you like. The
> same `.env` keys are updated in place — never duplicated — and re-opening
> `/setup` pre-fills every saved value (pins, channels, role, image URL).
> The bot token is write-only: it is never rendered back to the page.

---

## 4. First-boot behavior matrix

| Situation | LCD shows | Web UI |
|---|---|---|
| Fresh install, no `.env` | `Setup Needed! / Visit WebUI!` | `/` → redirects to `/setup` |
| Setup done, DHT11 unplugged | Non-blocking notice, then normal pages; poller keeps probing | Dashboard live; bell shows "DHT11 offline" |
| Setup done, WiFi down | Station runs; outdoor fields show last known values | Bell: "WiFi/API unreachable" |
| Everything healthy | Your pages | Dashboard live |

---

## 5. Verify your install

```bash
curl http://<pi-ip>:8000/api/health        # {"status":"ok",...} (no auth)
curl -u admin:admin http://<pi-ip>:8000/api/data   # live values
```

On the desktop (mock) the LCD mirror on the dashboard always matches the
`[SIMULATED]` backend — handy for verifying renders without hardware.
