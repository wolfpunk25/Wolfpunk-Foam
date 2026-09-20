# The monophonic voice: oscillator (tri/saw/square blend), resonant
# low-pass filter with a decay-only envelope driving its cutoff, and a
# drive stage that just pushes amplitude into synthio's own soft clipping.
#
# This is the simplified stand-in for the Liquid Foam's VCO + wave mixer +
# LPF + envelope generator + drive stage, collapsed onto knobs the encoder
# pages can reach. See docs/liquid-foam-manual-notes.md for the mapping.

import time
import board
import audiopwmio
import synthio
import ulab.numpy as np

SAMPLE_RATE = 22050
TABLE_SIZE = 512
VOL = 28000

FILTER_MIN_HZ = 60
FILTER_MAX_HZ = 9000
ENV_FILTER_RANGE_HZ = 6000  # how far the envelope can swing the cutoff

WAVE_REGEN_THROTTLE = 0.03  # seconds; avoid rebuilding the table every tick


def _triangle():
    half = TABLE_SIZE // 2
    rising = [int(-VOL + (2 * VOL) * i / half) for i in range(half)]
    falling = [int(VOL - (2 * VOL) * i / half) for i in range(half)]
    return rising + falling


def _saw():
    return [int(VOL - (2 * VOL) * i / TABLE_SIZE) for i in range(TABLE_SIZE)]


def _pulse(width):
    on = max(1, min(TABLE_SIZE - 1, int(TABLE_SIZE * width)))
    return [VOL] * on + [-VOL] * (TABLE_SIZE - on)


def _crossfade(a, b, t):
    return [int(a[i] * (1 - t) + b[i] * t) for i in range(TABLE_SIZE)]


def _clamp(v, lo, hi):
    return lo if v < lo else hi if v > hi else v


class Voice:
    def __init__(self, macropad):
        # adafruit_macropad.MacroPad already claims SPEAKER_ENABLE in its own
        # constructor and never exposes it publicly, so reuse the pin it's
        # holding rather than fight it for ownership (raises "in use").
        macropad._speaker_enable.value = True

        self.audio = audiopwmio.PWMAudioOut(board.SPEAKER)
        self.synth = synthio.Synthesizer(sample_rate=SAMPLE_RATE)
        self.audio.play(self.synth)

        self._tri = _triangle()
        self._saw = _saw()
        self._pulse_width = 0.5
        self._pulse = _pulse(self._pulse_width)
        self._blend = 0.35
        self._last_wave_regen = 0.0

        self.note = synthio.Note(
            frequency=110,
            waveform=np.array(self._crossfaded(), dtype=np.int16),
            amplitude=0.6,
            envelope=synthio.Envelope(
                attack_time=0.004,
                decay_time=0.3,
                sustain_level=0.0,
                release_time=0.03,
            ),
        )

        self.cutoff_base = 2000
        self.resonance = 1.2
        self.env_depth = 0.5  # -1..+1, negative = inverted per the manual's "eg inv"
        self.decay_time = 0.3
        self.drive = 0.15
        self.level = 0.7

        self._note_on_time = None
        self._playing = False
        self._extra_filter_hz = 0.0

    def _crossfaded(self):
        if self._blend <= 0.5:
            return _crossfade(self._tri, self._saw, self._blend * 2)
        return _crossfade(self._saw, self._pulse, (self._blend - 0.5) * 2)

    def set_wave(self, blend, pulse_width=None):
        now = time.monotonic()
        self._blend = _clamp(blend, 0.0, 1.0)
        if pulse_width is not None:
            self._pulse_width = _clamp(pulse_width, 0.05, 0.95)
        if now - self._last_wave_regen < WAVE_REGEN_THROTTLE:
            return
        self._last_wave_regen = now
        self._pulse = _pulse(self._pulse_width)
        self.note.waveform = np.array(self._crossfaded(), dtype=np.int16)

    def set_filter(self, cutoff_hz, resonance):
        self.cutoff_base = _clamp(cutoff_hz, FILTER_MIN_HZ, FILTER_MAX_HZ)
        self.resonance = _clamp(resonance, 0.5, 8.0)

    def set_envelope(self, decay_time, depth):
        self.decay_time = _clamp(decay_time, 0.005, 2.0)
        self.env_depth = _clamp(depth, -1.0, 1.0)
        self.note.envelope = synthio.Envelope(
            attack_time=0.004,
            decay_time=self.decay_time,
            sustain_level=0.0,
            release_time=0.03,
        )

    def set_drive(self, drive, level):
        self.drive = _clamp(drive, 0.0, 1.0)
        self.level = _clamp(level, 0.15, 1.0)

    def trigger(self, midi_note, extra_filter_hz=0.0):
        self.note.frequency = synthio.midi_to_hz(midi_note)
        amp = self.level * (1.0 + self.drive * 2.5)
        self.note.amplitude = min(amp, 3.0)
        self._note_on_time = time.monotonic()
        self._playing = True
        self._extra_filter_hz = extra_filter_hz
        self._update_filter(0.0)
        # retriggers the envelope even if the note was already sounding
        # (legato steps in the pattern), and is safe even if it wasn't
        self.synth.release_then_press(self.note)

    def silence(self):
        self.synth.release(self.note)
        self._playing = False

    def _update_filter(self, elapsed):
        decay_frac = 2 ** (-elapsed / max(self.decay_time, 0.005))
        depth_hz = self.env_depth * ENV_FILTER_RANGE_HZ * decay_frac
        cutoff = self.cutoff_base + depth_hz + self._extra_filter_hz
        cutoff = _clamp(cutoff, FILTER_MIN_HZ, FILTER_MAX_HZ)
        # CircuitPython 10.2.1's synthio has no Synthesizer.low_pass_filter()
        # helper - build the Biquad directly instead.
        self.note.filter = synthio.Biquad(synthio.FilterMode.LOW_PASS, frequency=cutoff, Q=self.resonance)

    def tick(self):
        """Call every main-loop iteration to sweep the filter envelope."""
        if not self._playing or self._note_on_time is None:
            return
        if abs(self.env_depth) < 0.01:
            return  # flat cutoff, nothing to sweep
        elapsed = time.monotonic() - self._note_on_time
        if elapsed > self.decay_time * 6:
            self._playing = False  # envelope has settled; stop polling
            return
        self._update_filter(elapsed)
