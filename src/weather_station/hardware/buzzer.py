async def run_loop(self):
        while True:
            # Audible Error Alert (Only beeps once when error starts)
            if state.dht_error and not state.last_dht_error:
                self.buzzer.error_alert()
                state.last_dht_error = True
            elif not state.dht_error:
                state.last_dht_error = False

            if self.sensors.is_pressed():
                start = time.time()
                # Light "Tick" for tactile feedback
                self.buzzer.beep(0.02) 
                while self.sensors.is_pressed():
                    await asyncio.sleep(0.05)
                
                duration = time.time() - start
                
                if duration > 3: # Long press to enter/exit settings
                    state.in_settings_mode = not state.in_settings_mode
                    state.settings_index = 1
                    self.buzzer.beep(0.1, repeats=2)
                else: # Short tap
                    if state.in_settings_mode:
                        state.settings_index = 1 if state.settings_index >= 10 else state.settings_index + 1
                    else:
                        state.current_page = 1 if state.current_page >= 6 else state.current_page + 1
            await asyncio.sleep(0.05)