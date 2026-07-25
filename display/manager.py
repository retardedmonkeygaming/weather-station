"""LCD Display Manager Async Task."""
from core.state import state
from display.widgets import WIDGET_MAP, render_widget_indoor

class DisplayManager:
    def __init__(self, lcd_driver):
        self.lcd = lcd_driver

    async def update_display(self):
        snap = state.get_snapshot_sync()
        widget_key = state.custom_lcd_pages.get(snap.current_page, "widget_indoor")
        render_fn = WIDGET_MAP.get(widget_key, render_widget_indoor)
        
        line1, line2 = render_fn(snap)
        self.lcd.write_lines(line1, line2)
        await state.update(last_lcd_rendered_text=[line1, line2])