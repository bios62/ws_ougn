# SPDX-FileCopyrightText: 2021 Kattni Rembor for Adafruit Industries
# SPDX-License-Identifier: MIT
"""CircuitPython blink example for built-in NeoPixel LED"""
import time
import board
import neopixel
import feathers3

VERSION='V 1.0 090525'
# Color and blink

AZURE=(0,255,255)
YELLOW=(255,255,0)
ORANGE=(255,64,0)
BLUE=(0,0,255)
WHITE=(255,255,255)
GREEN=(0,255,0)
RED=(255,0,0)
PURPLE=(255,0,255)
DARK=(0,0,0)
pixel = neopixel.NeoPixel(board.NEOPIXEL, 1)
print("Blink verification program, Version: "+VERSION)
while True:
    pixel.fill(RED)
    time.sleep(0.5)
    pixel.fill(GREEN)
    time.sleep(0.5)
    pixel.fill(BLUE)
    time.sleep(0.5)
