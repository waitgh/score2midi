"""MIDI → WAV / MP3 rendering using FluidSynth and ffmpeg."""

import subprocess
from pathlib import Path

# Default soundfont bundled with the project
DEFAULT_SOUNDFONT = Path(__file__).parent.parent / "soundfonts" / "FluidR3.sf3"


def midi_to_wav(midi_path: Path, output_path: Path, soundfont: Path = None) -> Path:
    """Render a MIDI file to WAV using FluidSynth."""
    sf = soundfont or DEFAULT_SOUNDFONT
    wav_path = output_path.with_suffix(".wav")

    cmd = [
        "fluidsynth",
        "-ni",                  # non-interactive, no audio driver
        "-F", str(wav_path),    # write output to file
        str(sf),
        str(midi_path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"FluidSynth failed:\n{result.stderr}")

    return wav_path


def wav_to_mp3(wav_path: Path, output_path: Path) -> Path:
    """Convert WAV to MP3 using ffmpeg."""
    mp3_path = output_path.with_suffix(".mp3")

    cmd = [
        "ffmpeg", "-y",
        "-i", str(wav_path),
        "-codec:a", "libmp3lame",
        "-qscale:a", "2",       # VBR quality ~190 kbps
        str(mp3_path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg failed:\n{result.stderr}")

    return mp3_path


def midi_to_mp3(midi_path: Path, output_path: Path, soundfont: Path = None) -> Path:
    """Render MIDI → WAV → MP3, cleaning up the intermediate WAV."""
    wav_path = midi_path.with_suffix(".wav")
    wav = midi_to_wav(midi_path, wav_path, soundfont)
    mp3 = wav_to_mp3(wav, output_path)
    wav.unlink(missing_ok=True)
    return mp3
