"""Optical Music Recognition: image/PDF → MusicXML using Audiveris."""

import subprocess
import zipfile
from pathlib import Path

AUDIVERIS = "/Applications/Audiveris.app/Contents/MacOS/Audiveris"


def process(input_path: Path, work_dir: Path) -> list[Path]:
    """Process an image or PDF and return a list of MusicXML paths (one per page)."""
    suffix = input_path.suffix.lower()
    if suffix not in (".png", ".jpg", ".jpeg", ".tiff", ".tif", ".bmp", ".pdf"):
        raise ValueError(f"Unsupported input format: '{suffix}'. Use PNG, JPG, or PDF.")

    return _run_audiveris(input_path, work_dir)


def _run_audiveris(input_path: Path, output_dir: Path) -> list[Path]:
    """Run Audiveris in batch mode and return paths to the MusicXML files."""
    cmd = [
        AUDIVERIS,
        "-batch",
        "-transcribe",
        "-export",
        "-output", str(output_dir),
        "--",
        str(input_path),
    ]

    import os
    env = os.environ.copy()
    env["PATH"] = "/opt/homebrew/opt/openjdk/bin:" + env.get("PATH", "/usr/bin:/bin")

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        env=env,
    )

    # Audiveris outputs .mxl files (compressed MusicXML) — extract them
    mxl_files = sorted(output_dir.rglob("*.mxl"))
    if not mxl_files:
        raise RuntimeError(
            f"Audiveris produced no output.\nSTDOUT: {result.stdout[-2000:]}\nSTDERR: {result.stderr[-2000:]}"
        )

    return [_extract_mxl(f, output_dir) for f in mxl_files]


def _extract_mxl(mxl_path: Path, output_dir: Path) -> Path:
    """Extract a .mxl (zip) file and return the path to the inner .xml file."""
    with zipfile.ZipFile(mxl_path, "r") as z:
        for name in z.namelist():
            if name.endswith(".xml") and not name.startswith("META-INF"):
                xml_path = output_dir / Path(name).name
                xml_path.write_bytes(z.read(name))
                return xml_path
    raise RuntimeError(f"No XML found inside {mxl_path}")
