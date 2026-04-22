# score2midi

Convert scanned sheet music (images or PDFs) to MIDI, WAV, or MP3.

## How it works

```
Image / PDF
    ↓
Optical Music Recognition (Audiveris)
    ↓
MusicXML
    ↓
MIDI (music21)
    ↓
WAV / MP3 (FluidSynth + ffmpeg)
```

## Requirements

- macOS with Homebrew
- Python 3.12 (managed via pyenv)
- Java (OpenJDK) — for Audiveris
- FluidSynth and ffmpeg — for audio rendering

## Setup

```bash
# 1. Install system dependencies
brew install pyenv ffmpeg fluidsynth openjdk

# 2. Install Audiveris (macOS arm64)
# Download from https://github.com/Audiveris/audiveris/releases
# and move Audiveris.app to /Applications

# 3. Install Python 3.12
pyenv install 3.12.9

# 4. Clone and set up the project
git clone git@github.com:waitgh/score2midi.git
cd score2midi
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

## Usage

```bash
source .venv/bin/activate

# Convert to MP3 (default)
score2midi convert sheet.png

# Convert a PDF
score2midi convert sheet.pdf

# Override tempo and time signature
score2midi convert sheet.png --tempo 80 --time-sig "3/4"

# Save the intermediate MusicXML for inspection in MuseScore
score2midi convert sheet.png --save-musicxml sheet.musicxml

# Fast debug loop — skip the slow OMR step, re-render from saved MusicXML
score2midi from-xml sheet.musicxml --tempo 66 --time-sig "3/4"

# Other output formats
score2midi convert sheet.png --format wav
score2midi convert sheet.png --format midi --output song.mid
```

### Options — `convert`

| Option | Short | Default | Description |
|---|---|---|---|
| `--format` | `-f` | `mp3` | Output format: `midi`, `wav`, `mp3` |
| `--output` | `-o` | same name as input | Output file path |
| `--tempo` | `-t` | from score | Override tempo in BPM |
| `--time-sig` | | from score | Override time signature (e.g. `3/4`) |
| `--save-musicxml` | | — | Save intermediate MusicXML for debugging |
| `--soundfont` | `-s` | `soundfonts/FluidR3.sf3` | Custom soundfont (.sf2 or .sf3) |

### Options — `from-xml`

Same as `convert` minus `--save-musicxml`. Takes a `.musicxml` file directly, skipping OMR.

## Supported input formats

- Images: `.png`, `.jpg`, `.jpeg`, `.tiff`, `.bmp`
- Documents: `.pdf` (multi-page supported — pages are combined into one output)

## Debug workflow

OMR takes 1–2 minutes. To avoid re-running it on every tweak:

```bash
# Step 1 — run OMR once, save the MusicXML
score2midi convert sheet.png --save-musicxml sheet.musicxml

# Step 2 — iterate in seconds
score2midi from-xml sheet.musicxml --tempo 80
score2midi from-xml sheet.musicxml --tempo 80 --time-sig "3/4"
score2midi from-xml sheet.musicxml --format midi
```

Open `sheet.musicxml` in [MuseScore](https://musescore.org) (free) to visually inspect what was recognised.

## OMR limitations

Audiveris is the best available free OMR engine, but no OMR is perfect:

- **Tempo** — rarely encoded in scanned scores; use `--tempo` to set BPM manually
- **Complex scores** — dense chords, multiple voices, or poor scan quality reduce accuracy
- **Handwritten scores** — not supported reliably

## Project structure

```
score2midi/
├── soundfonts/
│   └── FluidR3.sf3       # bundled GM soundfont
├── score2midi/
│   ├── cli.py            # typer CLI (convert + from-xml commands)
│   ├── omr.py            # Audiveris wrapper (image/PDF → MusicXML)
│   ├── converter.py      # music21 (MusicXML → MIDI)
│   └── renderer.py       # FluidSynth + ffmpeg (MIDI → WAV/MP3)
└── pyproject.toml
```

## Dependencies

| Library | Purpose |
|---|---|
| [Audiveris](https://github.com/Audiveris/audiveris) | Optical Music Recognition |
| [music21](https://web.mit.edu/music21/) | MusicXML parsing and MIDI export |
| [FluidSynth](https://www.fluidsynth.org/) | MIDI to WAV rendering |
| [ffmpeg](https://ffmpeg.org/) | WAV to MP3 encoding |
| [pymupdf](https://pymupdf.readthedocs.io/) | PDF to image conversion |
| [typer](https://typer.tiangolo.com/) | CLI framework |
