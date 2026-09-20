# Seven-degree scale tables, one semitone offset per step key.
# Real Liquid Foam pitch DAC only ever produces 7 distinct pitches from its
# gate combinations (A, B, AB, C, AC, BC, ABC) - same shape as our 7 step
# keys, so every scale here is exactly 7 notes long by construction.

NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]

# name -> 7 semitone offsets from the root
SCALES = {
    "Major":     [0, 2, 4, 5, 7, 9, 11],
    "Minor":     [0, 2, 3, 5, 7, 8, 10],
    "Dorian":    [0, 2, 3, 5, 7, 9, 10],
    # Phrygian dominant, a.k.a. the "Byzantine" scale - the reviewer's own
    # word for the kind of runs this box is good at.
    "Byzantine": [0, 1, 4, 5, 7, 8, 10],
    "MinPent+2": [0, 3, 5, 7, 10, 12, 15],  # pentatonic stretched to 7 degrees
    "WholeTone": [0, 2, 4, 6, 8, 10, 12],
    # A tight chromatic cluster - deliberately the "off-key tantrum" scale.
    "Cluster":   [0, 1, 2, 3, 4, 5, 6],
}

SCALE_NAMES = list(SCALES.keys())

BASE_MIDI = 48  # C3 - root note when ROOT index is 0 (C) and octave offset is 0


def midi_note(root_index, scale_name, degree, octave=0):
    offset = SCALES[scale_name][degree % 7]
    return BASE_MIDI + root_index + offset + (12 * octave)
