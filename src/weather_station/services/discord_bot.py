import discord
from discord.ext import commands, tasks
from discord import app_commands
import logging
from weather_station.core.state import state
from weather_station.core.config import settings
from weather_station.services.system import SystemService

logger = logging.getLogger("DiscordBot")

class WeatherBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True 
        intents.members = True          
        
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        """Syncs slash commands instantly to all joined servers."""
        # This loop makes slash commands appear instantly in your specific servers
        for guild in self.guilds:
            self.tree.copy_global_to(guild=guild)
            await self.tree.sync(guild=guild)
        
        # Also sync globally (can take up to an hour for new servers)
        await self.tree.sync()
        
        self.presence_task.start()
    @tasks.loop(minutes=5)
    async def presence_task(self):
        """Updates the sidebar status with live temperature."""
        # Wait until the bot is fully connected to avoid the 'NoneType' error
        await self.wait_until_ready()
        
        if state.indoor_temp is not None:
            try:
                activity = discord.Activity(
                    type=discord.ActivityType.watching, 
                    name=f"In: {state.indoor_temp}°{settings.unit}"
                )
                await self.change_presence(activity=activity)
            except Exception as e:
                logger.error(f"Failed to update presence: {e}")

    async def on_ready(self):
        logger.info(f"Discord Bot online as {self.user}")

    # --- 1. CONVERSATIONAL LAYER (DM & Channel Chat) ---
    async def on_message(self, message):
        if message.author == self.user:
            return

        # Handle DMs or messages in #station-chat
        is_dm = isinstance(message.channel, discord.DMChannel)
        # Check for channel name safely
        is_station_chat = hasattr(message.channel, 'name') and message.channel.name == "station-chat"

        if is_dm or is_station_chat:
            content = message.content.lower()
            
            if "how" in content and "inside" in content:
                await message.reply(f"It's currently **{state.indoor_temp}°{settings.unit}** inside with **{state.indoor_humid}%** humidity.")
            
            elif "outside" in content:
                await message.reply(f"The outdoor temperature is **{state.outdoor_temp}°{settings.unit}**. It is **{state.weather_text}**.")
            
            elif "aqi" in content or "air" in content:
                await message.reply(f"The Air Quality Index is **{state.aqi_val}** ({state.aqi_status}).")
            
            elif "lcd" in content or "screen" in content:
                await message.reply(f"The physical LCD currently says:\n```\n[{state.last_line1}]\n[{state.last_line2}]\n```")

        await self.process_commands(message)

    # --- 2. SLASH COMMANDS (/status) ---
    @app_commands.command(name="status", description="Get a full weather report card")
    async def status(self, interaction: discord.Interaction):
        embed = discord.Embed(title="🌡️ Pi Weather Station Status", color=0x0288d1)
        embed.add_field(name="🏠 Indoor", value=f"{state.indoor_temp}°{settings.unit} / {state.indoor_humid}%", inline=True)
        embed.add_field(name="🌍 Outdoor", value=f"{state.outdoor_temp}°{settings.unit} / {state.outdoor_humid}%", inline=True)
        embed.add_field(name="🍃 AQI", value=f"{state.aqi_val} ({state.aqi_status})", inline=False)
        embed.add_field(name="☀️ UV Index", value=f"Current: {state.uv_index} (Peak: {state.uv_max})", inline=True)
        embed.set_footer(text=f"System Health: {SystemService.get_stats()['cpu_temp']}")
        await interaction.response.send_message(embed=embed)