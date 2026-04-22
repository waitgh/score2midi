"""score2midi CLI — sheet music image/PDF → MIDI / WAV / MP3."""

import shutil
import tempfile
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console

from score2midi import omr, converter, renderer

app = typer.Typer(
    help="Convert scanned sheet music (image or PDF) to MIDI, WAV, or MP3.",
    no_args_is_help=True,
)
console = Console()


@app.command()
def convert(
    input_file: Path = typer.Argument(..., help="Sheet music image (.png/.jpg) or PDF"),
    output: Optional[Path] = typer.Option(
        None, "--output", "-o", help="Output file path (default: same name as input)"
    ),
    format: str = typer.Option(
        "mp3", "--format", "-f", help="Output format: midi | wav | mp3"
    ),
    soundfont: Optional[Path] = typer.Option(
        None, "--soundfont", "-s", help="Custom soundfont file (.sf2 or .sf3)"
    ),
    tempo: Optional[int] = typer.Option(
        None, "--tempo", "-t", help="Override tempo in BPM (e.g. 80). Default: use tempo from score or 120."
    ),
    time_sig: Optional[str] = typer.Option(
        None, "--time-sig", help="Override time signature (e.g. '3/4'). Default: use value from score."
    ),
    save_musicxml: Optional[Path] = typer.Option(
        None, "--save-musicxml", help="Save the intermediate MusicXML here for inspection in MuseScore."
    ),
):
    """Convert a sheet music image or PDF to audio."""
    if not input_file.exists():
        console.print(f"[red]Error:[/red] File not found: {input_file}")
        raise typer.Exit(1)

    fmt = format.lower().lstrip(".")
    if fmt == "midi":
        fmt = "mid"
    if fmt not in ("mid", "wav", "mp3"):
        console.print(f"[red]Error:[/red] Unknown format '{format}'. Use: midi, wav, mp3")
        raise typer.Exit(1)

    if output is None:
        output = input_file.with_suffix(f".{fmt}")

    sf = soundfont or renderer.DEFAULT_SOUNDFONT
    if fmt != "mid" and not sf.exists():
        console.print(f"[red]Error:[/red] Soundfont not found: {sf}")
        console.print("Place a .sf2/.sf3 file in soundfonts/ or pass --soundfont <path>")
        raise typer.Exit(1)

    with tempfile.TemporaryDirectory() as _tmp:
        work_dir = Path(_tmp)

        # ── Step 1: OMR ────────────────────────────────────────────────────────
        console.print("\n[bold cyan]Step 1/3[/bold cyan] Running optical music recognition…")
        console.print("  (First run downloads model weights ~100 MB — subsequent runs are fast)")
        try:
            mxl_paths = omr.process(input_file, work_dir)
        except Exception as exc:
            console.print(f"[red]OMR failed:[/red] {exc}")
            raise typer.Exit(1)
        console.print(f"  [green]✓[/green] Recognised {len(mxl_paths)} page(s)")

        # ── Optional: save MusicXML for inspection ────────────────────────────
        if save_musicxml is not None:
            if len(mxl_paths) == 1:
                shutil.copy(mxl_paths[0], save_musicxml)
            else:
                save_musicxml.mkdir(parents=True, exist_ok=True)
                for mxl in mxl_paths:
                    shutil.copy(mxl, save_musicxml / mxl.name)
            console.print(f"  [dim]MusicXML saved → {save_musicxml}[/dim]")

        # ── Step 2: MusicXML → MIDI ────────────────────────────────────────────
        console.print("\n[bold cyan]Step 2/3[/bold cyan] Converting to MIDI…")
        if tempo is not None:
            console.print(f"  Tempo override: [bold]{tempo} BPM[/bold]")
        if time_sig is not None:
            console.print(f"  Time signature override: [bold]{time_sig}[/bold]")
        midi_path = work_dir / "output.mid"
        try:
            midi_path = converter.to_midi(mxl_paths, midi_path, tempo_bpm=tempo, time_sig=time_sig)
        except Exception as exc:
            console.print(f"[red]MIDI conversion failed:[/red] {exc}")
            raise typer.Exit(1)
        console.print("  [green]✓[/green] MIDI ready")

        # ── Step 3: render or copy ─────────────────────────────────────────────
        console.print(f"\n[bold cyan]Step 3/3[/bold cyan] Writing {fmt.upper()} output…")
        try:
            if fmt == "mid":
                shutil.copy(midi_path, output)
            elif fmt == "wav":
                renderer.midi_to_wav(midi_path, output, sf)
            else:
                renderer.midi_to_mp3(midi_path, output, sf)
        except Exception as exc:
            console.print(f"[red]Rendering failed:[/red] {exc}")
            raise typer.Exit(1)

    console.print(f"\n[bold green]Done![/bold green] → {output.resolve()}\n")


@app.command("from-xml")
def from_xml(
    musicxml_file: Path = typer.Argument(..., help="MusicXML file produced by a previous run"),
    output: Optional[Path] = typer.Option(
        None, "--output", "-o", help="Output file path (default: same name as input)"
    ),
    format: str = typer.Option(
        "mp3", "--format", "-f", help="Output format: midi | wav | mp3"
    ),
    soundfont: Optional[Path] = typer.Option(
        None, "--soundfont", "-s", help="Custom soundfont file (.sf2 or .sf3)"
    ),
    tempo: Optional[int] = typer.Option(
        None, "--tempo", "-t", help="Override tempo in BPM (e.g. 80)"
    ),
    time_sig: Optional[str] = typer.Option(
        None, "--time-sig", help="Override time signature (e.g. '3/4')"
    ),
):
    """Convert an existing MusicXML file to audio — skips the slow OMR step."""
    if not musicxml_file.exists():
        console.print(f"[red]Error:[/red] File not found: {musicxml_file}")
        raise typer.Exit(1)

    fmt = format.lower().lstrip(".")
    if fmt == "midi":
        fmt = "mid"
    if fmt not in ("mid", "wav", "mp3"):
        console.print(f"[red]Error:[/red] Unknown format '{format}'. Use: midi, wav, mp3")
        raise typer.Exit(1)

    if output is None:
        output = musicxml_file.with_suffix(f".{fmt}")

    sf = soundfont or renderer.DEFAULT_SOUNDFONT
    if fmt != "mid" and not sf.exists():
        console.print(f"[red]Error:[/red] Soundfont not found: {sf}")
        raise typer.Exit(1)

    with tempfile.TemporaryDirectory() as _tmp:
        work_dir = Path(_tmp)

        console.print("\n[bold cyan]Step 1/2[/bold cyan] Converting MusicXML → MIDI…")
        if tempo is not None:
            console.print(f"  Tempo: [bold]{tempo} BPM[/bold]")
        if time_sig is not None:
            console.print(f"  Time signature: [bold]{time_sig}[/bold]")
        midi_path = work_dir / "output.mid"
        try:
            midi_path = converter.to_midi([musicxml_file], midi_path, tempo_bpm=tempo, time_sig=time_sig)
        except Exception as exc:
            console.print(f"[red]MIDI conversion failed:[/red] {exc}")
            raise typer.Exit(1)
        console.print("  [green]✓[/green] MIDI ready")

        console.print(f"\n[bold cyan]Step 2/2[/bold cyan] Writing {fmt.upper()} output…")
        try:
            if fmt == "mid":
                shutil.copy(midi_path, output)
            elif fmt == "wav":
                renderer.midi_to_wav(midi_path, output, sf)
            else:
                renderer.midi_to_mp3(midi_path, output, sf)
        except Exception as exc:
            console.print(f"[red]Rendering failed:[/red] {exc}")
            raise typer.Exit(1)

    console.print(f"\n[bold green]Done![/bold green] → {output.resolve()}\n")


def main():
    app()
