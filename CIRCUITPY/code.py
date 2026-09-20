# Wolfpunk Foam - a MIDI groovebox for the Adafruit MacroPad RP2040,
# loosely modelled on the Herbs and Stones Liquid Foam. See
# docs/liquid-foam-manual-notes.md for how the real module's controls map
# onto this one's pages, keys and encoder.

import time
from adafruit_macropad import MacroPad
from adafruit_midi.timing_clock import TimingClock
from adafruit_midi.start import Start
from adafruit_midi.stop import Stop
from adafruit_midi.note_on import NoteOn
from adafruit_midi.note_off import NoteOff

from wolfpunk.voice import Voice
from wolfpunk.pattern import Pattern, Vary
from wolfpunk.clock import Clock
from wolfpunk.scales import SCALE_NAMES, NOTE_NAMES, midi_note
import wolfpunk.ui as ui_mod

MIDI_CHANNEL = 0  # channel 1
VELOCITY = 100

PAGES = ["WAVE", "FILTER", "ENV", "LFO", "DRIVE", "TEMPO", "SCALE"]


def clamp(v, lo, hi):
    return lo if v < lo else hi if v > hi else v


class App:
    def __init__(self):
        self.macropad = MacroPad(midi_out_channel=MIDI_CHANNEL + 1)
        self.voice = Voice()
        self.pattern = Pattern()
        self.vary = Vary()
        self.clock = Clock(bpm=110)
        self.ui = ui_mod.UI(self.macropad)

        self.midi = self.macropad.midi  # adafruit_midi.MIDI, out channel set above

        self.page_index = 0
        self.shift_held = False
        self.held_step = None  # step key currently held for live-play/retune

        self.wave_blend = 0.35
        self.wave_pw = 0.5
        self.filter_cutoff = 2000
        self.filter_res = 1.2
        self.env_decay = 0.3
        self.env_depth = 0.5
        self.lfo_rate = 2.0
        self.lfo_width = 0.5
        self.lfo_dest_pitch = False
        self.drive = 0.15
        self.level = 0.7
        self.swing = 0.0
        self.scale_index = 0
        self.root_index = 0

        self.playhead = 0
        self.last_midi_note = None
        self._push_all_params()

        self._last_render = 0.0

    # -- parameter push-through --------------------------------------
    def _push_all_params(self):
        self.voice.set_wave(self.wave_blend, self.wave_pw)
        self.voice.set_filter(self.filter_cutoff, self.filter_res)
        self.voice.set_envelope(self.env_decay, self.env_depth)
        self.voice.set_drive(self.drive, self.level)
        self.clock.set_bpm(self.clock.bpm)
        self.clock.set_swing(self.swing)

    # -- encoder handling ----------------------------------------------
    def handle_encoder(self, delta):
        if delta == 0:
            return
        if self.held_step is not None:
            self.pattern.nudge_degree(self.held_step, delta)
            self._play_step(self.held_step, live=True)  # retrigger so the retune is audible
            return

        page = PAGES[self.page_index]
        if page == "WAVE":
            if self.shift_held:
                self.wave_pw = clamp(self.wave_pw + delta * 0.02, 0.05, 0.95)
            else:
                self.wave_blend = clamp(self.wave_blend + delta * 0.02, 0.0, 1.0)
            self.voice.set_wave(self.wave_blend, self.wave_pw)
        elif page == "FILTER":
            if self.shift_held:
                self.filter_res = clamp(self.filter_res + delta * 0.1, 0.5, 8.0)
            else:
                self.filter_cutoff = clamp(self.filter_cutoff * (1.05 ** delta), 60, 9000)
            self.voice.set_filter(self.filter_cutoff, self.filter_res)
        elif page == "ENV":
            if self.shift_held:
                self.env_depth = clamp(self.env_depth + delta * 0.05, -1.0, 1.0)
            else:
                self.env_decay = clamp(self.env_decay * (1.08 ** delta), 0.005, 2.0)
            self.voice.set_envelope(self.env_decay, self.env_depth)
        elif page == "LFO":
            if self.shift_held:
                self.lfo_width = clamp(self.lfo_width + delta * 0.02, 0.05, 0.95)
            else:
                self.lfo_rate = clamp(self.lfo_rate + delta * 0.1, 0.1, 20.0)
        elif page == "DRIVE":
            if self.shift_held:
                self.level = clamp(self.level + delta * 0.02, 0.15, 1.0)
            else:
                self.drive = clamp(self.drive + delta * 0.02, 0.0, 1.0)
            self.voice.set_drive(self.drive, self.level)
        elif page == "TEMPO":
            if self.shift_held:
                self.swing = clamp(self.swing + delta * 0.01, 0.0, 0.4)
                self.clock.set_swing(self.swing)
            else:
                self.clock.set_bpm(self.clock.bpm + delta)
        elif page == "SCALE":
            if self.shift_held:
                self.root_index = (self.root_index + delta) % 12
            else:
                self.scale_index = (self.scale_index + delta) % len(SCALE_NAMES)

    # -- LFO (free-running, not tied to the step clock) -----------------
    def _lfo_value(self):
        phase = (time.monotonic() * self.lfo_rate) % 1.0
        return 1.0 if phase < self.lfo_width else -1.0

    # -- MIDI helpers -----------------------------------------------
    def _midi_note_on(self, note):
        if self.last_midi_note is not None:
            self.midi.send(NoteOff(self.last_midi_note, 0))
        self.midi.send(NoteOn(note, VELOCITY))
        self.last_midi_note = note

    def _midi_note_off(self):
        if self.last_midi_note is not None:
            self.midi.send(NoteOff(self.last_midi_note, 0))
            self.last_midi_note = None

    # -- sequencer step -----------------------------------------------
    def _play_step(self, i, live=False):
        scale_name = SCALE_NAMES[self.scale_index]
        degree = self.pattern.degree[i]
        note = midi_note(self.root_index, scale_name, degree)

        lfo_val = self._lfo_value()
        extra_hz = self.vary.filter_hz + (lfo_val * 800.0 if not self.lfo_dest_pitch else 0.0)
        if self.lfo_dest_pitch and lfo_val > 0:
            note += 2  # a small rhythmic pitch hop instead of a filter wobble

        self.voice.set_filter(self.filter_cutoff, self.filter_res + self.vary.resonance)
        self.voice.set_drive(clamp(self.drive + self.vary.drive, 0.0, 1.0), self.level)
        self.voice.trigger(note, extra_filter_hz=extra_hz)
        self._midi_note_on(note)
        if not live:
            self.playhead = i

    def _advance_pattern(self):
        i = self.pattern.advance()
        if i == 0:
            self.vary.step()
        if self.pattern.enabled[i]:
            self._play_step(i)
        else:
            self.playhead = i
            self.voice.silence()
            self._midi_note_off()

    # -- key handling ---------------------------------------------------
    def handle_key(self, key_number, pressed):
        if key_number in ui_mod.KEY_STEPS:
            if pressed:
                self.held_step = key_number
                self._play_step(key_number, live=True)
            else:
                if self.held_step == key_number:
                    self.pattern.toggle(key_number)
                self.held_step = None
                self.voice.silence()
                self._midi_note_off()
            return

        if key_number == ui_mod.KEY_SHIFT_LEFT and pressed:
            self.pattern.shift(-1)
        elif key_number == ui_mod.KEY_SHIFT_RIGHT and pressed:
            self.pattern.shift(1)
        elif key_number == ui_mod.KEY_PLAY and pressed:
            self._toggle_run()
        elif key_number == ui_mod.KEY_VARY and pressed:
            self.vary.enabled = not self.vary.enabled
            if self.vary.enabled:
                self.vary.reroll()
        elif key_number == ui_mod.KEY_PAGE:
            self.shift_held = pressed
            if pressed:
                self.page_index = (self.page_index + 1) % len(PAGES)

    def _toggle_run(self):
        if self.clock.running:
            self.clock.stop()
            self.voice.silence()
            self._midi_note_off()
            self.midi.send(Stop())
        else:
            self.clock.start()
            self.midi.send(Start())

    def handle_encoder_switch(self, held_ms):
        if held_ms > 600:
            self.vary.reroll()
        else:
            self.lfo_dest_pitch = not self.lfo_dest_pitch

    # -- display ----------------------------------------------------
    def _render(self):
        page = PAGES[self.page_index]
        if page == "WAVE":
            primary = f"blend {self.wave_blend:.2f}"
            secondary = f"pw {self.wave_pw:.2f}"
        elif page == "FILTER":
            primary = f"cut {int(self.filter_cutoff)}Hz"
            secondary = f"res {self.filter_res:.2f}"
        elif page == "ENV":
            primary = f"decay {self.env_decay:.2f}s"
            secondary = f"depth {self.env_depth:+.2f}"
        elif page == "LFO":
            primary = f"rate {self.lfo_rate:.1f}Hz"
            secondary = f"width {self.lfo_width:.2f}"
        elif page == "DRIVE":
            primary = f"drive {self.drive:.2f}"
            secondary = f"level {self.level:.2f}"
        elif page == "TEMPO":
            primary = f"{int(self.clock.bpm)} bpm"
            secondary = f"swing {self.swing:.2f}"
        else:  # SCALE
            primary = SCALE_NAMES[self.scale_index]
            secondary = NOTE_NAMES[self.root_index]

        page_line = f"[{page}] {secondary}" if self.shift_held else f"{page}: {primary}"
        root_name = NOTE_NAMES[self.root_index]
        scale_name = SCALE_NAMES[self.scale_index]
        transport = "RUN" if self.clock.running else "STOP"
        status_line = f"{int(self.clock.bpm)}bpm {root_name}{scale_name} {transport}"
        lfo_dest = "pitch" if self.lfo_dest_pitch else "filt"
        vary_line = f"vary:{'on' if self.vary.enabled else 'off'} lfo>{lfo_dest}"

        self.ui.render(page_line, status_line, vary_line, self.pattern, self.playhead)
        self.ui.leds(
            self.pattern,
            self.playhead,
            self.clock.running,
            self.vary.enabled,
            self.shift_held,
        )

    # -- main loop --------------------------------------------------
    def run(self):
        macropad = self.macropad
        prev_encoder = macropad.encoder
        encoder_switch_down_at = None

        while True:
            while True:
                event = macropad.keys.events.get()
                if event is None:
                    break
                self.handle_key(event.key_number, event.pressed)

            enc = macropad.encoder
            if enc != prev_encoder:
                self.handle_encoder(enc - prev_encoder)
                prev_encoder = enc

            self.macropad.encoder_switch_debounced.update()
            if self.macropad.encoder_switch_debounced.pressed:
                encoder_switch_down_at = time.monotonic()
            if self.macropad.encoder_switch_debounced.released and encoder_switch_down_at:
                held_ms = (time.monotonic() - encoder_switch_down_at) * 1000
                self.handle_encoder_switch(held_ms)
                encoder_switch_down_at = None

            if self.clock.due_step():
                self._advance_pattern()
            ticks = self.clock.due_ticks()
            for _ in range(ticks):
                self.midi.send(TimingClock())

            self.voice.tick()

            now = time.monotonic()
            if now - self._last_render > 0.05:
                self._last_render = now
                self._render()


App().run()
