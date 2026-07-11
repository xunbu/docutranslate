# SPDX-FileCopyrightText: 2025 QinHan
# SPDX-License-Identifier: MPL-2.0
"""DWG ↔ DXF converter using external backends.

Detects and invokes user-installed converters (LibreDWG, HaoChen, AutoCAD).
DocuTranslate does NOT bundle converters — users install them separately.
"""
from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class ConverterResult:
    success: bool
    input_path: str
    output_path: str | None = None
    backend_used: str = ""
    message: str = ""


class DwgConverter:
    """Detect and call external DWG ↔ DXF converters."""

    BACKENDS = {
        "libredwg": "dwg2dxf",
        "haochen": "haochen_com",
        "autocad": "autocad_com",
    }

    def __init__(self, backend: str = "auto"):
        self.backend = backend.strip().lower()

    # ------------------------------------------------------------------
    # Detection
    # ------------------------------------------------------------------

    def detect_available(self) -> dict[str, bool]:
        """Return which backends are available on this system."""
        results: dict[str, bool] = {}
        for name, binary in self.BACKENDS.items():
            results[name] = shutil.which(binary) is not None
        return results

    def _select_backend(self) -> str:
        if self.backend and self.backend != "auto":
            return self.backend
        available = self.detect_available()
        for name in ("libredwg", "haochen", "autocad"):
            if available.get(name):
                return name
        return ""

    # ------------------------------------------------------------------
    # Conversion
    # ------------------------------------------------------------------

    def dwg_to_dxf(self, input_path: str, output_dir: str, backend: str = "") -> ConverterResult:
        """Convert DWG to DXF. If input is already DXF, copy it."""
        src = Path(input_path)
        if not src.exists():
            return ConverterResult(False, input_path, message=f"File not found: {input_path}")

        if src.suffix.lower() == ".dxf":
            out = Path(output_dir) / src.name
            out.parent.mkdir(parents=True, exist_ok=True)
            if src.resolve() != out.resolve():
                import shutil as _shutil
                _shutil.copy2(str(src), str(out))
            return ConverterResult(True, input_path, str(out), "dxf_only", "Input is already DXF")

        be = backend or self._select_backend()
        if not be:
            return ConverterResult(
                False, input_path,
                message="No DWG converter available. Install LibreDWG (dwg2dxf), HaoChen CAD, or AutoCAD.",
            )

        out_dir = Path(output_dir)
        out_dir.mkdir(parents=True, exist_ok=True)

        if be == "libredwg":
            return self._run_libredwg(src, out_dir)
        elif be in ("haochen", "autocad"):
            return self._run_com_backend(src, out_dir, be)
        else:
            return ConverterResult(False, input_path, message=f"Unknown backend: {be}")

    def dxf_to_dwg(self, input_path: str, output_dir: str, backend: str = "") -> ConverterResult:
        """Convert DXF to DWG (only supported by some backends)."""
        src = Path(input_path)
        if not src.exists():
            return ConverterResult(False, input_path, message=f"File not found: {input_path}")

        be = backend or self._select_backend()
        if be in ("haochen", "autocad"):
            return self._run_com_backend_dxf2dwg(src, Path(output_dir), be)

        return ConverterResult(False, input_path, message="DXF→DWG conversion requires HaoChen or AutoCAD backend")

    # ------------------------------------------------------------------
    # Backend implementations
    # ------------------------------------------------------------------

    def _run_libredwg(self, src: Path, out_dir: Path) -> ConverterResult:
        exe = shutil.which("dwg2dxf")
        if not exe:
            return ConverterResult(False, str(src), message="dwg2dxf not found in PATH")
        out = out_dir / f"{src.stem}.dxf"
        try:
            subprocess.run(
                [exe, "-o", str(out), str(src)],
                check=True, capture_output=True, timeout=120,
            )
            return ConverterResult(True, str(src), str(out), "libredwg")
        except subprocess.CalledProcessError as e:
            return ConverterResult(False, str(src), message=f"LibreDWG failed: {e.stderr.decode(errors='replace')}")
        except subprocess.TimeoutExpired:
            return ConverterResult(False, str(src), message="LibreDWG conversion timed out")

    def _run_com_backend(self, src: Path, out_dir: Path, backend: str) -> ConverterResult:
        """Invoke HaoChen/AutoCAD COM automation via Python script."""
        exe = shutil.which(f"{backend}_converter")
        if not exe:
            return ConverterResult(False, str(src), message=f"{backend}_converter not found in PATH")
        out = out_dir / f"{src.stem}.dxf"
        try:
            subprocess.run(
                [exe, "--input", str(src), "--output", str(out)],
                check=True, capture_output=True, timeout=300,
            )
            return ConverterResult(True, str(src), str(out), backend)
        except subprocess.CalledProcessError as e:
            return ConverterResult(False, str(src), message=f"{backend} failed: {e.stderr.decode(errors='replace')}")
        except subprocess.TimeoutExpired:
            return ConverterResult(False, str(src), message=f"{backend} conversion timed out")

    def _run_com_backend_dxf2dwg(self, src: Path, out_dir: Path, backend: str) -> ConverterResult:
        exe = shutil.which(f"{backend}_converter")
        if not exe:
            return ConverterResult(False, str(src), message=f"{backend}_converter not found in PATH")
        out = out_dir / f"{src.stem}.dwg"
        try:
            subprocess.run(
                [exe, "--input", str(src), "--output", str(out), "--format", "dwg"],
                check=True, capture_output=True, timeout=300,
            )
            return ConverterResult(True, str(src), str(out), backend)
        except subprocess.CalledProcessError as e:
            return ConverterResult(False, str(src), message=f"{backend} failed: {e.stderr.decode(errors='replace')}")
        except subprocess.TimeoutExpired:
            return ConverterResult(False, str(src), message=f"{backend} conversion timed out")

