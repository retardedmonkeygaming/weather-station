"""Discord bot integration for SkyCast Weather Station."""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

import discord
from discord.ext import commands, tasks
from discord import app_commands, ui, Interaction, Client

from weather_station.core.state import state
from weather_station.core.config import settings
from weather_station.persistence.database import DatabaseManager
from weather_station.services.system import SystemService
from weather_station.utils.formatting import calculate_moon_phase


logger = logging.getLogger("DiscordBot")

db_manager = DatabaseManager()


class SetupWizardView(ui.View):
    """Interactive setup wizard for new servers."""
    
    def __init__(self, bot: "WeatherBot", server_id: str):
        super().__init__(timeout=300)  # 5 minute timeout
        self.bot = bot
        self.server_id = server_id
        self.step = 0
        self.config: Dict[str, Any] = {
            "channel_id": None,
            "allowed_roles": [],
            "nl_enabled": True,
            "briefing_hour": 7,
            "quiet_hours_start": 22,
            "quiet_hours_end": 7
        }
    
    @ui.button(label="Select Channel", style=discord.ButtonStyle.primary, emoji="📺")
    async def select_channel(self, interaction: Interaction, button: ui.Button):
        """Step 1: Select default channel."""
        await interaction.response.send_message(
            "Please select a channel for weather updates:",
            view=ChannelSelectView(self),
            ephemeral=True
        )
    
    @ui.button(label="Configure Roles", style=discord.ButtonStyle.secondary, emoji="👥")
    async def config_roles(self, interaction: Interaction, button: ui.Button):
        """Step 2: Configure allowed roles."""
        await interaction.response.send_message(
            "Configure which roles can use control commands.",
            view=RoleSelectView(self),
            ephemeral=True
        )
    
    @ui.button(label="Toggle Natural Language", style=discord.ButtonStyle.success, emoji="💬")
    async def toggle_nl(self, interaction: Interaction, button: ui.Button):
        """Toggle natural language feature."""
        self.config["nl_enabled"] = not self.config["nl_enabled"]
        button.style = discord.ButtonStyle.success if self.config["nl_enabled"] else discord.ButtonStyle.danger
        button.label = f"NL: {'Enabled' if self.config['nl_enabled'] else 'Disabled'}"
        await interaction.response.edit_message(view=self)
    
    @ui.button(label="Finish Setup", style=discord.ButtonStyle.green, emoji="✅")
    async def finish(self, interaction: Interaction, button: ui.Button):
        """Complete setup and save configuration."""
        await db_manager.save_discord_server(
            server_id=self.server_id,
            channel_id=str(self.config["channel_id"]) if self.config["channel_id"] else None,
            allowed_roles=",".join(map(str, self.config["allowed_roles"])) if self.config["allowed_roles"] else None,
            nl_enabled=self.config["nl_enabled"],
            briefing_hour=self.config["briefing_hour"],
            quiet_hours_start=self.config["quiet_hours_start"],
            quiet_hours_end=self.config["quiet_hours_end"]
        )
        
        embed = discord.Embed(
            title="✅ Setup Complete!",
            description="Your SkyCast Weather Station is now configured.",
            color=0x2e7d32,
            timestamp=datetime.now()
        )
        embed.add_field(name="Natural Language", value="Enabled" if self.config["nl_enabled"] else "Disabled", inline=True)
        embed.add_field(name="Briefing Hour", value=f"{self.config['briefing_hour']}:00", inline=True)
        embed.set_footer(text="Use /setup to reconfigure anytime")
        
        await interaction.response.send_message(embed=embed, ephemeral=False)
        self.stop()


class ChannelSelectView(ui.View):
    """Channel selection for setup wizard."""
    
    def __init__(self, wizard: SetupWizardView):
        super().__init__()
        self.wizard = wizard
        
        select = ui.ChannelSelect(
            placeholder="Choose a channel...",
            max_values=1,
            channel_types=[discord.ChannelType.text]
        )
        select.callback = self.channel_callback
        self.add_item(select)
    
    async def channel_callback(self, interaction: Interaction):
        channel = interaction.data["resolved"]["channels"][list(interaction.data["resolved"]["channels"].keys())[0]]
        self.wizard.config["channel_id"] = channel["id"]
        await interaction.response.send_message(
            f"✅ Channel selected: <#{channel['id']}>\n\nNext step: Configure roles or finish setup.",
            view=self.wizard,
            ephemeral=True
        )


class RoleSelectView(ui.View):
    """Role selection for setup wizard."""
    
    def __init__(self, wizard: SetupWizardView):
        super().__init__()
        self.wizard = wizard
        
        select = ui.RoleSelect(
            placeholder="Select roles (optional)...",
            max_values=10
        )
        select.callback = self.role_callback
        self.add_item(select)
    
    async def role_callback(self, interaction: Interaction):
        roles = [r["id"] for r in interaction.data["resolved"]["roles"].values()] if "resolved" in interaction.data else []
        self.wizard.config["allowed_roles"] = roles
        await interaction.response.send_message(
            f"✅ Roles configured: {len(roles)} role(s)\n\nContinue with setup.",
            view=self.wizard,
            ephemeral=True
        )


class WeatherBot(commands.Bot):
    """Discord bot for weather station interactions."""

    def __init__(self) -> None:
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True

        super().__init__(command_prefix="!", intents=intents, help_command=None)
        self.conversation_memory: dict[str, dict] = {}  # Per-user short memory
        self.setup_in_progress: set[str] = set()  # Track servers in setup

    async def setup_hook(self) -> None:
        """Syncs slash commands instantly to all joined servers."""
        for guild in self.guilds:
            self.tree.copy_global_to(guild=guild)
            await self.tree.sync(guild=guild)
        await self.tree.sync()
        
        # Initialize database
        await db_manager.initialize()
        
        self.presence_task.start()
        self.briefing_task.start()
        
        logger.info(f"Bot ready in {len(self.guilds)} guilds")

    @tasks.loop(minutes=5)
    async def presence_task(self) -> None:
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
    async def briefing_task(self) -> None:
        """Sends daily morning briefing to designated channels."""
        await self.wait_until_ready()
        
        # Get all configured servers
        async with db_manager.db_path if hasattr(db_manager, 'db_path') else None:
            pass  # Will be implemented with proper async context
        
        for guild in self.guilds:
            try:
                server_config = await db_manager.get_discord_server(str(guild.id))
                if server_config and server_config.get("channel_id"):
                    channel = self.get_channel(int(server_config["channel_id"]))
                    if channel and server_config.get("nl_enabled", True):
                        # Check quiet hours
                        current_hour = datetime.now().hour
                        qh_start = server_config.get("quiet_hours_start", 22)
                        qh_end = server_config.get("quiet_hours_end", 7)
                        
                        # Skip if in quiet hours
                        if qh_start > qh_end:  # Spans midnight
                            if qh_start <= current_hour < qh_end:
                                continue
                        else:
                            if qh_start <= current_hour < qh_end:
                                continue
                        
                        embed = self.create_status_embed(title="🌅 Good Morning! Daily Weather Briefing")
                        await channel.send(embed=embed)
            except Exception as e:
                logger.error(f"Briefing failed for guild {guild.id}: {e}")

    @briefing_task.before_loop
    async def before_briefing(self) -> None:
        """Wait until 7 AM before starting the briefing task."""
        await self.wait_until_ready()
        now = datetime.now()
        target = now.replace(hour=7, minute=0, second=0, microsecond=0)
        if now > target:
            target = target + timedelta(days=1)
        delay = (target - now).total_seconds()
        await asyncio.sleep(delay)

    async def on_guild_join(self, guild: discord.Guild) -> None:
        """Handle bot joining a new server - start setup wizard."""
        logger.info(f"Joined guild: {guild.name} ({guild.id})")
        
        # Find owner or admin
        owner = guild.owner
        if not owner:
            for member in guild.members:
                if member.guild_permissions.administrator:
                    owner = member
                    break
        
        if owner:
            embed = discord.Embed(
                title="🌤️ Welcome to SkyCast Weather Station!",
                description="Thank you for adding me! Let's get me set up.",
                color=0x0288d1,
                timestamp=datetime.now()
            )
            embed.add_field(
                name="Quick Start",
                value=(
                    "I can help you monitor weather conditions with:\n"
                    "• `/status` - Full weather report\n"
                    "• `/now` - Quick conditions\n"
                    "• `/health` - System diagnostics\n"
                    "• Or just ask me about the weather!"
                ),
                inline=False
            )
            embed.set_footer(text="Use /setup to begin configuration")
            
            try:
                await owner.send(embed=embed)
            except discord.Forbidden:
                # Can't DM, send in general channel
                for channel in guild.text_channels:
                    if channel.permissions_for(guild.me).send_messages:
                        await channel.send(
                            content="👋 Hello! I'm your SkyCast weather assistant. Use `/setup` to configure me!",
                            embed=embed
                        )
                        break

    async def on_ready(self) -> None:
        """Called when the bot is ready."""
        logger.info(f"Discord Bot online as {self.user} in {len(self.guilds)} guilds")
        state.discord_ready = True
        state.discord_guilds = len(self.guilds)

    def create_status_embed(
        self,
        title: str = "🌡️ SkyCast Weather Station",
        color: int = 0x0288d1
    ) -> discord.Embed:
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

        embed.set_footer(text=f"SkyCast v{state.__class__.__module__.split('.')[0]} • Live Data")
        return embed

    async def on_message(self, message: discord.Message) -> None:
        """Handle incoming messages for conversational interface."""
        if message.author == self.user:
            return

        # Check if NL is enabled for this server
        server_config = None
        if message.guild:
            server_config = await db_manager.get_discord_server(str(message.guild.id))
            nl_enabled = server_config.get("nl_enabled", True) if server_config else True
        else:
            nl_enabled = True  # Always enabled in DMs

        if not nl_enabled:
            return

        is_dm = isinstance(message.channel, discord.DMChannel)
        is_station_chat = hasattr(message.channel, 'name') and message.channel.name == "station-chat"

        if is_dm or is_station_chat:
            content = message.content.lower()
            user_key = str(message.author.id)

            # Get user preferences
            user_config = await db_manager.get_discord_user(user_key)
            units = user_config.get("preferred_units", "C") if user_config else "C"

            # Simple conversation patterns
            if any(word in content for word in ["how", "inside", "indoor"]):
                await message.reply(
                    f"It's currently **{state.indoor_temp}°{units}** inside "
                    f"with **{state.indoor_humid}%** humidity."
                )
                self.conversation_memory[user_key] = {"last_topic": "indoor", "time": datetime.now()}

            elif any(word in content for word in ["outside", "outdoor", "weather"]):
                await message.reply(
                    f"The outdoor temperature is **{state.outdoor_temp}°{units}**. "
                    f"It is **{state.weather_text}**."
                )
                self.conversation_memory[user_key] = {"last_topic": "outdoor", "time": datetime.now()}

            elif "aqi" in content or "air quality" in content:
                await message.reply(
                    f"The Air Quality Index is **{state.aqi_val}** ({state.aqi_status})."
                )
                self.conversation_memory[user_key] = {"last_topic": "aqi", "time": datetime.now()}

            elif "lcd" in content or "screen" in content or "display" in content:
                await message.reply(
                    f"The physical LCD currently shows:\n```\n[{state.last_line1}]\n[{state.last_line2}]\n```"
                )
                self.conversation_memory[user_key] = {"last_topic": "lcd", "time": datetime.now()}

            elif "help" in content:
                await message.reply(
                    "👋 I'm your SkyCast weather assistant! Try these commands:\n"
                    "• `/status` - Full weather report\n"
                    "• `/now` - Quick current conditions\n"
                    "• `/health` - System health check\n"
                    "• Or just ask me about the weather!"
                )

        await self.process_commands(message)

    # --- SLASH COMMANDS ---

    @app_commands.command(name="setup", description="Configure SkyCast for this server")
    async def setup(self, interaction: discord.Interaction) -> None:
        """Start the setup wizard."""
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message(
                "❌ You need administrator permissions to run setup.",
                ephemeral=True
            )
            return
        
        wizard = SetupWizardView(self, str(interaction.guild_id))
        embed = discord.Embed(
            title="🔧 SkyCast Setup Wizard",
            description="Configure your weather station integration",
            color=0x0288d1
        )
        embed.add_field(
            name="Steps",
            value=(
                "1️⃣ Select default channel for alerts\n"
                "2️⃣ Configure allowed roles\n"
                "3️⃣ Toggle natural language\n"
                "4️⃣ Finish and save"
            ),
            inline=False
        )
        
        await interaction.response.send_message(embed=embed, view=wizard, ephemeral=True)

    @app_commands.command(name="status", description="Get a full weather report card")
    async def status(self, interaction: discord.Interaction) -> None:
        """Get a full weather report."""
        embed = self.create_status_embed()
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="now", description="Quick current conditions")
    async def now(self, interaction: discord.Interaction) -> None:
        """Get quick current conditions."""
        embed = discord.Embed(
            title="☁️ Current Conditions",
            color=0x0288d1,
            timestamp=datetime.now()
        )
        embed.add_field(
            name="🏠 Indoor",
            value=f"{state.indoor_temp}°{settings.unit} / {state.indoor_humid}%",
            inline=True
        )
        embed.add_field(
            name="🌍 Outdoor",
            value=f"{state.outdoor_temp}°{settings.unit} / {state.outdoor_humid}%",
            inline=True
        )
        embed.add_field(
            name="🍃 AQI",
            value=f"{state.aqi_val} - {state.aqi_status}",
            inline=False
        )
        embed.set_footer(text="SkyCast • Live Data")
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="health", description="System health diagnostics")
    async def health_cmd(self, interaction: discord.Interaction) -> None:
        """Check system health."""
        stats = SystemService.get_stats()

        # Color based on health
        cpu_temp = stats.get('cpu_temp', '0°C')
        try:
            temp_val = float(cpu_temp.replace('°C', ''))
            color = 0x2e7d32 if temp_val < 60 else 0xf57c00 if temp_val < 80 else 0xc62828
        except (ValueError, AttributeError):
            color = 0x546e7a

        embed = discord.Embed(
            title="⚡ System Health Check",
            color=color,
            timestamp=datetime.now()
        )
        embed.add_field(name="🖥️ CPU Temperature", value=stats.get('cpu_temp', 'N/A'), inline=True)
        embed.add_field(name="📊 CPU Usage", value=stats.get('cpu_usage', 'N/A'), inline=True)
        embed.add_field(name="💾 Memory", value=stats.get('ram_usage', 'N/A'), inline=True)
        embed.add_field(name="⏱️ Uptime", value=stats.get('uptime', 'N/A'), inline=True)
        embed.add_field(
            name="🌡️ Sensors",
            value="✅ OK" if state.indoor_temp else "❌ Error",
            inline=True
        )
        embed.add_field(
            name="🌐 API Connection",
            value="✅ Connected" if state.outdoor_temp != "N/A" else "❌ Disconnected",
            inline=True
        )

        # Buttons for actions
        view = ui.View()
        view.add_item(ui.Button(
            label="Open Dashboard",
            url=f"http://localhost:{settings.web_port}",
            style=discord.ButtonStyle.link
        ))

        embed.set_footer(text=f"SkyCast v3.0.0 • All systems operational")
        await interaction.response.send_message(embed=embed, view=view)

    @app_commands.command(name="help", description="Show help and available commands")
    async def help_cmd(self, interaction: discord.Interaction) -> None:
        """Show help information."""
        embed = discord.Embed(
            title="📖 SkyCast Weather Bot Help",
            color=0x0288d1,
            description="Your personal weather monitoring assistant"
        )
        embed.add_field(
            name="📊 Weather Commands",
            value=(
                "`/status` - Full weather report with all metrics\n"
                "`/now` - Quick current conditions\n"
                "`/aqi` - Air quality details"
            ),
            inline=False
        )
        embed.add_field(
            name="⚡ System Commands",
            value=(
                "`/health` - System diagnostics and status\n"
                "`/about` - Bot information\n"
                "`/setup` - Configure for this server"
            ),
            inline=False
        )
        embed.add_field(
            name="💬 Natural Language",
            value="Just ask about indoor/outdoor temperature, air quality, or LCD display in DMs or #station-chat!",
            inline=False
        )
        embed.set_footer(text="SkyCast v3.0.0 • Mention me for quick help")
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="about", description="About this bot")
    async def about(self, interaction: discord.Interaction) -> None:
        """Show information about the bot."""
        embed = discord.Embed(
            title="🌤️ About SkyCast Weather Station",
            color=0x0288d1,
            description="A professional, self-hosted weather monitoring system running on Raspberry Pi.",
            timestamp=datetime.now()
        )
        embed.add_field(name="Version", value="3.0.0", inline=True)
        embed.add_field(name="Guilds", value=str(len(self.guilds)), inline=True)
        embed.add_field(name="Uptime", value="Active", inline=True)
        embed.add_field(
            name="Features",
            value=(
                "• Real-time weather monitoring\n"
                "• LCD display integration\n"
                "• Air quality tracking\n"
                "• System health monitoring\n"
                "• Natural language queries"
            ),
            inline=False
        )
        embed.set_footer(text="Live from your station • SkyCast Project")
        await interaction.response.send_message(embed=embed)


# Confirmation modal for destructive actions
class ConfirmModal(ui.Modal, title="Confirm Action"):
    """Modal dialog for confirming destructive actions."""

    def __init__(self, action_name: str) -> None:
        super().__init__()
        self.action_name = action_name
        self.confirmed = False

    confirm_input = ui.TextInput(
        label="Type 'CONFIRM' to proceed",
        placeholder="CONFIRM",
        max_length=10
    )

    async def on_submit(self, interaction: discord.Interaction) -> None:
        """Handle modal submission."""
        if self.confirm_input.value.upper() == "CONFIRM":
            self.confirmed = True
            await interaction.response.send_message(
                f"✅ {self.action_name} confirmed.",
                ephemeral=True
            )
        else:
            await interaction.response.send_message("❌ Action cancelled.", ephemeral=True)
