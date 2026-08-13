"""
Professional Touch Input Processor
State machine with proper debouncing, timing windows, and gesture recognition

Gestures:
- Single tap: Next page / next setting
- Double tap: Previous page (optional)
- Triple tap: Enter/leave settings
- Short hold (0.8s): Adjust value in settings
- Medium hold (3s): Factory reset confirmation
- Long hold (5s): Reboot confirmation
- Extra long hold (10s): Shutdown confirmation
"""

import asyncio
from enum import Enum, auto
from typing import Optional, Callable, Dict, Any, List
from datetime import datetime
from dataclasses import dataclass


class TouchGesture(Enum):
    """Recognized touch gestures"""
    TAP = auto()           # Single tap
    DOUBLE_TAP = auto()    # Double tap
    TRIPLE_TAP = auto()    # Triple tap - enter/leave settings
    SHORT_HOLD = auto()    # 0.8s - adjust value
    MEDIUM_HOLD = auto()   # 3s - factory reset
    LONG_HOLD = auto()     # 5s - reboot
    EXTRA_LONG_HOLD = auto()  # 10s - shutdown


@dataclass
class GestureConfig:
    """Configuration for gesture timing"""
    debounce_ms: int = 150          # Debounce period to prevent false triggers
    tap_timeout_ms: int = 350       # Max time between taps for multi-tap
    short_hold_ms: int = 800        # Short hold threshold
    medium_hold_ms: int = 3000      # Medium hold threshold
    long_hold_ms: int = 5000        # Long hold threshold
    extra_long_hold_ms: int = 10000 # Extra long hold threshold


class InputProcessor:
    """
    Professional touch input processor with state machine.
    Handles debouncing, gesture recognition, and callback dispatch.
    """
    
    def __init__(
        self,
        hardware_interface,
        config: Optional[GestureConfig] = None,
        on_gesture: Optional[Callable[[TouchGesture], Any]] = None
    ):
        self.hardware = hardware_interface
        self.config = config or GestureConfig()
        self.on_gesture = on_gesture
        
        # State machine
        self._state = 'IDLE'  # IDLE, TOUCHED, WAITING_FOR_RELEASE, HOLDING
        self._touch_start_time: Optional[datetime] = None
        self._tap_count = 0
        self._last_tap_time: Optional[datetime] = None
        self._hold_callback_called = False
        self._running = False
        self._task: Optional[asyncio.Task] = None
        
        # Callbacks for specific gestures
        self._gesture_callbacks: Dict[TouchGesture, List[Callable]] = {}
        
        # Statistics
        self.total_gestures = 0
        self.gesture_counts = {g: 0 for g in TouchGesture}
    
    def register_gesture_callback(
        self,
        gesture: TouchGesture,
        callback: Callable[[TouchGesture], Any]
    ) -> None:
        """Register a callback for a specific gesture"""
        if gesture not in self._gesture_callbacks:
            self._gesture_callbacks[gesture] = []
        self._gesture_callbacks[gesture].append(callback)
    
    async def start(self) -> None:
        """Start the input processing loop"""
        if self._running:
            return
        
        self._running = True
        self._task = asyncio.create_task(self._process_loop())
        print("[InputProcessor] Started")
    
    async def stop(self) -> None:
        """Stop the input processing loop"""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        print("[InputProcessor] Stopped")
    
    async def _process_loop(self) -> None:
        """Main input processing loop"""
        while self._running:
            try:
                # Read touch sensor
                is_touched = await self.hardware.read_touch()
                
                # Apply debouncing
                if is_touched:
                    await self._handle_touch()
                else:
                    await self._handle_release()
                
                # Small delay to prevent CPU spinning
                await asyncio.sleep(0.02)  # 20ms polling
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"[InputProcessor] Error: {e}")
                await asyncio.sleep(0.1)
    
    async def _handle_touch(self) -> None:
        """Handle touch event"""
        now = datetime.utcnow()
        
        if self._state == 'IDLE':
            # New touch detected
            self._state = 'TOUCHED'
            self._touch_start_time = now
            
        elif self._state == 'WAITING_FOR_RELEASE':
            # Still waiting for release, check if it's a new tap
            if self._touch_start_time:
                elapsed = (now - self._touch_start_time).total_seconds() * 1000
                if elapsed < self.config.debounce_ms:
                    # Ignore, still debouncing
                    return
            
            # Check if this could be a multi-tap
            if self._last_tap_time:
                since_last_tap = (now - self._last_tap_time).total_seconds() * 1000
                if since_last_tap < self.config.tap_timeout_ms:
                    # This is another tap
                    self._tap_count += 1
                    self._touch_start_time = now
                    return
            
            # Start of a new potential hold
            self._state = 'HOLDING'
            self._touch_start_time = now
            self._hold_callback_called = False
    
    async def _handle_release(self) -> None:
        """Handle touch release event"""
        if self._state in ('IDLE', 'TOUCHED'):
            return
        
        now = datetime.utcnow()
        
        if self._state == 'HOLDING':
            # Was holding, check duration
            if self._touch_start_time:
                hold_duration = (now - self._touch_start_time).total_seconds() * 1000
                await self._process_hold(hold_duration)
        
        elif self._state == 'TOUCHED':
            # Was a tap
            self._tap_count += 1
            self._last_tap_time = now
            
            # Wait briefly to see if more taps come
            await asyncio.sleep(self.config.tap_timeout_ms / 1000.0)
            
            # Check if more taps came during wait
            current_state = self._state
            if self._state == 'TOUCHED':  # No additional taps
                await self._process_taps(self._tap_count)
            
            # Reset tap state
            self._tap_count = 0
            self._state = 'IDLE'
            return
        
        self._state = 'IDLE'
        self._touch_start_time = None
    
    async def _process_taps(self, count: int) -> None:
        """Process tap gesture based on count"""
        gesture = None
        
        if count == 1:
            gesture = TouchGesture.TAP
        elif count == 2:
            gesture = TouchGesture.DOUBLE_TAP
        elif count >= 3:
            gesture = TouchGesture.TRIPLE_TAP
        
        if gesture:
            await self._dispatch_gesture(gesture)
    
    async def _process_hold(self, duration_ms: float) -> None:
        """Process hold gesture based on duration"""
        gesture = None
        
        if duration_ms >= self.config.extra_long_hold_ms:
            gesture = TouchGesture.EXTRA_LONG_HOLD
        elif duration_ms >= self.config.long_hold_ms:
            gesture = TouchGesture.LONG_HOLD
        elif duration_ms >= self.config.medium_hold_ms:
            gesture = TouchGesture.MEDIUM_HOLD
        elif duration_ms >= self.config.short_hold_ms:
            gesture = TouchGesture.SHORT_HOLD
        
        if gesture:
            await self._dispatch_gesture(gesture)
    
    async def _dispatch_gesture(self, gesture: TouchGesture) -> None:
        """Dispatch gesture to callbacks"""
        self.total_gestures += 1
        self.gesture_counts[gesture] = self.gesture_counts.get(gesture, 0) + 1
        
        print(f"[InputProcessor] Gesture: {gesture.name}")
        
        # Call main callback
        if self.on_gesture:
            try:
                result = self.on_gesture(gesture)
                if asyncio.iscoroutine(result):
                    await result
            except Exception as e:
                print(f"[InputProcessor] Callback error: {e}")
        
        # Call specific callbacks
        if gesture in self._gesture_callbacks:
            for callback in self._gesture_callbacks[gesture]:
                try:
                    result = callback(gesture)
                    if asyncio.iscoroutine(result):
                        await result
                except Exception as e:
                    print(f"[InputProcessor] Specific callback error: {e}")
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get input statistics"""
        return {
            'total_gestures': self.total_gestures,
            'gesture_counts': {g.name: c for g, c in self.gesture_counts.items()},
            'current_state': self._state,
        }
