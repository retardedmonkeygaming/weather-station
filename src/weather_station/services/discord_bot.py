import discord
from discord.ext import commands, tasks
from discord import app_commands, ui
import logging
from datetime import datetime
from weather_station.core.state import state
from weather_station.core.config import settings
from weather_station.services.system import SystemService
from weather_station.utils.formatting import calculate_moon_phase

logger = logging.getLogger("DiscordBot")

class WeatherBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True 
        intents.members = True          
        
        super().__init__(command_prefix="!", intents=intents, help_command=None)
        self.conversation_memory = {}  # Per-user short memory

    async def setup_hook(self):
        """Syncs slash commands instantly to all joined servers."""
        for guild in self.guilds:
            self.tree.copy_global_to(guild=guild)
            await self.tree.sync(guild=guild)
        await self.tree.sync()
        self.presence_task.start()
        self.briefing_task.start()
        
    @tasks.loop(minutes=5)
    async def presence_task(self):
        """Updates the sidebar status with live temperature."""
        await self.wait_until_ready()
        if state.indoor_temp is not None:
            try:
                activity = discord.Activity(
                    type=discord.ActivityType.watching, 
                    name=f"🌡️ {state.indoor_temp}°{settings.unit} Indoor"
                )
                await self.change_presence(activity=activity, status=discord.Status.online)
            except Exception as e:
                logger.error(f"Failed to update presence: {e}")
    
    @tasks.loop(hours=24)
    async def briefing_task(self):
        """Sends daily morning briefing to designated channel."""
        await self.wait_until_ready()
        if settings.discord_channel_id and settings.alert_enabled:
            try:
                channel = self.get_channel(settings.discord_channel_id)
                if channel:
                    embed = self.create_status_embed(title="🌅 Good Morning! Daily Weather Briefing")
                    await channel.send(embed=embed)
            except Exception as e:
                logger.error(f"Briefing failed: {e}")
    
    @briefing_task.before_loop
    async def before_briefing(self):
        await self.wait_until_ready()
        # Wait until 7 AM
        now = datetime.now()
        target = now.replace(hour=7, minute=0, second=0, microsecond=0)
        if now > target:
            target = target.replace(day=target.day + 1)
        delay = (target - now).total_seconds()
        await asyncio.sleep(delay)

    async def on_ready(self):
        logger.info(f"Discord Bot online as {self.user} in {len(self.guilds)} guilds")

    def create_status_embed(self, title="🌡️ SkyCast Weather Station", color=0x0288d1):
        """Creates a professional, consistent embed for weather data."""
        moon = calculate_moon_phase()
        stats = SystemService.get_stats()
        
        embed = discord.Embed(
            title=title,
            color=color,
            timestamp=datetime.now(),
            description="Live from your personal weather station"
        )
        
        # Indoor/Outdoor side by side
        embed.add_field(
            name="🏠 Indoor Climate",
            value=f"**Temperature:** {state.indoor_temp}°{settings.unit}\n**Humidity:** {state.indoor_humid}%",
            inline=True
        )
        embed.add_field(
            name="🌍 Outdoor Weather",
            value=f"**Temperature:** {state.outdoor_temp}°{settings.unit}\n**Condition:** {state.weather_text}",
            inline=True
        )
        
        # AQI and UV
        embed.add_field(
            name="🍃 Air Quality & UV",
            value=f"**AQI:** {state.aqi_val} ({state.aqi_status})\n**UV Index:** {state.uv_index}",
            inline=False
        )
        
        # Moon phase
        embed.add_field(
            name="🌙 Moon Phase",
            value=f"{moon.get('short_name', 'N/A')} • {moon.get('illumination', 0)}% illuminated",
            inline=True
        )
        
        # System health
        embed.add_field(
            name="⚡ System Health",
            value=f"CPU: {stats.get('cpu_temp', 'N/A')}\nUptime: {stats.get('uptime', 'N/A')}",
            inline=True
        )
        
        embed.set_footer(text=f"SkyCast v1.0.0 • Live Data")
        return embed

    # --- CONVERSATIONAL LAYER ---
    async def on_message(self, message):
        if message.author == self.user:
            return

        is_dm = isinstance(message.channel, discord.DMChannel)
        is_station_chat = hasattr(message.channel, 'name') and message.channel.name == "station-chat"

        if is_dm or is_station_chat:
            content = message.content.lower()
            user_key = str(message.author.id)
            
            # Simple conversation patterns
            if any(word in content for word in ["how", "inside", "indoor"]):
                await message.reply(f"It's currently **{state.indoor_temp}°{settings.unit}** inside with **{state.indoor_humid}%** humidity.")
                self.conversation_memory[user_key] = {"last_topic": "indoor", "time": datetime.now()}
            
            elif any(word in content for word in ["outside", "outdoor", "weather"]):
                await message.reply(f"The outdoor temperature is **{state.outdoor_temp}°{settings.unit}**. It is **{state.weather_text}**.")
                self.conversation_memory[user_key] = {"last_topic": "outdoor", "time": datetime.now()}
            
            elif "aqi" in content or "air quality" in content:
                await message.reply(f"The Air Quality Index is **{state.aqi_val}** ({state.aqi_status}).")
                self.conversation_memory[user_key] = {"last_topic": "aqi", "time": datetime.now()}
            
            elif "lcd" in content or "screen" in content or "display" in content:
                await message.reply(f"The physical LCD currently shows:\n```\n[{state.last_line1}]\n[{state.last_line2}]\n```")
                self.conversation_memory[user_key] = {"last_topic": "lcd", "time": datetime.now()}
            
            elif "help" in content:
                await message.reply("👋 I'm your SkyCast weather assistant! Try these commands:\n• `/status` - Full weather report\n• `/now` - Quick current conditions\n• `/health` - System health check\n• Or just ask me about the weather!")

        await self.process_commands(message)

    # --- SLASH COMMANDS ---
    @app_commands.command(name="status", description="Get a full weather report card")
    async def status(self, interaction: discord.Interaction):
        embed = self.create_status_embed()
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="now", description="Quick current conditions")
    async def now(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="☁️ Current Conditions",
            color=0x0288d1,
            timestamp=datetime.now()
        )
        embed.add_field(name="🏠 Indoor", value=f"{state.indoor_temp}°{settings.unit} / {state.indoor_humid}%", inline=True)
        embed.add_field(name="🌍 Outdoor", value=f"{state.outdoor_temp}°{settings.unit} / {state.outdoor_humid}%", inline=True)
        embed.add_field(name="🍃 AQI", value=f"{state.aqi_val} - {state.aqi_status}", inline=False)
        embed.set_footer(text="SkyCast • Live Data")
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="health", description="System health diagnostics")
    async def health_cmd(self, interaction: discord.Interaction):
        stats = SystemService.get_stats()
        
        # Color based on health
        cpu_temp = stats.get('cpu_temp', '0°C')
        try:
            temp_val = float(cpu_temp.replace('°C', ''))
            color = 0x2e7d32 if temp_val < 60 else 0xf57c00 if temp_val < 80 else 0xc62828
        except:
            color = 0x546e7a
        
        embed = discord.Embed(
            title="⚡ System Health Check",
            color=color,
            timestamp=datetime.now()
        )
        embed.add_field(name="🖥️ CPU Temperature", value=stats.get('cpu_temp', 'N/A'), inline=True)
        embed.add_field(name="📊 CPU Usage", value=stats.get('cpu_percent', 'N/A'), inline=True)
        embed.add_field(name="💾 Memory", value=stats.get('memory_percent', 'N/A'), inline=True)
        embed.add_field(name="⏱️ Uptime", value=stats.get('uptime', 'N/A'), inline=True)
        embed.add_field(name="🌡️ Sensors", value="✅ OK" if state.indoor_temp else "❌ Error", inline=True)
        embed.add_field(name="🌐 API Connection", value="✅ Connected" if state.outdoor_temp != "N/A" else "❌ Disconnected", inline=True)
        
        # Buttons for actions
        view = ui.View()
        view.add_item(ui.Button(label="Open Dashboard", url=f"http://localhost:{settings.web_port}", style=discord.ButtonStyle.link))
        
        embed.set_footer(text=f"SkyCast v1.0.0 • All systems operational")
        await interaction.response.send_message(embed=embed, view=view)

    @app_commands.command(name="help", description="Show help and available commands")
    async def help_cmd(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="📖 SkyCast Weather Bot Help",
            color=0x0288d1,
            description="Your personal weather monitoring assistant"
        )
        embed.add_field(
            name="📊 Weather Commands",
            value="`/status` - Full weather report with all metrics\n`/now` - Quick current conditions\n`/aqi` - Air quality details",
            inline=False
        )
        embed.add_field(
            name="⚡ System Commands",
            value="`/health` - System diagnostics and status\n`/about` - Bot information",
            inline=False
        )
        embed.add_field(
            name="💬 Natural Language",
            value="Just ask about indoor/outdoor temperature, air quality, or LCD display in DMs or #station-chat!",
            inline=False
        )
        embed.set_footer(text="SkyCast v1.0.0 • Mention me for quick help")
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="about", description="About this bot")
    async def about(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="🌤️ About SkyCast Weather Station",
            color=0x0288d1,
            description="A professional, self-hosted weather monitoring system running on Raspberry Pi.",
            timestamp=datetime.now()
        )
        embed.add_field(name="Version", value="1.0.0", inline=True)
        embed.add_field(name="Guilds", value=str(len(self.guilds)), inline=True)
        embed.add_field(name="Uptime", value="Active", inline=True)
        embed.add_field(
            name="Features",
            value="• Real-time weather monitoring\n• LCD display integration\n• Air quality tracking\n• System health monitoring\n• Natural language queries",
            inline=False
        )
        embed.set_footer(text="Live from your station • SkyCast Project")
        await interaction.response.send_message(embed=embed)

# Confirmation modal for destructive actions
class ConfirmModal(ui.Modal, title="Confirm Action"):
    def __init__(self, action_name):
        super().__init__()
        self.action_name = action_name
        self.confirmed = False
    
    confirm_input = ui.TextInput(label=f"Type 'CONFIRM' to proceed", placeholder="CONFIRM", max_length=10)
    
    async def on_submit(self, interaction: discord.Interaction):
        if self.confirm_input.value.upper() == "CONFIRM":
            self.confirmed = True
            await interaction.response.send_message(f"✅ {self.action_name} confirmed.", ephemeral=True)
        else:
            await interaction.response.send_message("❌ Action cancelled.", ephemeral=True)

import asyncio
