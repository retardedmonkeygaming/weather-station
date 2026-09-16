# Discord Guide — token setup, commands, live updates

The station ships a full Discord bot: weather cards, forecast, page
control, alarm management, live updates, daily reminders, and a boot
status card.

---

## 1. Create the bot token

1. Open the [Discord Developer Portal](https://discord.com/developers/applications)
   → **New Application** → give it a name.
2. **Bot** tab → **Reset Token** → copy the token
   (you will paste it into the setup wizard — it is stored only in your
   local `.env`).
3. **Bot** tab → *Privileged Gateway Intents* → enable
   **MESSAGE CONTENT INTENT**. This powers the "speak the weather" TTS
   listener; without it slash commands still work but the bot logs a clear
   warning and skips the voice feature.
4. **OAuth2 → URL Generator** → check `bot` + `applications.commands` →
   copy the generated URL → open it → invite the bot to your server.

## 2. Configure the station

Either paste the token into the **setup wizard step 3** (also where you can
set the live-update channel, reminder channel, admin role, and weather
image URL), or add to `.env` and restart:

```env
DISCORD_BOT_TOKEN=MTA5...your.token
DISCORD_UPDATE_CHANNEL_ID=123456789012345678      # live weather cards
DISCORD_REMINDER_CHANNEL_ID=123456789012345679    # alarm reminders + boot card (fallback: live channel)
DISCORD_UPDATE_MIN_INTERVAL_S=60                  # rate limit for live cards
DISCORD_ADMIN_ROLE=Station Admin                  # admin commands gate
DISCORD_WEATHER_IMAGE_URL=https://example.com/station.jpg   # optional card image
```

Channel IDs: enable **Developer Mode** in Discord (Settings → Advanced),
then right-click a channel → **Copy Channel ID**.

## 3. Slash commands

| Command | Who | What it does |
|---|---|---|
| `/weather` | everyone | Rich weather card: moon emoji in title, indoor/outdoor temps + humidity, moon phase + illumination, AQI with color accent, comfort + trend, current LCD page, condition image |
| `/forecast` | everyone | Today's min/max with ⬇⬆ arrows, conditions icon, UV now/peak, outdoor humidity; warns when the API is offline |
| `/status` | everyone | Diagnostics: DHT/WiFi/LCD state, current page, uptime, CPU temp/load, RAM, recovering subsystems |
| `/status-embed` | everyone | The all-in-one card: weather + system + hardware in one embed |
| `/setpage page widget` | admin | Assign any widget to any LCD page 1–10; replies with the exact 16-char frame the panel will show |
| `/alarm on hour minute` | admin | Legacy combined alarm setter |
| `/alarm-on hour minute` | admin | Enable the daily alarm |
| `/alarm-off` | admin | Disable the daily alarm |
| `/set-alert high low` | admin | Configure indoor alert thresholds (−40..80 °C, low < high); the DHT poller enforces them |
| `/liveupdate on [channel]` | admin | Toggle the live weather-card feed, optionally retargeting the channel |

**Permissions:** admin commands pass for Discord **Administrators** or
members holding the role named in `DISCORD_ADMIN_ROLE` (case-insensitive).
Everyone else gets a polite ephemeral denial naming the required role.

## 4. Live updates, reminders, and the boot card

- **Live updates** — a background loop watches the data signature (temps,
  humidity, AQI, LCD page, alarm, alert, weather code) and posts the
  weather card to the live channel when it changes, rate-limited to
  `DISCORD_UPDATE_MIN_INTERVAL_S`. **Alarm and temperature-alert
  transitions bypass the rate limit** so warnings are never swallowed.
- **Daily alarm reminder** — when the alarm is ON, a ⏰ reminder embed is
  posted each day at the alarm time to the reminder channel. One post per
  (day, alarm time); editing the alarm re-arms it.
- **Boot status embed** — every time the station starts, the bot posts a
  one-shot 🛰️ "Weather Station Online" card (state, temps, CPU/RAM,
  recovering subsystems) to the reminder channel.

## 5. Voice: "speak the weather"

Type `speak the weather` in any channel the bot can see and it replies with
a Discord-TTS message:

> Indoor temperature is 24.6 degrees celsius, outdoor 31.2 degrees celsius,
> humidity 41%. Air quality index 88.

Your Discord client speaks it aloud (client-side TTS toggle applies).

## 6. Weather images

Every weather-card embed carries an image:

- `DISCORD_WEATHER_IMAGE_URL` when set — e.g. a photo of your station or a
  static sky chart;
- otherwise an auto-generated free placeholder (placehold.co) rendering the
  current condition text on a sky-blue card — zero configuration.

## 7. Troubleshooting

| Symptom | Fix |
|---|---|
| Bot never comes online | Token correct? Restart the station and check the log line `Discord bot online as …` |
| Slash commands missing | Invite with **both** `bot` and `applications.commands` scopes; wait up to a minute for the global sync |
| "speak the weather" ignored | MESSAGE CONTENT INTENT not enabled in the Developer Portal |
| Admin commands denied | Grant the `DISCORD_ADMIN_ROLE` role or make the user an Administrator |
| No live cards | Live channel ID set/valid? Bot can **view + send** in that channel? |
| No reminder/boot card | Set `DISCORD_REMINDER_CHANNEL_ID` (or it falls back to the live channel) |
