"""
Settings Management System
Handles persistent configuration with validation, tracking, and import/export.
"""

import json
from datetime import datetime
from typing import Any, Dict, Optional, List
from dataclasses import dataclass
from enum import Enum


class SettingType(Enum):
    STRING = "string"
    INTEGER = "integer"
    FLOAT = "float"
    BOOLEAN = "boolean"
    SELECTION = "selection"


@dataclass
class SettingDefinition:
    """Defines a setting's metadata"""
    key: str
    name: str
    description: str
    setting_type: SettingType
    default_value: Any
    min_value: Optional[Any] = None
    max_value: Optional[Any] = None
    options: Optional[List[str]] = None  # For SELECTION type
    group: str = "General"
    requires_restart: bool = False
    
    def validate(self, value: Any) -> tuple[bool, str]:
        """Validate a value against this setting's constraints"""
        if value is None:
            return False, "Value cannot be None"
        
        try:
            if self.setting_type == SettingType.INTEGER:
                int_val = int(value)
                if self.min_value is not None and int_val < self.min_value:
                    return False, f"Value must be >= {self.min_value}"
                if self.max_value is not None and int_val > self.max_value:
                    return False, f"Value must be <= {self.max_value}"
            elif self.setting_type == SettingType.FLOAT:
                float_val = float(value)
                if self.min_value is not None and float_val < self.min_value:
                    return False, f"Value must be >= {self.min_value}"
                if self.max_value is not None and float_val > self.max_value:
                    return False, f"Value must be <= {self.max_value}"
            elif self.setting_type == SettingType.BOOLEAN:
                if isinstance(value, bool):
                    return True, ""
                if str(value).lower() not in ["true", "false", "1", "0", "yes", "no"]:
                    return False, "Must be a boolean value"
            elif self.setting_type == SettingType.SELECTION:
                if self.options and value not in self.options:
                    return False, f"Must be one of: {', '.join(self.options)}"
            
            return True, ""
        except (ValueError, TypeError) as e:
            return False, f"Invalid type: {str(e)}"


@dataclass
class SettingRecord:
    """A stored setting with metadata"""
    key: str
    value: Any
    last_changed_by: str  # "hardware", "web", "discord", "system"
    last_changed_at: datetime
    version: int = 1


class SettingsManager:
    """
    Manages all system settings with persistence, validation, and change tracking.
    Works with the DatabaseManager for storage.
    """
    
    def __init__(self):
        self._definitions: Dict[str, SettingDefinition] = {}
        self._values: Dict[str, SettingRecord] = {}
        self._db_manager = None
        self._initialized = False
        
        self._register_default_settings()
    
    def _register_default_settings(self):
        """Register all default system settings"""
        
        # Temperature & Units
        self.register(SettingDefinition(
            key="unit",
            name="Temperature Unit",
            description="Display temperature in Celsius or Fahrenheit",
            setting_type=SettingType.SELECTION,
            default_value="C",
            options=["C", "F"],
            group="Display"
        ))
        
        self.register(SettingDefinition(
            key="temp_offset",
            name="Temperature Offset",
            description="Calibration offset for DHT sensor",
            setting_type=SettingType.FLOAT,
            default_value=0.0,
            min_value=-10.0,
            max_value=10.0,
            group="Calibration"
        ))
        
        self.register(SettingDefinition(
            key="temp_high_threshold",
            name="High Temperature Alert",
            description="Trigger alert when indoor temp exceeds this",
            setting_type=SettingType.FLOAT,
            default_value=32.0,
            min_value=0.0,
            max_value=50.0,
            group="Alerts"
        ))
        
        self.register(SettingDefinition(
            key="temp_low_threshold",
            name="Low Temperature Alert",
            description="Trigger alert when indoor temp falls below this",
            setting_type=SettingType.FLOAT,
            default_value=10.0,
            min_value=-10.0,
            max_value=30.0,
            group="Alerts"
        ))
        
        # Buzzer & Audio
        self.register(SettingDefinition(
            key="buzzer_mode",
            name="Buzzer Mode",
            description="Control when buzzer sounds",
            setting_type=SettingType.SELECTION,
            default_value="ALL",
            options=["ALL", "ERR", "MUTE"],
            group="Audio"
        ))
        
        # Display
        self.register(SettingDefinition(
            key="screen_on",
            name="Screen Power",
            description="Enable or disable LCD display",
            setting_type=SettingType.BOOLEAN,
            default_value=True,
            group="Display"
        ))
        
        self.register(SettingDefinition(
            key="auto_scroll_interval",
            name="Auto-Scroll Interval",
            description="Seconds between page rotations (0 = disabled)",
            setting_type=SettingType.INTEGER,
            default_value=0,
            min_value=0,
            max_value=60,
            group="Display"
        ))
        
        # Alarm
        self.register(SettingDefinition(
            key="alarm_enabled",
            name="Daily Alarm",
            description="Enable daily alarm",
            setting_type=SettingType.BOOLEAN,
            default_value=False,
            group="Alarm"
        ))
        
        self.register(SettingDefinition(
            key="alarm_hour",
            name="Alarm Hour",
            description="Hour for daily alarm (0-23)",
            setting_type=SettingType.INTEGER,
            default_value=17,
            min_value=0,
            max_value=23,
            group="Alarm"
        ))
        
        self.register(SettingDefinition(
            key="alarm_minute",
            name="Alarm Minute",
            description="Minute for daily alarm (0-59)",
            setting_type=SettingType.INTEGER,
            default_value=0,
            min_value=0,
            max_value=59,
            group="Alarm"
        ))
        
        # Intervals
        self.register(SettingDefinition(
            key="api_fetch_interval",
            name="API Fetch Interval",
            description="Minutes between weather API requests",
            setting_type=SettingType.INTEGER,
            default_value=10,
            min_value=1,
            max_value=60,
            group="Data"
        ))
        
        self.register(SettingDefinition(
            key="log_interval",
            name="Database Log Interval",
            description="Minutes between database log entries",
            setting_type=SettingType.INTEGER,
            default_value=15,
            min_value=1,
            max_value=120,
            group="Data"
        ))
        
        # Location
        self.register(SettingDefinition(
            key="latitude",
            name="Latitude",
            description="Geographic latitude for weather data",
            setting_type=SettingType.STRING,
            default_value="29.325390",
            group="Location"
        ))
        
        self.register(SettingDefinition(
            key="longitude",
            name="Longitude",
            description="Geographic longitude for weather data",
            setting_type=SettingType.STRING,
            default_value="48.019562",
            group="Location"
        ))
        
        # Quiet Hours
        self.register(SettingDefinition(
            key="quiet_hours_start",
            name="Quiet Hours Start",
            description="Hour when quiet mode begins (0-23)",
            setting_type=SettingType.INTEGER,
            default_value=23,
            min_value=0,
            max_value=23,
            group="Audio"
        ))
        
        self.register(SettingDefinition(
            key="quiet_hours_end",
            name="Quiet Hours End",
            description="Hour when quiet mode ends (0-23)",
            setting_type=SettingType.INTEGER,
            default_value=7,
            min_value=0,
            max_value=23,
            group="Audio"
        ))
        
        # Discord
        self.register(SettingDefinition(
            key="discord_enabled",
            name="Discord Bot",
            description="Enable Discord bot integration",
            setting_type=SettingType.BOOLEAN,
            default_value=False,
            group="Discord"
        ))
        
        self.register(SettingDefinition(
            key="discord_natural_language",
            name="Discord Natural Language",
            description="Allow natural language queries on Discord",
            setting_type=SettingType.BOOLEAN,
            default_value=True,
            group="Discord"
        ))
    
    def register(self, definition: SettingDefinition) -> None:
        """Register a new setting definition"""
        self._definitions[definition.key] = definition
        if definition.key not in self._values:
            self._values[definition.key] = SettingRecord(
                key=definition.key,
                value=definition.default_value,
                last_changed_by="system",
                last_changed_at=datetime.now()
            )
    
    def set_db_manager(self, db_manager) -> None:
        """Set the database manager for persistence"""
        self._db_manager = db_manager
    
    async def initialize(self) -> None:
        """Load settings from database"""
        if self._db_manager is None:
            raise RuntimeError("Database manager not set")
        
        await self._db_manager.ensure_tables()
        await self._load_from_db()
        self._initialized = True
    
    async def _load_from_db(self) -> None:
        """Load all settings from database"""
        if self._db_manager is None:
            return
        
        rows = await self._db_manager.fetch_all("SELECT key, value, changed_by, changed_at FROM settings")
        for row in rows:
            key, value, changed_by, changed_at = row
            if key in self._definitions:
                # Convert value to appropriate type
                definition = self._definitions[key]
                typed_value = self._convert_value(value, definition.setting_type)
                
                self._values[key] = SettingRecord(
                    key=key,
                    value=typed_value,
                    last_changed_by=changed_by or "system",
                    last_changed_at=datetime.fromisoformat(changed_at) if changed_at else datetime.now()
                )
    
    def _convert_value(self, value: str, setting_type: SettingType) -> Any:
        """Convert string value from DB to appropriate type"""
        if value is None:
            return None
        
        try:
            if setting_type == SettingType.INTEGER:
                return int(value)
            elif setting_type == SettingType.FLOAT:
                return float(value)
            elif setting_type == SettingType.BOOLEAN:
                return str(value).lower() in ["true", "1", "yes"]
            else:
                return str(value)
        except (ValueError, TypeError):
            return None
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get a setting value"""
        if key in self._values:
            return self._values[key].value
        if key in self._definitions:
            return self._definitions[key].default_value
        return default
    
    def get_typed(self, key: str) -> tuple[Any, SettingType]:
        """Get setting value with its type"""
        if key in self._values:
            record = self._values[key]
            return record.value, self._definitions[key].setting_type
        if key in self._definitions:
            defn = self._definitions[key]
            return defn.default_value, defn.setting_type
        return default, None
    
    async def set(self, key: str, value: Any, changed_by: str = "unknown") -> tuple[bool, str]:
        """
        Set a setting value with validation.
        
        Returns:
            Tuple of (success, error_message)
        """
        if key not in self._definitions:
            return False, f"Unknown setting: {key}"
        
        definition = self._definitions[key]
        valid, error = definition.validate(value)
        if not valid:
            return False, error
        
        # Update in memory
        self._values[key] = SettingRecord(
            key=key,
            value=value,
            last_changed_by=changed_by,
            last_changed_at=datetime.now()
        )
        
        # Persist to database
        if self._db_manager:
            await self._db_manager.execute(
                """INSERT INTO settings (key, value, changed_by, changed_at) 
                   VALUES (?, ?, ?, ?)
                   ON CONFLICT(key) DO UPDATE SET 
                   value=excluded.value, 
                   changed_by=excluded.changed_by,
                   changed_at=excluded.changed_at""",
                (key, str(value), changed_by, datetime.now().isoformat())
            )
        
        return True, ""
    
    def get_group(self, group_name: str) -> List[SettingDefinition]:
        """Get all settings in a group"""
        return [d for d in self._definitions.values() if d.group == group_name]
    
    def get_groups(self) -> List[str]:
        """Get all unique setting groups"""
        return list(set(d.group for d in self._definitions.values()))
    
    def get_all_definitions(self) -> Dict[str, SettingDefinition]:
        """Get all setting definitions"""
        return self._definitions.copy()
    
    def get_all_values(self) -> Dict[str, Any]:
        """Get all current setting values"""
        return {k: v.value for k, v in self._values.items()}
    
    async def export_json(self) -> str:
        """Export all settings as JSON"""
        export_data = {
            "exported_at": datetime.now().isoformat(),
            "settings": {}
        }
        
        for key, record in self._values.items():
            export_data["settings"][key] = {
                "value": record.value,
                "changed_by": record.last_changed_by,
                "changed_at": record.last_changed_at.isoformat()
            }
        
        return json.dumps(export_data, indent=2)
    
    async def import_json(self, json_str: str, changed_by: str = "import") -> tuple[bool, str]:
        """Import settings from JSON"""
        try:
            data = json.loads(json_str)
            settings_data = data.get("settings", {})
            
            for key, setting_data in settings_data.items():
                if key in self._definitions:
                    value = setting_data.get("value")
                    valid, error = self._definitions[key].validate(value)
                    if valid:
                        await self.set(key, value, changed_by)
            
            return True, ""
        except json.JSONDecodeError as e:
            return False, f"Invalid JSON: {e}"
        except Exception as e:
            return False, f"Import failed: {e}"
    
    async def reset_to_defaults(self, changed_by: str = "system") -> None:
        """Reset all settings to their defaults"""
        for key, definition in self._definitions.items():
            await self.set(key, definition.default_value, changed_by)
