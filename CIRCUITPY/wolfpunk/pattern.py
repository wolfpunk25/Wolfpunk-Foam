# The pitch sequencer: 7 steps, one per step key, each holding an
# enabled/disabled gate and a scale degree (0-6) - the same shape as the
# real Liquid Foam's 3-bit pitch DAC, which only ever produces 7 distinct
# pitches from its gate combinations.
#
# `shift()` stands in for the X/Y controls that nudge the gate pattern
# around; `Vary` stands in for Sequencer B, which the manual describes as
# quietly re-combining gates onto the filter/LFO/drive knobs every lap.

import random

STEPS = 7


def _clamp(v, lo, hi):
    return lo if v < lo else hi if v > hi else v


class Pattern:
    def __init__(self):
        self.enabled = [True] * STEPS
        self.degree = list(range(STEPS))  # ascending run through the scale
        self.position = 0

    def advance(self):
        self.position = (self.position + 1) % STEPS
        return self.position

    def toggle(self, i):
        self.enabled[i] = not self.enabled[i]

    def set_degree(self, i, degree):
        self.degree[i] = degree % STEPS

    def nudge_degree(self, i, delta):
        self.degree[i] = (self.degree[i] + delta) % STEPS

    def shift(self, direction):
        d = direction % STEPS
        self.enabled = self.enabled[-d:] + self.enabled[:-d]
        self.degree = self.degree[-d:] + self.degree[:-d]


class Vary:
    """A slow pseudo-random walk applied to filter/res/drive/LFO-rate,
    nudged once per completed lap of the pattern - the "new ideas" Sequencer
    B keeps offering, simplified to a single on/off toggle."""

    def __init__(self, seed=1):
        random.seed(seed)  # CircuitPython's random has no Random() class to instantiate
        self._rng = random
        self.enabled = False
        self.filter_hz = 0.0
        self.resonance = 0.0
        self.drive = 0.0

    def _signed(self, magnitude_min, magnitude_max):
        # uniform(-max, max) can land near zero and feel like nothing
        # happened; pick a magnitude that's always at least noticeable,
        # then randomize its sign.
        magnitude = self._rng.uniform(magnitude_min, magnitude_max)
        return magnitude if self._rng.random() < 0.5 else -magnitude

    def reroll(self):
        self.filter_hz = self._signed(800, 2600)
        self.resonance = self._signed(0.8, 2.5)
        self.drive = self._signed(0.08, 0.3)

    def step(self):
        if not self.enabled:
            return
        self.filter_hz = _clamp(self.filter_hz + self._signed(150, 500), -2600, 2600)
        self.resonance = _clamp(self.resonance + self._signed(0.15, 0.5), -2.5, 2.5)
        self.drive = _clamp(self.drive + self._signed(0.03, 0.08), -0.3, 0.3)
