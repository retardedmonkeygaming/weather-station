"""LCD Display Manager with Hardware Diagnostics, Splash Screens, and Clean UI."""
import asyncio
import socket
from core.state import state
from display.widgets import WIDGET_MAP, render_widget_clock, render_widget_settings


class DisplayManager:
    def __init__(self, lcd_driver):
        self.lcd = lcd_driver

    async def run_diagnostics_and_boot(self, dht_sensor, buzzer):
        """Runs hardware self-test diagnostics followed by splash & loading screens."""
        self.lcd.clear()
        
        # 3 clear, properly timed startup beeps
        for _ in range(3):
            buzzer.beep(on_time=0.15, off_time=0.10, n=1)
            await asyncio.sleep(0.25)

        # --- STEP 1: HARDWARE DIAGNOSTICS ---
        self.lcd.write_lines("Diagnostics...", "Testing DHT11")
        await asyncio.sleep(1.0)
        
        dht_ok = False
        try:
            t, h = dht_sensor.read()
            if t is not None:
                dht_ok = True
        except Exception:
            dht_ok = False

        if dht_ok:
            self.lcd.write_lines("DHT11 Sensor:", "Status: OK")
            await state.update(dht_error=False)
        else:
            self.lcd.write_lines("DHT11 Sensor:", "Status: Error!")
            await state.update(dht_error=True)
            buzzer.beep(on_time=0.2, off_time=0.1, n=2)
        await asyncio.sleep(1.5)

        # Wi-Fi Connectivity Check
        self.lcd.write_lines("Diagnostics...", "Testing Wi-Fi")
        await asyncio.sleep(0.8)
        wifi_ok = False
        try:
            socket.create_connection(("1.1.1.1", 53), timeout=2)
            wifi_ok = True
        except OSError:
            wifi_ok = False

        if wifi_ok:
            self.lcd.write_lines("Wi-Fi Network:", "Status: OK")
            await state.update(wifi_error=False)
        else:
            self.lcd.write_lines("Wi-Fi Network:", "Status: Offline")
            await state.update(wifi_error=True)
            buzzer.beep(on_time=0.2, off_time=0.1, n=2)
        await asyncio.sleep(1.5)

        # --- STEP 2: SPLASH SCREEN 1 ---
        self.lcd.write_lines("    Weather     ", "    Station     ")
        await asyncio.sleep(2.0)

        # --- STEP 3: SPLASH SCREEN 2 & LOADING MATRIX ---
        loading_text = "Loading..."
        total_steps = 16
        for i in range(1, total_steps + 1):
            bar = "█" * i + " " * (total_steps - i)
            self.lcd.write_lines(loading_text, bar)
            await asyncio.sleep(0.08)

        await asyncio.sleep(0.4)
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