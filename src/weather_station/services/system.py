"""
System Service
Monitors system health, handles alerts, manages shutdown/reboot
"""

import asyncio
import os
import shutil
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta


class SystemService:
    """
    System monitoring and management service.
    Handles alerts, system health, and graceful shutdown.
    """
    
    def __init__(
        self,
        state: Any,
        database_manager: Any,
        config: Any,
        hardware_interface: Any
    ):
        self.state = state
        self.db = database_manager
        self.config = config
        self.hardware = hardware_interface
        
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._start_time = datetime.utcnow()
    
    async def start(self) -> None:
        """Start system monitoring"""
        if self._running:
            return
        
        self._running = True
        self._task = asyncio.create_task(self._monitor_loop())
        
        # Update system status
        self.state.system.status.value = "running"
        self.state.system.start_time = self._start_time
        self.state.system.version = self.config.version if hasattr(self.config, 'version') else "3.0.0"
        
        # Log startup event
        if self.db and self.db._initialized:
            await self.db.log_system_event(
                event_type='startup',
                message='System started',
                source='system'
            )
        
        print("[SystemService] Started")
    
    async def stop(self) -> None:
        """Stop system monitoring"""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        print("[SystemService] Stopped")
    
    async def _monitor_loop(self) -> None:
        """Main monitoring loop"""
        while self._running:
            try:
                # Update uptime
                self.state.system.uptime_seconds = (datetime.utcnow() - self._start_time).total_seconds()
                
                # Update disk space
                try:
                    total, used, free = shutil.disk_usage("/")
                    self.state.system.disk_free_mb = free / (1024 * 1024)
                except Exception:
                    pass
                
                # Check for alert conditions
                await self._check_alerts()
                
                # Update system status
                self.state.system.status.value = "running"
                
                await asyncio.sleep(5)  # Check every 5 seconds
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"[SystemService] Monitor error: {e}")
                await asyncio.sleep(10)
    
    async def _check_alerts(self) -> None:
        """Check for alert conditions"""
        sensor = self.state.sensor
        
        if not sensor or sensor.sensor_error:
            return
        
        # Temperature alerts
        if sensor.temperature is not None:
            temp_high = self.config.alert.temp_high if hasattr(self.config, 'alert') else 30.0
            temp_low = self.config.alert.temp_low if hasattr(self.config, 'alert') else 5.0
            
            if sensor.temperature > temp_high:
                await self._trigger_alert('temp_high', f"High temp: {sensor.temperature:.1f}C", sensor.temperature, temp_high)
            
            if sensor.temperature < temp_low:
                await self._trigger_alert('temp_low', f"Low temp: {sensor.temperature:.1f}C", sensor.temperature, temp_low)
        
        # Humidity alerts
        if sensor.humidity is not None:
            humid_high = self.config.alert.humidity_high if hasattr(self.config, 'alert') else 80.0
            humid_low = self.config.alert.humidity_low if hasattr(self.config, 'alert') else 20.0
            
            if sensor.humidity > humid_high:
                await self._trigger_alert('humidity_high', f"High humidity: {sensor.humidity:.1f}%", sensor.humidity, humid_high)
            
            if sensor.humidity < humid_low:
                await self._trigger_alert('humidity_low', f"Low humidity: {sensor.humidity:.1f}%", sensor.humidity, humid_low)
        
        # AQI alerts
        if sensor.aqi is not None:
            aqi_threshold = self.config.alert.aqi_unhealthy if hasattr(self.config, 'alert') else 101
            
            if sensor.aqi >= aqi_threshold:
                await self._trigger_alert('aqi_unhealthy', f"Unhealthy AQI: {sensor.aqi}", sensor.aqi, aqi_threshold)
    
    async def _trigger_alert(
        self,
        alert_type: str,
        message: str,
        value: float,
        threshold: float,
        severity: str = 'warning'
    ) -> None:
        """Trigger an alert"""
        # Check if we're in quiet hours
        if self._is_quiet_hours():
            return
        
        # Add to state
        await self.state.add_alert(alert_type, message, severity)
        
        # Activate buzzer if configured
        buzzer_mode = self.config.alert.buzzer_mode if hasattr(self.config, 'alert') else 'ALERTS'
        if buzzer_mode in ('ALL', 'ALERTS'):
            self.state.alerts.buzzer_active = True
            # In real implementation, would activate buzzer
        
        # Log to database
        if self.db and self.db._initialized:
            await self.db.log_alert(
                alert_type=alert_type,
                message=message,
                severity=severity,
                value=value,
                threshold=threshold
            )
        
        print(f"[SystemService] Alert: {message}")
    
    def _is_quiet_hours(self) -> bool:
        """Check if currently in quiet hours"""
        now = datetime.utcnow()
        current_hour = now.hour
        
        quiet_start = self.config.alert.quiet_hours_start if hasattr(self.config, 'alert') else 22
        quiet_end = self.config.alert.quiet_hours_end if hasattr(self.config, 'alert') else 7
        
        if quiet_start > quiet_end:
            # Spans midnight (e.g., 22-7)
            return current_hour >= quiet_start or current_hour < quiet_end
        else:
            # Same day (e.g., 1-5)
            return quiet_start <= current_hour < quiet_end
    
    async def graceful_shutdown(self) -> None:
        """Perform graceful shutdown"""
        print("[SystemService] Initiating graceful shutdown")
        
        # Update status
        self.state.system.status.value = "shutting_down"
        
        # Clear display
        try:
            await self.hardware.clear()
            await self.hardware.set_backlight(False)
        except Exception:
            pass
        
        # Stop buzzer
        try:
            await self.hardware.stop()
        except Exception:
            pass
        
        # Log shutdown event
        if self.db and self.db._initialized:
            await self.db.log_system_event(
                event_type='shutdown',
                message='Graceful shutdown',
                source='system'
            )
        
        self._running = False
    
    async def reboot(self) -> None:
        """Initiate system reboot"""
        print("[SystemService] Initiating reboot")
        
        # Log event
        if self.db and self.db._initialized:
            await self.db.log_system_event(
                event_type='reboot',
                message='System reboot initiated',
                source='system'
            )
        
        # In real implementation, would call os.system('sudo reboot')
        # For now, just set flag
        self.state.system.status.value = "rebooting"
    
    async def factory_reset(self, keep_logs: bool = True) -> None:
        """Perform factory reset"""
        print("[SystemService] Performing factory reset")
        
        # Reset settings in database
        if self.db and self.db._initialized:
            await self.db.factory_reset_settings(keep_logs=keep_logs)
        
        # Log event
        if self.db and self.db._initialized:
            await self.db.log_system_event(
                event_type='factory_reset',
                message=f'Factory reset (keep_logs={keep_logs})',
                source='system'
            )
        
        # Reset state
        self.state.display.current_page = 0
        self.state.display.in_settings = False
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get system health status"""
        return {
            'status': self.state.system.status.value,
            'uptime_seconds': self.state.system.uptime_seconds,
            'disk_free_mb': self.state.system.disk_free_mb,
            'version': self.state.system.version,
            'active_alerts': len(self.state.alerts.alerts_active),
            'buzzer_active': self.state.alerts.buzzer_active,
            'quiet_hours': self._is_quiet_hours(),
        }
