"""MusicXML → MIDI conversion using music21."""

from pathlib import Path

import music21


def to_midi(
    musicxml_paths: list[Path],
    output_path: Path,
    tempo_bpm: int = None,
    time_sig: str = None,
    instrument_name: str = None,
) -> Path:
    """Parse one or more MusicXML files and write a combined MIDI file.

    Args:
        musicxml_paths:  One MusicXML file per page.
        output_path:     Destination .mid file.
        tempo_bpm:       If set, overrides whatever tempo is in the score.
        time_sig:        If set (e.g. "3/4"), overrides the time signature.
        instrument_name: If set (e.g. "Piano"), overrides the instrument on all parts.
    """
    if len(musicxml_paths) == 1:
        score = music21.converter.parse(str(musicxml_paths[0]))
    else:
        score = _combine(musicxml_paths)

    if tempo_bpm is not None:
        _set_tempo(score, tempo_bpm)

    if time_sig is not None:
        _set_time_signature(score, time_sig)

    if instrument_name is not None:
        _set_instrument(score, instrument_name)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    score.write("midi", fp=str(output_path))
    return output_path


def _set_tempo(score: music21.stream.Score, bpm: int) -> None:
    """Replace all tempo markings in the score with a fixed BPM."""
    # Remove every tempo indication anywhere in the score (including <sound> elements
    # that sit outside measures, at the part level)
    for el in list(score.recurse().getElementsByClass(music21.tempo.TempoIndication)):
        el.activeSite.remove(el)

    # Insert a single marking at offset 0 of the first part
    mark = music21.tempo.MetronomeMark(number=bpm)
    if score.parts:
        score.parts[0].insert(0, mark)
    else:
        score.insert(0, mark)


def _set_time_signature(score: music21.stream.Score, time_sig: str) -> None:
    """Replace all time signatures in the score with the given one (e.g. '3/4')."""
    ts = music21.meter.TimeSignature(time_sig)
    for el in list(score.recurse().getElementsByClass(music21.meter.TimeSignature)):
        el.activeSite.remove(el)
    # Insert into the first measure of each part so MIDI export sees it
    for part in score.parts:
        measures = part.getElementsByClass("Measure")
        if measures:
            measures[0].insert(0, ts)


def _set_instrument(score: music21.stream.Score, names: str) -> None:
    """Set instruments by part.

    names: comma-separated list, e.g. "Piano" or "Voice,Piano".
    - One name  → applied to all parts.
    - Many names → applied per part in order; extras are ignored.
    """
    name_list = [n.strip() for n in names.split(",")]

    for part_idx, part in enumerate(score.parts):
        name = name_list[0] if len(name_list) == 1 else name_list[part_idx] if part_idx < len(name_list) else None
        if name is None:
            continue
        try:
            inst = music21.instrument.fromString(name)
        except music21.instrument.InstrumentException:
            raise ValueError(
                f"Unknown instrument '{name}'. "
                "Examples: Piano, Violin, Flute, Guitar, Voice, Trumpet, Cello."
            )
        for existing in list(part.getElementsByClass(music21.instrument.Instrument)):
            part.remove(existing)
        part.insert(0, inst)


def _combine(paths: list[Path]) -> music21.stream.Score:
    """Concatenate multiple per-page scores into one by appending measures."""
    base = music21.converter.parse(str(paths[0]))

    for path in paths[1:]:
        page = music21.converter.parse(str(path))
        for part_idx, part in enumerate(page.parts):
            if part_idx >= len(base.parts):
                break
            base_part = base.parts[part_idx]
            for measure in part.getElementsByClass("Measure"):
                base_part.append(measure)

    return base
