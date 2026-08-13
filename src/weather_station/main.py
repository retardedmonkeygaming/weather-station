"""
SkyCast Weather Station - Main Application
Application factory pattern with all services integrated
"""

import asyncio
import signal
from typing import Optional
from pathlib import Path

from .core.config import get_settings, Settings
from .core.state import AppState, app_state
from .core.events import EventBus, EventType, event_bus
from .hardware.interfaces import MockHardware, RealHardware, HardwareInterface
from .persistence.database import DatabaseManager, get_database_manager
from .input.processor import InputProcessor, GestureConfig, TouchGesture
from .display.manager import DisplayManager
from .services.weather import WeatherService
from .services.system import SystemService


class WeatherStationApp:
    """
    Main application class using factory pattern.
    Orchestrates all components and services.
    """
    
    def __init__(self, config: Optional[Settings] = None):
        self.config = config or get_settings()
        self.state = app_state
        self.event_bus = event_bus
        
        # Components (initialized in run)
        self.hardware: Optional[HardwareInterface] = None
        self.db: Optional[DatabaseManager] = None
        self.input_processor: Optional[InputProcessor] = None
        self.display_manager: Optional[DisplayManager] = None
        self.weather_service: Optional[WeatherService] = None
        self.system_service: Optional[SystemService] = None
        
        self._running = False
        self._shutdown_event = asyncio.Event()
    
    async def initialize(self) -> bool:
        """Initialize all components"""
        print(f"[SkyCast] Initializing {self.config.app_name} v{self.config.version}")
        
        # Initialize database
        self.db = get_database_manager()
        self.db.database_url = self.config.database_url
        if not await self.db.initialize():
            print("[SkyCast] Database initialization failed")
            return False
        
        # Initialize hardware (mock or real based on config)
        if self.config.sensor.mock_hardware or self.config.is_mock():
            self.hardware = MockHardware()
        else:
            self.hardware = RealHardware()
        
        if not await self.hardware.initialize():
            print("[SkyCast] Hardware initialization failed, falling back to mock")
            self.hardware = MockHardware()
            await self.hardware.initialize()
        
        # Initialize display manager
        self.display_manager = DisplayManager(
            lcd_interface=self.hardware,
            state=self.state,
            auto_dim_seconds=60
        )
        if not await self.display_manager.initialize():
            print("[SkyCast] Display initialization failed")
            return False
        
        # Initialize input processor
        gesture_config = GestureConfig(
            debounce_ms=150,
            tap_timeout_ms=350,
            short_hold_ms=800,
            medium_hold_ms=3000,
            long_hold_ms=5000,
            extra_long_hold_ms=10000
        )
        
        self.input_processor = InputProcessor(
            hardware_interface=self.hardware,
            config=gesture_config,
            on_gesture=self._handle_gesture
        )
        
        # Initialize weather service
        self.weather_service = WeatherService(
            state=self.state,
            database_manager=self.db,
            api_key=None,  # Would come from config
            latitude=self.config.location.latitude,
            longitude=self.config.location.longitude,
            fetch_interval=self.config.data.api_fetch_interval
        )
        
        # Initialize system service
        self.system_service = SystemService(
            state=self.state,
            database_manager=self.db,
            config=self.config,
            hardware_interface=self.hardware
        )
        
        # Register event handlers
        self._register_event_handlers()
        
        print("[SkyCast] All components initialized")
        return True
    
    def _register_event_handlers(self) -> None:
        """Register event bus handlers"""
        self.event_bus.subscribe(EventType.SYSTEM_SHUTDOWN, self._on_shutdown_event)
        self.event_bus.subscribe(EventType.FACTORY_RESET, self._on_factory_reset)
    
    def _handle_gesture(self, gesture: TouchGesture):
        """Handle touch gestures"""
        if not self.display_manager:
            return
        
        if gesture == TouchGesture.TAP:
            # Single tap = next page
            asyncio.create_task(self.display_manager.next_page())
        
        elif gesture == TouchGesture.DOUBLE_TAP:
            # Double tap = previous page
            asyncio.create_task(self.display_manager.prev_page())
        
        elif gesture == TouchGesture.TRIPLE_TAP:
            # Triple tap = enter/exit settings
            if hasattr(self.state, 'display') and self.state.display.in_settings:
                asyncio.create_task(self.display_manager.exit_settings())
            else:
                asyncio.create_task(self.display_manager.enter_settings())
        
        elif gesture == TouchGesture.SHORT_HOLD:
            # Short hold = adjust setting value
            if hasattr(self.state, 'display') and self.state.display.in_settings:
                asyncio.create_task(self.display_manager.adjust_setting())
        
        elif gesture == TouchGesture.MEDIUM_HOLD:
            # Medium hold = factory reset
            print("[SkyCast] Factory reset requested (hold 3s)")
            if self.system_service:
                asyncio.create_task(self.system_service.factory_reset())
        
        elif gesture == TouchGesture.LONG_HOLD:
            # Long hold = reboot
            print("[SkyCast] Reboot requested (hold 5s)")
            if self.system_service:
                asyncio.create_task(self.system_service.reboot())
        
        elif gesture == TouchGesture.EXTRA_LONG_HOLD:
            # Extra long hold = shutdown
            print("[SkyCast] Shutdown requested (hold 10s)")
            asyncio.create_task(self.shutdown())
    
    async def _on_shutdown_event(self, event) -> None:
        """Handle shutdown event"""
        await self.shutdown()
    
    async def _on_factory_reset(self, event) -> None:
        """Handle factory reset event"""
        if self.system_service:
            await self.system_service.factory_reset()
    
    async def run(self) -> None:
        """Run the application"""
        if not await self.initialize():
            print("[SkyCast] Initialization failed, exiting")
            return
        
        self._running = True
        
        # Start all services
        await self.input_processor.start()
        await self.weather_service.start()
        await self.system_service.start()
        
        # Update state
        self.state.system.status.value = "running"
        self.state.system.version = self.config.version
        
        # Log startup
        if self.db:
            await self.db.log_system_event(
                event_type='startup',
                message=f'{self.config.app_name} v{self.config.version} started',
                source='system'
            )
        
        print(f"[SkyCast] Running - {self.config.app_name} v{self.config.version}")
        print("[SkyCast] Press Ctrl+C to stop")
        
        # Wait for shutdown signal
        try:
            await self._shutdown_event.wait()
        except asyncio.CancelledError:
            pass
        
        # Shutdown
        await self.shutdown()
    
    async def shutdown(self) -> None:
        """Graceful shutdown"""
        if not self._running:
            return
        
        print("[SkyCast] Shutting down...")
        self._running = False
        
        # Stop services
        if self.input_processor:
            await self.input_processor.stop()
        
        if self.weather_service:
            await self.weather_service.stop()
        
        if self.system_service:
            await self.system_service.stop()
        
        if self.display_manager:
            await self.display_manager.shutdown()
        
        # Graceful hardware shutdown
        if self.hardware:
            await self.hardware.shutdown()
        
        # Close database
        if self.db:
            await self.db.shutdown()
        
        # Signal shutdown complete
        self._shutdown_event.set()
        
        print("[SkyCast] Shutdown complete")
    
    def get_status(self) -> dict:
        """Get application status"""
        return {
            'running': self._running,
            'version': self.config.version,
            'profile': self.config.profile,
            'mock_hardware': self.config.sensor.mock_hardware,
            'components': {
                'hardware': self.hardware is not None,
                'database': self.db is not None and self.db._initialized,
                'display': self.display_manager is not None,
                'input': self.input_processor is not None,
                'weather': self.weather_service is not None,
                'system': self.system_service is not None,
            }
        }


def create_app(config: Optional[Settings] = None) -> WeatherStationApp:
    """Application factory function"""
    return WeatherStationApp(config)


async def main():
    """Main entry point"""
    app = create_app()
    
    # Setup signal handlers
    loop = asyncio.get_event_loop()
    
    def signal_handler():
        asyncio.create_task(app.shutdown())
    
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, signal_handler)
    
    # Run application
    await app.run()


if __name__ == '__main__':
    asyncio.run(main())
