"""
discord_bot.py — Discord integration for the weather station.

Slash commands:
    /weather              — rich weather card (moon emoji, formatted temps)
    /forecast             — today's min/max, UV peak, conditions
    /setpage page widget  — assign a widget to an LCD page (admin)
    /alarm on/off hour minute — legacy combined alarm command (admin)
    /alarm-on hour minute — enable the daily alarm (admin)
    /alarm-off            — disable the daily alarm (admin)
    /set-alert high low   — configure indoor alert thresholds (admin)
    /status               — station diagnostics + subsystem health
    /status-embed         — all-in-one rich station card
    /liveupdate on [channel] — toggle live weather-card feed (admin)

Voice support:
    Saying "speak the weather" in any channel the bot can see makes it reply
    with a Discord-TTS spoken summary of current conditions.

Live updates:
    When DISCORD_UPDATE_CHANNEL_ID is set (setup wizard / .env) the bot posts
    a weather card to that channel whenever the data signature changes,
    rate-limited by DISCORD_UPDATE_MIN_INTERVAL_S. Alerts/alarm bypass the
    rate limit so warnings are never swallowed.

Permissions:
    Admin commands require the Discord "Administrator" permission or
    membership in the role named by DISCORD_ADMIN_ROLE (setup wizard / .env).

The bot runs under the same safe_task supervisor as every other subsystem.
If DISCORD_BOT_TOKEN is unset the task exits cleanly (supervisor logs it and
moves on) so desktop development never requires Discord.
"""

from __future__ import annotations

import asyncio
import logging
import time
from datetime import datetime
from typing import Any, Dict, Optional

import config, database
from config import get_state
from services import moon_phase, render
from utils import format_humid, format_temp, safe_float

log = logging.getLogger("weather.discord")

try:
    import discord
    from discord import app_commands
    HAS_DISCORD = True
except ImportError:      # discord.py not installed — feature degrades cleanly
    discord = None
    app_commands = None
    HAS_DISCORD = False


# ---------------------------------------------------------------------------
# Shared formatting helpers
# ---------------------------------------------------------------------------

MOON_EMOJI: Dict[str, str] = {
    "New Moon": "🌑", "Waxing Crescent": "🌒", "First Quarter": "🌓",
    "Waxing Gibbous": "🌔", "Full Moon": "🌕", "Waning Gibbous": "🌖",
    "Last Quarter": "🌗", "Waning Crescent": "🌘",
}

AQI_COLORS: Dict[str, int] = {
    "Good": 0x34D399, "Moderate": 0xFBBF24,
    "Sensitiv": 0xF97316, "Unhealthy": 0xEF4444,
}


def _spoken_temp(value, unit: str) -> str:
    """Human-friendly temperature for TTS ("23.5 degrees")."""
    try:
        t = float(str(value).replace("C", "").replace("F", ""))
        return f"{t:.1f} degrees {('fahrenheit' if unit == 'F' else 'celsius')}"
    except (TypeError, ValueError):
        return "unavailable"


class WeatherBotClient:
    """discord.py client wiring the weather-station slash commands."""

    def __init__(self, token: str) -> None:
        if not HAS_DISCORD:
            raise RuntimeError("discord.py is not installed")
        self.token = token
        intents = discord.Intents.default()
        intents.message_content = True     # "speak the weather" listener
        self.client = discord.Client(intents=intents)
        self.tree = app_commands.CommandTree(self.client)
        self._register_commands()
        self._register_events()

    # ------------------------------------------------------------------
    # Permissions (role-based gate for admin commands)
    # ------------------------------------------------------------------

    def _is_admin(self, interaction) -> bool:
        """Administrator permission OR the configured admin role name."""
        user = interaction.user
        perms = getattr(user, "guild_permissions", None)
        if perms is not None and perms.administrator:
            return True
        role_name = config.DISCORD_ADMIN_ROLE
        if role_name:
            roles = getattr(user, "roles", []) or []
            if any(r.name.lower() == role_name.lower() for r in roles):
                return True
        return False

    async def _deny_admin(self, interaction) -> None:
        role = config.DISCORD_ADMIN_ROLE or "Administrator"
        await interaction.response.send_message(
            embed=self._embed("🔒 Admins only", {
                "Required": f"the **{role}** role or Administrator permission",
            }, color=0xF87171),
            ephemeral=True)

    # ------------------------------------------------------------------
    # Embed builders
    # ------------------------------------------------------------------

    @staticmethod
    def _embed(title: str, fields: Dict[str, str],
               color: int = 0x38BDF8) -> Any:
        embed = discord.Embed(title=title, color=color,
                              timestamp=datetime.now())
        for name, value in fields.items():
            embed.add_field(name=name, value=value, inline=True)
        return embed

    @staticmethod
    def build_weather_card() -> Any:
        """Feature 5: rich weather-card embed with moon emoji + temps."""
        state = get_state()
        unit = state.get_setting("unit")
        phase, _, illum, _ = moon_phase.calculate_moon_phase()
        moon_icon = MOON_EMOJI.get(phase, "🌙")
        comfort = render.get_comfort_level(state.indoor_temp,
                                           state.indoor_humid)
        w_icon, w_text = render.weather_info(state.weather_code)

        color = AQI_COLORS.get(state.aqi_status, 0x38BDF8)
        embed = discord.Embed(
            title=f"{moon_icon} Weather Station",
            description=(
                f"{w_icon} **{w_text}** · feels "
                f"**{format_temp(state.indoor_temp, unit)}** inside"
            ),
            color=color,
            timestamp=datetime.now(),
        )
        embed.add_field(name=f"🌡️ Indoor ({unit})",
                        value=f"**{format_temp(state.indoor_temp, unit)}**\n"
                              f"{format_humid(state.indoor_humid)} humidity",
                        inline=True)
        embed.add_field(name=f"🌍 Outdoor ({unit})",
                        value=f"**{format_temp(state.outdoor_temp, unit)}**\n"
                              f"{format_humid(safe_float(state.outdoor_humid))}"
                              f" humidity",
                        inline=True)
        embed.add_field(name=f"{moon_icon} Moon",
                        value=f"{phase}\n{illum}% illuminated",
                        inline=True)
        embed.add_field(name="🍃 Air Quality",
                        value=f"AQI **{state.aqi_val}** ({state.aqi_status})\n"
                              f"PM2.5 {state.pm2_5_val} · PM10 {state.pm10_val}",
                        inline=True)
        embed.add_field(name="😊 Comfort",
                        value=f"**{comfort}**\nTrend {state.temp_trend_symbol}",
                        inline=True)
        embed.add_field(name="🖥️ LCD",
                        value=f"Page {state.current_page} · "
                              f"{state.page_names.get(state.current_page, '')}",
                        inline=True)
        embed.set_footer(text=f"Raspberry Pi Weather Station v{config.APP_VERSION}")
        return embed

    # ------------------------------------------------------------------
    # Command registration
    # ------------------------------------------------------------------

    def _register_commands(self) -> None:
        @self.tree.command(name="weather",
                           description="Rich weather card with moon emoji")
        async def weather_command(interaction):
            await interaction.response.send_message(
                embed=self.build_weather_card())

        @self.tree.command(name="forecast",
                           description="Today's forecast: min/max, UV, AQI")
        async def forecast_command(interaction):
            await self._cmd_forecast(interaction)

        @self.tree.command(name="setpage",
                           description="Assign a widget to an LCD page (admin)")
        @app_commands.describe(
            page="LCD page number (1-10)",
            widget="Widget to show on that page",
        )
        @app_commands.choices(widget=[
            app_commands.Choice(name=w["title"], value=w["type"])
            for w in render.WIDGET_CATALOG
        ])
        async def setpage_command(interaction, page: int, widget:
                                  app_commands.Choice[str]):
            if not self._is_admin(interaction):
                await self._deny_admin(interaction)
                return
            await self._cmd_setpage(interaction, page, widget.value)

        @self.tree.command(name="alarm",
                           description="Set the daily alarm (admin)")
        @app_commands.describe(
            on="Turn the alarm on or off",
            hour="Hour 0-23 (24h format)",
            minute="Minute 0-59 (step 5 recommended)",
        )
        async def alarm_command(interaction, on: bool, hour: int = 7,
                                minute: int = 0):
            if not self._is_admin(interaction):
                await self._deny_admin(interaction)
                return
            await self._cmd_alarm(interaction, on, hour, minute)

        # Feature 1: explicit on/off commands
        @self.tree.command(name="alarm-on",
                           description="Enable the daily alarm (admin)")
        @app_commands.describe(hour="Hour 0-23", minute="Minute 0-59")
        async def alarm_on_command(interaction, hour: int = 7,
                                   minute: int = 0):
            if not self._is_admin(interaction):
                await self._deny_admin(interaction)
                return
            await self._cmd_alarm(interaction, True, hour, minute)

        @self.tree.command(name="alarm-off",
                           description="Disable the daily alarm (admin)")
        async def alarm_off_command(interaction):
            if not self._is_admin(interaction):
                await self._deny_admin(interaction)
                return
            state = get_state()
            state.set_setting("alarm_on", "OFF")
            await database.save_setting("alarm_on", "OFF")
            state.mark_page_dirty()
            await interaction.response.send_message(
                embed=self._embed("⏰ Alarm disabled", {"State": "OFF"},
                                  color=0x34D399))

        # Feature 1: configurable alert thresholds
        @self.tree.command(name="set-alert",
                           description="Set indoor alert thresholds (admin)")
        @app_commands.describe(
            high="High-temp alert threshold in °C (e.g. 32)",
            low="Low-temp alert threshold in °C (e.g. 10)",
        )
        async def set_alert_command(interaction, high: float, low: float):
            if not self._is_admin(interaction):
                await self._deny_admin(interaction)
                return
            await self._cmd_set_alert(interaction, high, low)

        @self.tree.command(name="status", description="Station diagnostics")
        async def status_command(interaction):
            await self._cmd_status(interaction)

        # Feature 1: all-in-one rich card
        @self.tree.command(name="status-embed",
                           description="All-in-one station card")
        async def status_embed_command(interaction):
            await self._cmd_status_embed(interaction)

        # Feature 3: runtime control of the live-update feed
        @self.tree.command(name="liveupdate",
                           description="Toggle live weather cards (admin)")
        @app_commands.describe(
            on="Enable or disable the live-update feed",
            channel="Optional channel override (defaults to setup channel)",
        )
        async def liveupdate_command(interaction, on: bool,
                                     channel: Optional[str] = None):
            if not self._is_admin(interaction):
                await self._deny_admin(interaction)
                return
            if on and channel:
                if not channel.strip().isdigit():
                    await interaction.response.send_message(
                        embed=self._embed("❌ Invalid channel ID",
                                          {"Rule": "numeric ID only"},
                                          color=0xF87171),
                        ephemeral=True)
                    return
                self.live_channel_id = int(channel.strip())
            elif on and config.DISCORD_UPDATE_CHANNEL_ID:
                self.live_channel_id = config.DISCORD_UPDATE_CHANNEL_ID
            self.live_enabled = on
            target = self.live_channel_id or "(none set)"
            await interaction.response.send_message(
                embed=self._embed("📡 Live updates",
                                  {"State": "ON" if on else "OFF",
                                   "Channel": str(target)},
                                  color=0x34D399),
                ephemeral=True)

    # ------------------------------------------------------------------
    # Events (feature 2: voice "speak the weather")
    # ------------------------------------------------------------------

    def _register_events(self) -> None:
        @self.client.event
        async def on_ready():
            log.info("Discord bot online as %s — syncing slash commands",
                     self.client.user)
            try:
                await self.tree.sync()
                log.info("Discord slash commands synced")
            except Exception:
                log.exception("Discord slash command sync failed")

        @self.client.event
        async def on_message(message):
            if message.author.bot:
                return
            text = (message.content or "").lower()
            if "speak the weather" in text:
                state = get_state()
                unit = state.get_setting("unit")
                spoken = (
                    f"Indoor temperature is {_spoken_temp(state.indoor_temp, unit)}, "
                    f"outdoor {_spoken_temp(state.outdoor_temp, unit)}, "
                    f"humidity {format_humid(state.indoor_humid)}. "
                    f"Air quality index {state.aqi_val}."
                )
                try:
                    await message.reply(spoken, tts=True,
                                        mention_author=False)
                except Exception:
                    log.exception("TTS reply failed")

    # ------------------------------------------------------------------
    # Command handlers
    # ------------------------------------------------------------------

    async def _cmd_forecast(self, interaction) -> None:
        state = get_state()
        unit = state.get_setting("unit")
        w_icon, w_text = render.weather_info(state.weather_code)
        fields = {
            f"Today ({unit})":
                f"⬇ {format_temp(state.outdoor_min, unit)}  "
                f"⬆ {format_temp(state.outdoor_max, unit)}",
            "Conditions": f"{w_icon} {w_text}",
            "UV Index": f"{state.uv_current} now · peak {state.uv_max}",
            "Humidity (outdoor)":
                format_humid(safe_float(state.outdoor_humid)),
        }
        if state.wifi_error:
            fields["⚠️ Note"] = "API offline — showing last known values"
        await interaction.response.send_message(
            embed=self._embed("📅 Forecast", fields,
                              color=0xF87171 if state.wifi_error else 0x38BDF8))

    async def _cmd_setpage(self, interaction, page: int, widget: str) -> None:
        state = get_state()

        if not 1 <= page <= config.MAX_LCD_PAGES:
            await interaction.response.send_message(
                embed=self._embed("❌ Invalid page",
                                  {"Range": f"1..{config.MAX_LCD_PAGES}"},
                                  color=0xF87171),
                ephemeral=True)
            return

        title = next((w["title"] for w in render.WIDGET_CATALOG
                      if w["type"] == widget), widget)
        state.custom_lcd_pages[page] = widget
        if page > state.total_pages:
            state.total_pages = page
        state.mark_page_dirty()
        await database.save_custom_page(page, widget)

        # Mirror what the LCD will now show on that page.
        saved = state.current_page
        state.current_page = page
        frame = render.build_frame(state)
        state.current_page = saved
        lcd_preview = f"{frame[0][:16]}\n{frame[1][:16]}"

        embed = self._embed("✅ LCD page updated", {
            "Page": f"{page} ({state.page_names.get(page, '')})",
            "Widget": title,
            "Line 1": f"`{frame[0][:16] or ' '}`",
            "Line 2": f"`{frame[1][:16] or ' '}`",
        }, color=0x34D399)
        await interaction.response.send_message(embed=embed)

    async def _cmd_alarm(self, interaction, on: bool, hour: int,
                         minute: int) -> None:
        state = get_state()
        if not (0 <= hour <= 23 and 0 <= minute <= 59):
            await interaction.response.send_message(
                embed=self._embed("❌ Invalid time",
                                  {"Rules": "hour 0-23, minute 0-59"},
                                  color=0xF87171),
                ephemeral=True)
            return

        state.set_setting("alarm_on", "ON" if on else "OFF")
        state.set_setting("alarm_hr", hour)
        state.set_setting("alarm_min", minute)
        await database.save_setting("alarm_on", "ON" if on else "OFF")
        await database.save_setting("alarm_hr", hour)
        await database.save_setting("alarm_min", minute)
        state.mark_page_dirty()

        embed = self._embed("⏰ Alarm updated", {
            "State": "ON" if on else "OFF",
            "Time": f"{hour:02d}:{minute:02d}",
        }, color=0x34D399)
        await interaction.response.send_message(embed=embed)

    async def _cmd_set_alert(self, interaction, high: float,
                             low: float) -> None:
        state = get_state()
        if not (-40 <= low < high <= 80):
            await interaction.response.send_message(
                embed=self._embed("❌ Invalid thresholds", {
                    "Rules": "low < high, both within -40..80 °C",
                }, color=0xF87171),
                ephemeral=True)
            return

        state.set_setting("alert_high", high)
        state.set_setting("alert_low", low)
        await database.save_setting("alert_high", high)
        await database.save_setting("alert_low", low)
        config.push_notification(
            "info",
            f"Discord /set-alert: high {high}°C, low {low}°C")

        current = (f"**{format_temp(state.indoor_temp, 'C')}** now"
                   if state.indoor_temp is not None else "no reading yet")
        await interaction.response.send_message(
            embed=self._embed("🚨 Alert thresholds updated", {
                "High": f"{high:.1f} °C",
                "Low": f"{low:.1f} °C",
                "Indoor": current,
            }, color=0x34D399))

    async def _cmd_status(self, interaction) -> None:
        state = get_state()
        lcd = get_lcd_safe()
        subsystems = config.subsystem_status()
        pi = render.get_pi_system_stats()

        uptime_s = int(datetime.now().timestamp() - state.started_at)
        hours, rem = divmod(uptime_s, 3600)
        minutes = rem // 60

        fields = {
            "DHT11 Sensor": "🟢 Online" if not state.dht_error else "🔴 Error",
            "WiFi / API": "🟢 Connected" if not state.wifi_error else "🔴 Down",
            "LCD": "🖥️ Mock (desktop)" if (lcd and lcd.is_mock) else "🖥️ Hardware",
            "Current Page": f"{state.current_page} / {state.total_pages}",
            "Uptime": f"{hours}h {minutes}m",
            "CPU Temp": pi["cpu_temp"],
            "CPU Load": pi["cpu_usage"],
            "RAM Usage": pi["ram_usage"],
        }
        color = 0x34D399 if not subsystems else 0xFBBF24
        if subsystems:
            recovering = "\n".join(
                f"• {name}: {info['error']} ({info['restarts']} restarts)"
                for name, info in subsystems.items()
            )
            fields["⚠️ Recovering"] = recovering

        await interaction.response.send_message(
            embed=self._embed("📡 Station Status", fields, color=color))

    async def _cmd_status_embed(self, interaction) -> None:
        """Feature 1+5: the everything-card — weather + system in one embed."""
        state = get_state()
        lcd = get_lcd_safe()
        subsystems = config.subsystem_status()
        pi = render.get_pi_system_stats()
        uptime_s = int(datetime.now().timestamp() - state.started_at)
        hours, rem = divmod(uptime_s, 3600)
        minutes = rem // 60

        embed = self.build_weather_card()
        embed.title = "📡 Station Overview"
        embed.add_field(name="⚙️ System",
                        value=f"CPU {pi['cpu_temp']} · {pi['cpu_usage']}\n"
                              f"RAM {pi['ram_usage']}\n"
                              f"Uptime {hours}h {minutes}m",
                        inline=True)
        embed.add_field(name="🔌 Hardware",
                        value=("🖥️ Mock" if (lcd and lcd.is_mock)
                               else "🖥️ Hardware") +
                              ("" if not state.dht_error else "\n🔴 DHT11 error") +
                              ("" if not state.wifi_error else "\n🔴 WiFi down"),
                        inline=True)
        if subsystems:
            embed.add_field(
                name="⚠️ Recovering subsystems",
                value="\n".join(f"• {n} ({i['restarts']}x)"
                                for n, i in subsystems.items()),
                inline=False)
        await interaction.response.send_message(embed=embed)

    # ------------------------------------------------------------------
    # Live updates (feature 3)
    # ------------------------------------------------------------------

    live_enabled: bool = bool(config.DISCORD_UPDATE_CHANNEL_ID)
    live_channel_id: Optional[int] = config.DISCORD_UPDATE_CHANNEL_ID
    _last_signature: Optional[tuple] = None
    _last_post_ts: float = 0.0

    def _live_signature(self) -> tuple:
        state = get_state()
        return (state.indoor_temp, state.outdoor_temp, state.indoor_humid,
                state.aqi_val, state.current_page, state.alarm_ringing,
                state.temp_alert_active, state.weather_code)

    async def live_update_tick(self) -> None:
        """One live-update check: post a card when the data changed.

        Urgent transitions (alarm ringing / temp alert active) bypass the
        minimum-interval rate limit so warnings are never swallowed.
        """
        if not self.live_enabled or not self.live_channel_id:
            return
        sig = self._live_signature()
        if sig == self._last_signature:
            return

        state = get_state()
        urgent = state.alarm_ringing or state.temp_alert_active
        now = time.time()
        if (not urgent
                and now - self._last_post_ts
                < config.DISCORD_UPDATE_MIN_INTERVAL_S):
            return

        channel = self.client.get_channel(self.live_channel_id)
        if channel is None:
            try:
                channel = await self.client.fetch_channel(
                    self.live_channel_id)
            except Exception:
                log.warning("Live-update channel %s unreachable",
                            self.live_channel_id)
                return
        try:
            await channel.send(embed=self.build_weather_card())
            self._last_signature = sig
            self._last_post_ts = now
        except Exception:
            log.exception("Live-update post failed")

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def run(self) -> None:
        """Connect and sync slash commands; runs until cancelled.

        If the MESSAGE CONTENT intent is not enabled for the bot in the
        Developer Portal, log clear instructions and stop cleanly instead of
        crash-looping under the supervisor (slash commands still work).
        """
        await self.client.login(self.token)
        try:
            await self.client.start(self.token)
        except asyncio.CancelledError:
            await self.client.close()
            raise
        except Exception as exc:
            if type(exc).__name__ == "PrivilegedIntentsRequired":
                log.warning(
                    "Discord: enable 'Message Content Intent' in the "
                    "Developer Portal (Bot tab) for 'speak the weather'. "
                    "Slash commands disabled until fixed."
                )
                await self.client.close()
                return
            raise


def get_lcd_safe():
    try:
        from hardware.lcd_driver import get_lcd
        return get_lcd()
    except Exception:
        return None


async def discord_bot_task() -> None:
    """Supervised entry: start the bot when a token is configured.

    Runs the client and the live-update loop concurrently; both die with the
    task so the supervisor can restart the whole Discord subsystem cleanly.
    """
    if not HAS_DISCORD:
        log.info("discord.py not installed — Discord bot disabled")
        return
    token = config.DISCORD_BOT_TOKEN
    if not token:
        log.info("DISCORD_BOT_TOKEN not set — Discord bot disabled "
                 "(run the setup wizard to enable)")
        return
    if config.DISCORD_UPDATE_CHANNEL_ID:
        log.info("Discord live updates -> channel %s (min interval %ss)",
                 config.DISCORD_UPDATE_CHANNEL_ID,
                 config.DISCORD_UPDATE_MIN_INTERVAL_S)

    bot = WeatherBotClient(token)
    live_task = asyncio.create_task(_live_update_loop(bot),
                                    name="discord-live-updates")
    try:
        await bot.run()
    finally:
        live_task.cancel()


async def _live_update_loop(bot: "WeatherBotClient") -> None:
    """Poll the station state; hand changed data to the poster."""
    try:
        while True:
            try:
                await bot.live_update_tick()
            except asyncio.CancelledError:
                raise
            except Exception:
                log.exception("live update tick failed")
            await asyncio.sleep(15)
    except asyncio.CancelledError:
        raise
