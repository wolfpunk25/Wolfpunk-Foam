# Liquid Foam, simplified - and how it maps to Wolfpunk Foam

Herbs and Stones' [Liquid Foam](https://herbs---stones.com/liquid-foam/) is a
monophonic, banana-jack-patched analogue groovebox built around a dual
sequencer. This is a plain-English summary of its printed manual, followed by
how each piece maps onto the Adafruit MacroPad RP2040 build in this repo.
Patching is the one thing deliberately *not* carried over - everything here
is hard-wired in software instead of being something you'd re-patch by hand.

## What the real module does

- **Oscillator** - triangle, sawtooth and square, blended with two mix
  knobs; the square wave's pulse width is adjustable but not modulatable.
- **Filter** - a two-pole, 12dB/octave resonant low-pass, `freq` and `res`.
- **Drive** - a CMOS-based overdrive stage right before the output jack,
  which the manual warns gets uncomfortably hot-sounding at full clockwise.
- **Envelope generator** - decay-only, retriggered on every gate. Its
  `offset` knob sets how much of an (optionally inverted) copy of that decay
  reaches the filter's cutoff frequency, so different steps can sound like
  they have different envelope shapes even though there's only one envelope.
  A gate can also be routed to the oscillator's pitch input for glides.
- **Pitch sequencer ("Sequencer A")** - a 3-bit DAC fed by up to three gate
  inputs (A, B, C). The combinations (A, B, AB, C, AC, BC, ABC) decode to
  seven distinct pitches. Only one gate is normally active at a time, but the
  `X`/`Y` controls shift the running pattern around, and gates can be
  stacked for more predictable results.
- **Sequencer B** - takes gates from the clock, the LFO or Sequencer A, and
  can have several gates high at once. Its four outputs rotate
  counter-clockwise onto the LFO's rate/width, the filter's freq/res and the
  drive amount, so the patch quietly re-combines itself every so often.
- **LFO** - a square wave with `rate` and `width`, normalled to the
  Sequencer B input so it can also feed the pitch DAC.
- **Clock** - free-running, with a mini-jack in/out (5V, ~quarter-note
  pulses). If the external clock signal stops, it falls back to its own
  internal clock after about a second - useful and occasionally surprising.
- No master volume - level is set entirely at the mixer.

A companion MusicRadar review by Rob Mitchell compared the sequencer to a
303 from some alternate timeline: each pass suggests a new idea rather than
faithfully replaying a fixed pattern, and it particularly rewards scratchy,
resonant, semi-controlled patch choices.

## How Wolfpunk Foam maps this onto the MacroPad

| Liquid Foam | Wolfpunk Foam |
|---|---|
| Banana patching | Nothing to patch - every source is hard-wired to a sensible destination, matching the table below. |
| Wave mixer (tri/saw/square, pulse width) | `WAVE` page: one knob sweeps triangle -> saw -> square; shift+knob sets pulse width. |
| 2-pole resonant LPF | `FILTER` page: knob = cutoff (log, 60Hz-9kHz); shift+knob = resonance. |
| Drive stage | `DRIVE` page: knob = drive/soft-clip amount; shift+knob = output level (the mixer knob the real unit doesn't have). |
| Decay envelope -> filter (offset, inv) | `ENV` page: knob = decay time; shift+knob = signed depth into the filter cutoff (negative = inverted). |
| LFO (rate, width) | `LFO` page: knob = rate; shift+knob = width (duty cycle). Encoder click toggles its destination between filter wobble and a rhythmic pitch hop - see [voice.py](../CIRCUITPY/wolfpunk/voice.py) and [code.py](../CIRCUITPY/code.py). |
| Sequencer A (3-bit DAC, 7 pitches) | The 7 step keys - one pitch each, from a 7-note scale (`SCALE` page picks the scale and root). |
| X/Y pattern shift | The two keys either side of the step row nudge (rotate) the whole pattern left/right. |
| Sequencer B (evolving modulation) | The `VARY` key: toggles a slow random walk over filter/resonance/drive, nudged once per lap of the pattern. Long-press the encoder to reroll it on demand. |
| Clock in/out (5V jack) | Internal tempo (`TEMPO` page: BPM, shift+knob = swing) sent out as USB MIDI clock (24 ppqn) plus Start/Stop, so external gear can still lock to it. |
| Mono output to a mixer | USB MIDI note out, *and* the onboard speaker plays the same voice live - see [Speaker in the README](../README.md#why-the-speaker-and-midi-agree). |

The pattern itself is 7 steps long rather than the usual 8 or 16 - a direct
consequence of there only being 7 pitches (and 7 step keys) to begin with.
Left alone, that makes every loop drift against a 4/4 grid, which fits right
in with the odd, off-key runs the real module is known for.
