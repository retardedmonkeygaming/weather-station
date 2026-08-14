"""
Event Bus for decoupled communication between components
Supports pub/sub pattern for state changes
"""

import asyncio
from enum import Enum, auto
from typing import Callable, Dict, List, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime


class EventType(Enum):
    """All event types in the system"""
    # Sensor events
    TEMPERATURE_UPDATED = auto()
    HUMIDITY_UPDATED = auto()
    PRESSURE_UPDATED = auto()
    AQI_UPDATED = auto()
    SENSOR_ERROR = auto()
    
    # Display events
    PAGE_CHANGED = auto()
    SETTINGS_ENTERED = auto()
    SETTINGS_EXITED = auto()
    SETTING_CHANGED = auto()
    BACKLIGHT_CHANGED = auto()
    
    # Alert events
    ALERT_TRIGGERED = auto()
    ALERT_CLEARED = auto()
    BUZZER_ACTIVATED = auto()
    BUZZER_DEACTIVATED = auto()
    
    # System events
    SYSTEM_STARTUP = auto()
    SYSTEM_SHUTDOWN = auto()
    SYSTEM_REBOOT = auto()
    FACTORY_RESET = auto()
    CONFIG_UPDATED = auto()
    
    # Data events
    DATA_LOGGED = auto()
    API_FETCHED = auto()
    
    # Discord events
    DISCORD_MESSAGE = auto()
    DISCORD_ALERT_SENT = auto()
    
    # Web events
    WEB_CLIENT_CONNECTED = auto()
    WEB_CLIENT_DISCONNECTED = auto()


@dataclass
class Event:
    """Event object passed through the bus"""
    type: EventType
    data: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)
    source: str = "unknown"


class EventBus:
    """
    Central event bus for decoupled communication.
    All components can publish and subscribe to events.
    """
    
    def __init__(self):
        self._subscribers: Dict[EventType, List[Callable]] = {}
        self._lock = asyncio.Lock()
    
    def subscribe(self, event_type: EventType, callback: Callable) -> None:
        """Subscribe to an event type"""
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        self._subscribers[event_type].append(callback)
    
    def unsubscribe(self, event_type: EventType, callback: Callable) -> None:
        """Unsubscribe from an event type"""
        if event_type in self._subscribers:
            self._subscribers[event_type].remove(callback)
    
    async def publish(self, event: Event) -> None:
        """Publish an event to all subscribers"""
        if event.type not in self._subscribers:
            return
        
        # Fire all callbacks asynchronously
        tasks = []
        for callback in self._subscribers[event.type]:
            try:
                if asyncio.iscoroutinefunction(callback):
                    tasks.append(callback(event))
                else:
                    callback(event)
            except Exception as e:
                # Log error but don't break other subscribers
                print(f"Event callback error: {e}")
        
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
    
    async def publish_simple(self, event_type: EventType, data: Optional[Dict[str, Any]] = None, source: str = "unknown") -> None:
        """Convenience method to publish simple events"""
        event = Event(type=event_type, data=data or {}, source=source)
        await self.publish(event)


# Global event bus instance
event_bus = EventBus()
