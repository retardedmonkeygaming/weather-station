"""
Hardware module: Abstraction layer for physical components
Supports real hardware and mock implementations for PC development
"""

from .interfaces import HardwareInterface, MockHardware, RealHardware, PIN_MAPPING

__all__ = ['HardwareInterface', 'MockHardware', 'RealHardware', 'PIN_MAPPING']
