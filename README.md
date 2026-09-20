# Wolfpunk Foam

A MIDI groovebox for the [Adafruit MacroPad RP2040](https://www.adafruit.com/product/5128),
loosely modelled on Herbs and Stones' [Liquid Foam](https://herbs---stones.com/liquid-foam/) -
a monophonic analogue synth built around a dual sequencer and open banana
patching. This firmware keeps the character (a decay-only filter envelope,
a wave-mixed oscillator, a self-varying second sequencer, an odd 7-step
loop) but drops the patch cables: everything is hard-wired in software so it
can live entirely on the MacroPad's 12 keys, its encoder, its screen and its
RGB LEDs.

See [docs/liquid-foam-manual-notes.md](docs/liquid-foam-manual-notes.md) for a
plain-English summary of the real module and exactly how each part maps
onto this one - start there if you want to know *why* something works the
way it does.

## Why the speaker and MIDI agree

Wolfpunk Foam plays one [`synthio`](https://docs.circuitpython.org/en/latest/shared-bindings/synthio/index.html)
voice through the MacroPad's built-in speaker, live, at the same time as it
sends the pattern out over USB MIDI. It's the same oscillator/filter/envelope
math driving both, so what comes out of the little speaker is a low-fi
preview of exactly what's being sent to whatever you plug the MacroPad into
- not a separate "beep" sound engine bolted on for fun.

## What you get

- A 7-step pitch sequencer (one step per key), each step toggle-on/off and
  individually tunable across a 7-note scale.
- Seven scales to choose from, including a "Byzantine" (Phrygian dominant)
  one as a nod to the review's description of the original's off-key runs.
- A wave-mixed oscillator (triangle -> saw -> square), a resonant low-pass
  filter with a sweeping decay envelope, and a drive stage - all on the
  encoder, one knob-equivalent per page, shift for the second parameter.
- `VARY`: an auto-wobble over filter/resonance/drive that gently changes the
  patch every lap of the pattern, standing in for the original's Sequencer B.
- Free-running LFO, switchable between wobbling the filter or hopping the
  pitch.
- USB MIDI note out plus MIDI clock/start/stop, so external gear can lock to
  it the way you'd lock a drum machine to the real module's clock jack.
- A live step/page/pattern readout on the OLED and pitch-coloured key LEDs.

## Controls

```
 [STEP1][STEP2][STEP3]
 [STEP4][STEP5][STEP6]
 [STEP7][ <  ][  >  ]
 [PLAY ][VARY ][PAGE ]

        (ENCODER)
```

- **STEP 1-7** - tap to toggle that step on/off. Press and hold to hear it
  play immediately; while held, turn the encoder to retune that step within
  the current scale.
- **`<` / `>`** - rotate (shift) the whole pattern left/right, live.
- **PLAY** - start/stop the internal clock. Green when running, red when
  stopped.
- **VARY** - toggle the auto-wobble on/off. Purple when active.
- **PAGE** - tap to cycle the encoder's page (`WAVE`, `FILTER`, `ENV`,
  `LFO`, `DRIVE`, `TEMPO`, `SCALE`). Hold it down and turn the encoder to
  edit that page's *second* parameter instead of its first.
- **Encoder** - turn to edit the current page's parameter. Click to swap the
  LFO's destination between the filter and pitch. Press and hold (>0.6s) to
  reroll the `VARY` wobble on demand.

Full parameter list and what each page's shift-value does is in
[docs/liquid-foam-manual-notes.md](docs/liquid-foam-manual-notes.md).

## Installing it

The MacroPad's factory firmware in this household is
[Macropad Hotkeys](https://github.com/deckerego/Macropad_Hotkeys), whose
`boot.py` disables the USB drive - that's why CIRCUITPY isn't showing up on
the desktop right now, not a fault with the board. Wolfpunk Foam's own
`boot.py` does the opposite (nothing), so once it's on the board CIRCUITPY
mounts normally again.

**Getting in for the first time**, since the drive isn't mounted yet:

1. Press the reset button on the left edge of the board.
2. As soon as it resets, hold the top-left key (KEY1) until the OLED shows
   "Mounting Read/Write".
3. CIRCUITPY should now appear on the desktop, writable.

**Then:**

```bash
# from this repo:
circup --path /Volumes/CIRCUITPY install adafruit_macropad adafruit_debouncer \
    adafruit_simple_text_display neopixel adafruit_display_text adafruit_hid \
    adafruit_midi adafruit_ticks
./tools/install.sh /Volumes/CIRCUITPY
```

[`circup`](https://pypi.org/project/circup/) installs the libraries the
`adafruit_macropad` helper needs (`pip install circup` if you don't have
it). `tools/install.sh` copies `CIRCUITPY/` onto the board - see the script
for why it's not just `cp -R` or `rsync` (macOS leaves `._*` AppleDouble
files all over a FAT volume, and CircuitPython chokes trying to import
them).

After that, the board reboots into Wolfpunk Foam on its own, and the drive
stays mounted for future edits - no more reset+KEY1 dance needed.

## Repo layout

```
CIRCUITPY/            everything that goes on the board
  code.py              main loop
  boot.py              deliberately empty - keeps the USB drive mounted
  wolfpunk/
    voice.py            oscillator + filter + envelope (the synthio voice)
    pattern.py           the 7-step sequencer and the VARY wobble
    clock.py             tempo, swing, MIDI clock scheduling
    scales.py            the 7 seven-note scales
    ui.py                 OLED + NeoPixel rendering
docs/
  liquid-foam-manual-notes.md   what the real module does, and the mapping
tools/
  install.sh            copies CIRCUITPY/ onto the mounted board, safely
```

## Changing things

- MIDI channel: `MIDI_CHANNEL` at the top of `code.py`.
- Note velocity: `VELOCITY` in the same place.
- LED brightness: `macropad.pixels.brightness` in `wolfpunk/ui.py`'s
  `UI.__init__`.
- Add a scale: append a 7-entry semitone list to `SCALES` in
  `wolfpunk/scales.py`.
