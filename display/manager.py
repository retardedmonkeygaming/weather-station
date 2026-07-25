"""LCD Display Manager & Loading Sequence Routine."""
import asyncio
from core.state import state
from display.widgets import WIDGET_MAP, render_widget_clock, render_widget_settings


class DisplayManager:
    def __init__(self, lcd_driver):
        self.lcd = lcd_driver

    async def run_loading_sequence(self, buzzer):
        """Displays boot screen with loading bar and 3 distinct beeps."""
        self.lcd.clear()
        
        # 3 distinct startup beeps
        for _ in range(3):
            buzzer.beep(on_time=0.08, off_time=0.08, n=1)
            await asyncio.sleep(0.15)
            
        loading_text = "WEATHER STATION"
        total_steps = 16
        
        for i in range(1, total_steps + 1):
            bar = "█" * i + " " * (total_steps - i)
            self.lcd.write_lines(loading_text.center(16), bar)
            await asyncio.sleep(0.08)
            
        await asyncio.sleep(0.5)
        self.lcd.clear()

    async def update_display(self):
        snap = state.get_snapshot_sync()
        
        if snap.in_settings_mode:
            line1, line2 = render_widget_settings(snap)
        else:
            render_fn = WIDGET_MAP.get(snap.current_page, render_widget_clock)
            line1, line2 = render_fn(snap)
        
        self.lcd.write_lines(line1, line2)
        await state.update(last_lcd_rendered_text=[line1, line2])