"""
Display Manager
Manages LCD display, widgets, and page transitions
"""

import asyncio
from typing import Optional, Dict, Any, List
from datetime import datetime

from ..hardware.interfaces import LCDInterface
from .widgets import BaseWidget, ClockWidget, IndoorWidget, OutdoorWidget, AQIWidget, SystemWidget, SettingsWidget


class DisplayManager:
    """
    Manages the LCD display with widget-based rendering.
    Handles page transitions, auto-scrolling, and backlight control.
    """
    
    def __init__(
        self,
        lcd_interface: LCDInterface,
        state: Any,
        auto_scroll_interval: float = 5.0,
        auto_dim_seconds: int = 60
    ):
        self.lcd = lcd_interface
        self.state = state
        self.auto_scroll_interval = auto_scroll_interval
        self.auto_dim_seconds = auto_dim_seconds
        
        # Initialize widgets
        self.widgets: List[BaseWidget] = [
            ClockWidget(),      # Page 0 - Clock (permanent)
            IndoorWidget(),     # Page 1 - Indoor climate
            OutdoorWidget(),    # Page 2 - Outdoor weather
            AQIWidget(),        # Page 3 - Air quality
            SystemWidget(),     # Page 4 - System info
            SettingsWidget(),   # Page 5 - Settings menu
        ]
        
        self.current_page = 0
        self.total_pages = len(self.widgets)
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._last_render_time: Optional[datetime] = None
        self._backlight_on = True
    
    async def initialize(self) -> bool:
        """Initialize display and create custom characters"""
        try:
            await self.lcd.initialize()
            await self.lcd.clear()
            
            # Create custom characters
            from .. import CUSTOM_CHARACTERS
            for idx, (name, bitmap) in enumerate(CUSTOM_CHARACTERS.items()):
                await self.lcd.create_custom_char(idx, bitmap)
            
            # Show boot splash
            await self._show_boot_splash()
            
            self._running = True
            self._task = asyncio.create_task(self._render_loop())
            
            print(f"[DisplayManager] Initialized with {self.total_pages} pages")
            return True
            
        except Exception as e:
            print(f"[DisplayManager] Initialization failed: {e}")
            return False
    
    async def shutdown(self) -> None:
        """Shutdown display"""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        
        await self.lcd.clear()
        await self.lcd.shutdown()
        print("[DisplayManager] Shutdown complete")
    
    async def _show_boot_splash(self) -> None:
        """Show boot splash screen"""
        from .. import __version__, __project_name__, __tagline__
        
        # Row 0: Project name
        await self.lcd.display_text(0, 0, __project_name__[:16].ljust(16))
        
        # Row 1: Version
        version_str = f"v{__version__}"
        await self.lcd.display_text(1, 0, version_str.ljust(16))
        
        # Wait 2 seconds
        await asyncio.sleep(2.0)
        await self.lcd.clear()
    
    async def _render_loop(self) -> None:
        """Main render loop"""
        while self._running:
            try:
                # Check if we should auto-dim
                await self._check_auto_dim()
                
                # Get current page
                page = self._get_current_page()
                
                # Render current widget
                if 0 <= page < len(self.widgets):
                    widget = self.widgets[page]
                    await widget.render(self.state, self.lcd)
                
                self._last_render_time = datetime.utcnow()
                
                # Wait before next render
                await asyncio.sleep(0.5)  # 500ms refresh rate
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"[DisplayManager] Render error: {e}")
                await asyncio.sleep(1.0)
    
    def _get_current_page(self) -> int:
        """Get current page from state or local"""
        if hasattr(self.state, 'display') and self.state.display:
            return self.state.display.current_page
        return self.current_page
    
    async def next_page(self) -> None:
        """Go to next page"""
        if hasattr(self.state, 'display') and self.state.display:
            if self.state.display.in_settings:
                # In settings mode, increment settings index
                self.state.display.settings_index += 1
                max_idx = 9  # 10 settings (0-9)
                if self.state.display.settings_index > max_idx:
                    self.state.display.settings_index = 0
            else:
                # Normal page navigation
                self.state.display.current_page += 1
                if self.state.display.current_page >= self.total_pages:
                    self.state.display.current_page = 0
        else:
            self.current_page = (self.current_page + 1) % self.total_pages
        
        # Wake display if dimmed
        await self.wake_display()
    
    async def prev_page(self) -> None:
        """Go to previous page"""
        if hasattr(self.state, 'display') and self.state.display:
            if not self.state.display.in_settings:
                self.state.display.current_page -= 1
                if self.state.display.current_page < 0:
                    self.state.display.current_page = self.total_pages - 1
        else:
            self.current_page = (self.current_page - 1) % self.total_pages
        
        await self.wake_display()
    
    async def enter_settings(self) -> None:
        """Enter settings mode"""
        if hasattr(self.state, 'display') and self.state.display:
            self.state.display.in_settings = True
            self.state.display.current_page = 5  # Settings page
            self.state.display.settings_index = 0
        print("[DisplayManager] Entered settings mode")
        await self.wake_display()
    
    async def exit_settings(self) -> None:
        """Exit settings mode"""
        if hasattr(self.state, 'display') and self.state.display:
            self.state.display.in_settings = False
            self.state.display.current_page = 0  # Back to clock
        print("[DisplayManager] Exited settings mode")
        await self.wake_display()
    
    async def adjust_setting(self) -> None:
        """Adjust current setting value"""
        if hasattr(self.state, 'display') and self.state.display:
            idx = self.state.display.settings_index
            if 0 <= idx < len(self.widgets):
                settings_widget = self.widgets[5]  # Settings widget
                if hasattr(settings_widget, 'cycle_setting'):
                    new_value = settings_widget.cycle_setting(idx)
                    print(f"[DisplayManager] Setting {idx} changed to: {new_value}")
        await self.wake_display()
    
    async def wake_display(self) -> None:
        """Wake display and turn on backlight"""
        if not self._backlight_on:
            self._backlight_on = True
            await self.lcd.set_backlight(True)
            if hasattr(self.state, 'display') and self.state.display:
                self.state.display.backlight_on = True
    
    async def _check_auto_dim(self) -> None:
        """Check if display should auto-dim"""
        if not self.auto_dim_seconds or not hasattr(self.state, 'display'):
            return
        
        display = self.state.display
        if not display.auto_dim_enabled or not display.last_interaction:
            return
        
        elapsed = (datetime.utcnow() - display.last_interaction).total_seconds()
        if elapsed > self.auto_dim_seconds and self._backlight_on:
            self._backlight_on = False
            await self.lcd.set_backlight(False)
            display.backlight_on = False
