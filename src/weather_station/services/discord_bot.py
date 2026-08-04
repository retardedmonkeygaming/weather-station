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
        intents.message_content = True  # Allows reading "How is it inside?"
        intents.members = True          # For future permissions
        
        super().__init__(command_prefix="!", intents=intents)
        self.persona = "Weather Station Assistant"

    async def setup_hook(self):
        """Called when the bot starts to sync slash commands."""
        await self.tree.sync()
        self.presence_task.start()

    @tasks.loop(minutes=10)
    async def presence_task(self):
        """Updates the sidebar status: 'Watching In: 23.5C'"""
        if state.indoor_temp:
            activity = discord.Activity(
                type=discord.ActivityType.watching, 
                name=f"In: {state.indoor_temp}°{settings.unit}"
            )
            await self.change_presence(activity=activity)

    async def on_ready(self):
        logger.info(f"Bot logged in as {self.user} (ID: {self.user.id})")

    # --- 1. CONVERSATIONAL LAYER (Natural Language) ---
    async def on_message(self, message):
        if message.author == self.user:
            return

        # Check if it's a DM or a mention in #station-chat
        is_dm = isinstance(message.channel, discord.DMChannel)
        is_station_chat = message.channel.name == "station-chat"

        if is_dm or is_station_chat:
            content = message.content.lower()
            
            # Simple Intent Matching (NLP)
            if "how" in content and "inside" in content:
                await message.reply(f"It's currently **{state.indoor_temp}°{settings.unit}** inside with **{state.indoor_humid}%** humidity.")
            
            elif "outside" in content:
                await message.reply(f"The outdoor temperature is **{state.outdoor_temp}°{settings.unit}**. It looks **{state.weather_text}** out there.")
            
            elif "aqi" in content or "air" in content:
                await message.reply(f"The Air Quality Index is **{state.aqi_val}**, which is considered **{state.aqi_status}**.")
            
            elif "pi" in content or "health" in content:
                stats = SystemService.get_stats()
                await message.reply(f"I'm running smoothly! My CPU is at **{stats['cpu_temp']}**.")

        await self.process_commands(message)

    # --- 2. SLASH COMMANDS (Professional UI) ---
    @app_commands.command(name="status", description="Full weather breakdown in a rich card")
    async def status(self, interaction: discord.Interaction):
        embed = discord.Embed(title="🌡️ Pi Weather Station", color=0x0288d1)
        embed.add_field(name="🏠 Indoor", value=f"{state.indoor_temp}°{settings.unit}\nHumid: {state.indoor_humid}%", inline=True)
        embed.add_field(name="🌍 Outdoor", value=f"{state.outdoor_temp}°{settings.unit}\nHumid: {state.outdoor_humid}%", inline=True)
        embed.add_field(name="🍃 AQI", value=f"{state.aqi_val} ({state.aqi_status})", inline=False)
        embed.add_field(name="☀️ UV Index", value=f"Current: {state.uv_index} (Peak: {state.uv_max})", inline=True)
        embed.set_footer(text=f"LCD Preview: {state.last_line1} | {state.last_line2}")
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="lcd", description="See exactly what the physical LCD shows")
    async def lcd_preview(self, interaction: discord.Interaction):
        await interaction.response.send_message(f"**Physical LCD Content:**\n```\n[{state.last_line1}]\n[{state.last_line2}]\n```")