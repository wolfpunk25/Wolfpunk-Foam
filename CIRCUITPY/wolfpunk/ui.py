# OLED (128x64 SH1106) and NeoPixel rendering. Kept deliberately dumb:
# code.py works out what everything should say/show, ui.py just draws it.

import displayio
import terminalio
from adafruit_display_text import label

WIDTH = 128
BOX = 14
GAP = 3
STEP_Y = 28
STEP_X0 = 3

# key layout on the 3x4 grid (row-major, keys 0-11)
KEY_STEPS = (0, 1, 2, 3, 4, 5, 6)
KEY_SHIFT_LEFT = 7
KEY_SHIFT_RIGHT = 8
KEY_PLAY = 9
KEY_VARY = 10
KEY_PAGE = 11

_DEGREE_HUE_STEP = 255 // 7


def _wheel(pos):
    pos = pos % 255
    if pos < 85:
        return (255 - pos * 3, pos * 3, 0)
    if pos < 170:
        pos -= 85
        return (0, 255 - pos * 3, pos * 3)
    pos -= 170
    return (pos * 3, 0, 255 - pos * 3)


def _scale_rgb(rgb, factor):
    return tuple(int(c * factor) for c in rgb)


class UI:
    def __init__(self, macropad):
        self.macropad = macropad
        macropad.pixels.brightness = 0.2

        self.group = displayio.Group()
        self.line1 = label.Label(terminalio.FONT, text="", color=0xFFFFFF, x=2, y=6)
        self.line2 = label.Label(terminalio.FONT, text="", color=0xFFFFFF, x=2, y=18)
        self.line3 = label.Label(terminalio.FONT, text="", color=0xFFFFFF, x=2, y=58)
        for l in (self.line1, self.line2, self.line3):
            self.group.append(l)

        self.step_bitmap = displayio.Bitmap(WIDTH, BOX, 2)
        self.step_palette = displayio.Palette(2)
        self.step_palette[0] = 0x000000
        self.step_palette[1] = 0xFFFFFF
        self.step_tile = displayio.TileGrid(
            self.step_bitmap, pixel_shader=self.step_palette, x=0, y=STEP_Y
        )
        self.group.append(self.step_tile)

        macropad.display.root_group = self.group

    def _draw_box(self, i, enabled, playhead):
        x0 = STEP_X0 + i * (BOX + GAP)
        bmp = self.step_bitmap
        for y in range(BOX):
            for x in range(BOX):
                border = x == 0 or y == 0 or x == BOX - 1 or y == BOX - 1
                bmp[x0 + x, y] = 1 if (enabled or border) else 0
        if playhead:
            cx, cy = x0 + BOX // 2, BOX // 2
            fill = 0 if enabled else 1
            for y in range(cy - 1, cy + 2):
                for x in range(cx - 1, cx + 2):
                    bmp[x, y] = fill

    def render(self, page_line, status_line, vary_line, pattern, playhead):
        self.line1.text = page_line[:21]
        self.line2.text = status_line[:21]
        self.line3.text = vary_line[:21]
        for i in range(7):
            self._draw_box(i, pattern.enabled[i], i == playhead)

    def leds(self, pattern, playhead, running, vary_on, shift_held):
        px = self.macropad.pixels
        for i in KEY_STEPS:
            hue = i * _DEGREE_HUE_STEP
            base = _wheel(hue)
            if i == playhead:
                px[i] = base
            elif pattern.enabled[i]:
                px[i] = _scale_rgb(base, 0.45)
            else:
                px[i] = _scale_rgb(base, 0.08)

        px[KEY_SHIFT_LEFT] = (60, 30, 0)
        px[KEY_SHIFT_RIGHT] = (60, 30, 0)
        px[KEY_PLAY] = (0, 90, 0) if running else (90, 0, 0)
        px[KEY_VARY] = (110, 0, 130) if vary_on else (20, 0, 25)
        px[KEY_PAGE] = (255, 255, 255) if shift_held else (60, 60, 60)
        px.show()
