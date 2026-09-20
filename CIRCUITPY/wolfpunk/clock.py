# Internal free-running clock. The real Liquid Foam has a mini-jack clock
# in/out; the MacroPad has no such jack, so this sends the same information
# out as USB MIDI clock (24 ppqn) instead - any DAW or MIDI box can still
# lock to Wolfpunk Foam the way the reviewer wanted to lock the Liquid Foam
# to a drum machine.

import time

PPQN = 24


def _clamp(v, lo, hi):
    return lo if v < lo else hi if v > hi else v


class Clock:
    def __init__(self, bpm=110, swing=0.0):
        self.bpm = bpm
        self.swing = swing  # 0.0-0.4, delays every other step
        self.running = False
        self._next_tick = 0.0
        self._next_step = 0.0
        self._tick_count = 0

    def set_bpm(self, bpm):
        self.bpm = _clamp(bpm, 40, 220)

    def set_swing(self, swing):
        self.swing = _clamp(swing, 0.0, 0.4)

    def start(self):
        now = time.monotonic()
        self.running = True
        self._tick_count = 0
        self._next_tick = now
        self._next_step = now

    def stop(self):
        self.running = False

    def _quarter_note_s(self):
        return 60.0 / self.bpm

    def _tick_interval_s(self):
        return self._quarter_note_s() / PPQN

    def due_ticks(self):
        """Yield True once per elapsed MIDI clock tick (24 ppqn)."""
        if not self.running:
            return 0
        now = time.monotonic()
        interval = self._tick_interval_s()
        count = 0
        while now >= self._next_tick:
            self._next_tick += interval
            self._tick_count += 1
            count += 1
        return count

    def due_step(self):
        """True once per pattern step (one quarter note, swung on odd steps)."""
        if not self.running:
            return False
        now = time.monotonic()
        if now < self._next_step:
            return False
        base = self._quarter_note_s()
        swing_add = base * self.swing if (self._tick_count // PPQN) % 2 else 0.0
        self._next_step = now + base + swing_add
        return True
