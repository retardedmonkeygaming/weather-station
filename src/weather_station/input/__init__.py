"""
Input module: Professional touch gesture recognition
State machine with proper debouncing and timing windows
"""

from .processor import InputProcessor, TouchGesture

__all__ = ['InputProcessor', 'TouchGesture']
