"""
Event System for Cross-Component Communication
Allows components to subscribe to and publish events without tight coupling.
"""

import asyncio
from datetime import datetime
from enum import Enum, auto
from typing import Callable, Any, Dict, List
from dataclasses import dataclass


class EventType(Enum):
    """All possible event types in the system"""
    # Sensor events
    SENSOR_UPDATED = auto()
    DHT_ERROR = auto()
    DHT_RECOVERED = auto()
    
    # Weather events
    WEATHER_FETCHED = auto()
    WEATHER_ERROR = auto()
    AQI_UPDATED = auto()
    
    # Alert events
    ALERT_TRIGGERED = auto()
    ALERT_DISMISSED = auto()
    ALARM_RINGING = auto()
    ALARM_DISMISSED = auto()
    
    # Setting events
    SETTING_CHANGED = auto()
    SETTINGS_LOADED = auto()
    SETTINGS_RESET = auto()
    
    # Display events
    PAGE_CHANGED = auto()
    SETTINGS_MODE_ENTERED = auto()
    SETTINGS_MODE_EXITED = auto()
    SCREEN_TOGGLED = auto()
    
    # System events
    SYSTEM_BOOT = auto()
    SYSTEM_SHUTDOWN = auto()
    SYSTEM_REBOOT = auto()
    HARDWARE_DIAGNOSTIC_COMPLETE = auto()
    
    # Database events
    LOG_ENTRY_ADDED = auto()
    
    # Location events
    LOCATION_CHANGED = auto()


@dataclass
class Event:
    """Represents an event with metadata"""
    event_type: EventType
    timestamp: datetime
    data: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.data is None:
            self.data = {}


class EventSystem:
    """
    Central event bus for the weather station.
    Components can subscribe to events and publish events asynchronously.
    """
    
    def __init__(self):
        self._subscribers: Dict[EventType, List[Callable]] = {}
        self._lock = asyncio.Lock()
    
    def subscribe(self, event_type: EventType, callback: Callable) -> None:
        """
        Subscribe to a specific event type.
        
        Args:
            event_type: The type of event to listen for
            callback: Async function to call when event occurs
        """
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        self._subscribers[event_type].append(callback)
    
    def unsubscribe(self, event_type: EventType, callback: Callable) -> None:
        """Remove a subscription"""
        if event_type in self._subscribers:
            try:
                self._subscribers[event_type].remove(callback)
            except ValueError:
                pass
    
    async def publish(self, event_type: EventType, data: Dict[str, Any] = None) -> None:
        """
        Publish an event to all subscribers.
        
        Args:
            event_type: The type of event
            data: Optional data payload
        """
        event = Event(event_type=event_type, timestamp=datetime.now(), data=data or {})
        
        if event_type not in self._subscribers:
            return
        
        # Fire all callbacks concurrently
        tasks = []
        for callback in self._subscribers[event_type]:
            try:
                if asyncio.iscoroutinefunction(callback):
                    tasks.append(callback(event))
                else:
                    # Run sync functions in executor
                    tasks.append(asyncio.get_event_loop().run_in_executor(None, callback, event))
            except Exception as e:
                print(f"Error preparing event callback: {e}")
        
        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            for result in results:
                if isinstance(result, Exception):
                    print(f"Event callback error: {result}")
    
    def clear(self) -> None:
        """Clear all subscriptions"""
        self._subscribers.clear()
    
    def get_subscriber_count(self, event_type: EventType) -> int:
        """Get number of subscribers for an event type"""
        return len(self._subscribers.get(event_type, []))
