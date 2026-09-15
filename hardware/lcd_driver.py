"""
lcd_driver.py — 1602A LCD design system.

Encapsulates:
    * adafruit_character_lcd Character_LCD_Mono initialization (4-bit mode,
      BCM pins from config.PIN).
    * Custom character (CGRAM) management for slots \\x00-\\x07. All eight
      glyphs are burned ONCE at startup under a thread-safe lock and are
      NEVER re-created at runtime — HD44780 CGRAM rewrites bank all slots and
      would glitch any in-flight frame.
    * STRICT 16x2 geometry: every write is auto-padded/centered then
      auto-clipped so rows never exceed 16 chars (no HD44780 wrap-around).
    * Safe mock backend for desktop simulation: frames are stored in memory,
      logged as [SIMULATED], and mirrored to the web dashboard unchanged.
"""

from __future__ import annotations

import asyncio
import logging
import threading
from typing import List, Optional, Sequence, Tuple

import config
from utils import center_text, clip_text, pad_text

log = logging.getLogger("weather.lcd")


# ---------------------------------------------------------------------------
# Mock backend (desktop / CI)
# ---------------------------------------------------------------------------

class MockLCD:
    """In-memory stand-in mirroring the adafruit Character_LCD_Mono API."""

    def __init__(self, columns: int = config.LCD_COLUMNS,
                 rows: int = config.LCD_ROWS) -> None:
        self.columns = columns
        self.rows = rows
        self._lines: List[str] = ["", ""]
        self.custom_chars: dict = {}

    @property
    def message(self) -> str:
        return "\n".join(self._lines)

    @message.setter
    def message(self, value: str) -> None:
        self._lines = value.split("\n")[: self.rows]

    def clear(self) -> None:
        self._lines = ["", ""]

    def create_char(self, location: int, pattern: Sequence[int]) -> None:
        self.custom_chars[location] = list(pattern)

    def snapshot(self) -> List[str]:
        return list(self._lines)


# ---------------------------------------------------------------------------
# Real backend (Raspberry Pi)
# ---------------------------------------------------------------------------

def _build_real_lcd():
    """Construct the adafruit Character_LCD_Mono; raises when not on a Pi."""
    import board
    import digitalio
    from adafruit_character_lcd.character_lcd import Character_LCD_Mono

    pins = config.PIN
    return Character_LCD_Mono(
        digitalio.DigitalInOut(getattr(board, f"D{pins.LCD_RS}")),
        digitalio.DigitalInOut(getattr(board, f"D{pins.LCD_EN}")),
        digitalio.DigitalInOut(getattr(board, f"D{pins.LCD_D4}")),
        digitalio.DigitalInOut(getattr(board, f"D{pins.LCD_D5}")),
        digitalio.DigitalInOut(getattr(board, f"D{pins.LCD_D6}")),
        digitalio.DigitalInOut(getattr(board, f"D{pins.LCD_D7}")),
        columns=config.LCD_COLUMNS,
        lines=config.LCD_ROWS,
    )


# ---------------------------------------------------------------------------
# Design-system facade
# ---------------------------------------------------------------------------

class LCD:
    """Geometry-safe facade over the physical or mock LCD backend.

    Every render path funnels through `_fit_row`, guaranteeing that a logical
    row never exceeds `columns` chars — the HD44780 has no soft-wrap and will
    jump to unseen DDRAM addresses when a row overflows.
    """

    def __init__(self) -> None:
        self.columns = config.LCD_COLUMNS
        self.rows = config.LCD_ROWS
        self._char_lock = threading.Lock()   # serialize the startup burn
        self._render_lock = asyncio.Lock()   # serialize async render cycles
        self._backend = self._make_backend()
        self._contrast_device = None         # optional PWM contrast pin
        self._setup_contrast_pin()
        self._burn_glyphs_once()

    def _setup_contrast_pin(self) -> None:
        """Optional PWM contrast control for Guest Mode dimming.

        Wire the 1602A V0 pin through an RC filter to the BCM pin given by
        LCD_CONTRAST_PIN (env/.env). Without it, dimming degrades to a
        backlight toggle — data stays visible either way.
        """
        pin = config.PIN.LCD_CONTRAST_PIN
        if not config.IS_PI or pin is None:
            return
        try:
            from gpiozero import PWMOutputDevice
            self._contrast_device = PWMOutputDevice(pin)
            self._contrast_device.value = config.LCD_CONTRAST_FULL
            log.info("LCD contrast PWM active on BCM %s", pin)
        except Exception:
            log.exception("Contrast PWM init failed on BCM %s", pin)

    # -- backend selection ---------------------------------------------------

    def _make_backend(self):
        if config.IS_PI:
            try:
                return _build_real_lcd()
            except Exception:
                log.exception("GPIO LCD init failed — falling back to mock")
                return MockLCD(self.columns, self.rows)
        log.info("Desktop environment — LCD running in SIMULATED mock mode")
        return MockLCD(self.columns, self.rows)

    def _burn_glyphs_once(self) -> None:
        """Upload ALL custom glyphs (\\x00-\\x07) exactly once, at startup.

        This is the ONLY place create_char is ever called. The lock makes the
        burn atomic with respect to any concurrent reader of the glyph table.
        """
        with self._char_lock:
            for slot, bitmap in config.CUSTOM_CHARACTERS.items():
                try:
                    self._backend.create_char(slot, bitmap)
                except Exception:
                    log.exception("Failed to burn glyph 0x%02X", slot)
        log.info("Burned %d custom glyphs (one-shot)", len(config.CUSTOM_CHARACTERS))

    # -- geometry helpers (STRICT 16x2) ---------------------------------------

    def _fit_row(self, text: str, width: Optional[int] = None,
                 align: str = "left") -> str:
        """Normalize a row to exactly `columns` chars (utils helpers).

        clip_text guarantees no HD44780 wrap; pad/center guarantee exact
        width so the simulator and the panel render byte-identical frames.
        """
        width = width or self.columns
        text = clip_text(text, width)
        if align == "center":
            return center_text(text, width)
        if align == "right":
            return text.rjust(width)
        return pad_text(text, width)

    def fit_text(self, text: str, align: str = "left") -> str:
        """Public one-row fitting utility (widgets/tests/designer)."""
        return self._fit_row(text, align=align)

    def center_text(self, text: str) -> str:
        """Center a single row inside 16 columns, clipped if needed."""
        return self._fit_row(text, align="center")

    def format_two_rows(self, line1: str, line2: str,
                        align: str = "left") -> Tuple[str, str]:
        """Fit both logical rows for a full-frame render."""
        return (self._fit_row(line1, align=align),
                self._fit_row(line2, align=align))

    # -- rendering -------------------------------------------------------------

    async def render(self, line1: str, line2: str,
                     align: str = "left", clear_first: bool = False) -> None:
        """Async-safe two-row frame render (geometry enforced)."""
        async with self._render_lock:
            row_a = self._fit_row(line1, align=align)
            row_b = self._fit_row(line2, align=align)
            payload = f"{row_a}\n{row_b}"
            try:
                if clear_first:
                    self._backend.clear()
                self._backend.message = payload
                if self.is_mock:
                    log.debug("[SIMULATED] LCD << %r", payload)
                else:
                    log.debug("LCD << %r", payload)
            except Exception:
                log.exception("LCD render failed")

    async def clear(self) -> None:
        async with self._render_lock:
            try:
                self._backend.clear()
            except Exception:
                log.exception("LCD clear failed")

    # -- Guest Mode dimming ----------------------------------------------------

    def set_dimmed(self, dimmed: bool) -> None:
        """Lower contrast (Guest Mode) while keeping the data on screen.

        With a contrast PWM pin: duty drops to LCD_CONTRAST_DIM. Without one:
        the backlight is cycled as a visible fallback; data still renders.
        The mock backend records the dim level for the web simulator.
        """
        level = config.LCD_CONTRAST_DIM if dimmed else config.LCD_CONTRAST_FULL
        if self._contrast_device is not None:
            try:
                self._contrast_device.value = level
            except Exception:
                log.exception("Contrast PWM write failed")
        else:
            try:
                if dimmed and hasattr(self._backend, "backlight_enabled"):
                    self._backend.backlight_enabled = False
                elif not dimmed and hasattr(self._backend, "backlight_enabled"):
                    self._backend.backlight_enabled = True
            except Exception:
                pass
        self._dim_level = level
        log.info("LCD %s (contrast level %.2f)",
                 "dimmed" if dimmed else "restored", level)

    @property
    def dim_level(self) -> float:
        """Current contrast duty (web UI / mock introspection)."""
        return getattr(self, "_dim_level", config.LCD_CONTRAST_FULL)

    # -- introspection ----------------------------------------------------------

    def snapshot(self) -> List[str]:
        """Current physical rows (mock backends only)."""
        if isinstance(self._backend, MockLCD):
            return self._backend.snapshot()
        return ["", ""]

    @property
    def is_mock(self) -> bool:
        return isinstance(self._backend, MockLCD)


# Module-level singleton
lcd = LCD()


def get_lcd() -> LCD:
    return lcd
