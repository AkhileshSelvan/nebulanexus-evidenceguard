"""Local OCR engine wrapper (Tesseract via ``pytesseract``).

Responsibilities:
  * report — honestly — whether a usable Tesseract binary is present;
  * run OCR on a single PIL image and return text + per-word boxes + a mean
    confidence in [0, 1].

This module never fabricates output. If Tesseract is missing, callers get a
clear status and no text.
"""

from __future__ import annotations

import os
import shutil
from dataclasses import dataclass, field
from functools import lru_cache

try:  # Pillow is a hard dependency of this module.
    from PIL import Image
except Exception as exc:  # pragma: no cover - install error surfaces immediately
    raise ImportError("modules.ocr requires Pillow ('pip install pillow')") from exc

try:
    import pytesseract
    from pytesseract import TesseractError, TesseractNotFoundError
except Exception as exc:  # pragma: no cover
    raise ImportError(
        "modules.ocr requires pytesseract ('pip install pytesseract')"
    ) from exc


DEFAULT_LANG = "eng"

# Common Windows install locations pytesseract will not find on its own.
_WINDOWS_CANDIDATES = (
    r"C:\Program Files\Tesseract-OCR\tesseract.exe",
    r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
    os.path.expandvars(r"%LOCALAPPDATA%\Tesseract-OCR\tesseract.exe"),
    os.path.expandvars(r"%USERPROFILE%\scoop\shims\tesseract.exe"),
    r"C:\ProgramData\chocolatey\bin\tesseract.exe",
)


def _resolve_binary() -> str | None:
    """Return a path to a Tesseract executable, or ``None`` if none is found."""
    # 1. explicit override
    env = os.getenv("TESSERACT_CMD") or os.getenv("TESSERACT_PATH")
    if env and os.path.isfile(env):
        return env
    # 2. whatever pytesseract is already pointed at (default: "tesseract")
    configured = getattr(pytesseract.pytesseract, "tesseract_cmd", "tesseract")
    if os.path.isfile(configured):
        return configured
    on_path = shutil.which(configured) or shutil.which("tesseract")
    if on_path:
        return on_path
    # 3. well-known Windows paths
    for candidate in _WINDOWS_CANDIDATES:
        if candidate and os.path.isfile(candidate):
            return candidate
    return None


@lru_cache(maxsize=1)
def tesseract_status() -> dict[str, object]:
    """Detect Tesseract once per process.

    Returns a dict: ``{"available": bool, "path": str|None, "version": str|None,
    "reason": str|None}``.
    """
    binary = _resolve_binary()
    if binary is None:
        return {
            "available": False,
            "path": None,
            "version": None,
            "reason": (
                "Tesseract executable not found. Install it and/or set the "
                "TESSERACT_CMD environment variable. On Windows: "
                "https://github.com/UB-Mannheim/tesseract/wiki"
            ),
        }
    pytesseract.pytesseract.tesseract_cmd = binary
    try:
        version = str(pytesseract.get_tesseract_version())
    except (TesseractNotFoundError, TesseractError, OSError) as exc:
        return {
            "available": False,
            "path": binary,
            "version": None,
            "reason": f"Tesseract at {binary!r} could not be executed: {exc}",
        }
    return {"available": True, "path": binary, "version": version, "reason": None}


def is_available() -> bool:
    return bool(tesseract_status()["available"])


@dataclass
class OcrWord:
    text: str
    conf: float  # [0, 1]
    left: int
    top: int
    width: int
    height: int


@dataclass
class OcrResult:
    text: str = ""
    words: list[OcrWord] = field(default_factory=list)
    mean_conf: float = 0.0  # [0, 1], 0.0 when no words were read
    ran: bool = False       # True only if Tesseract actually executed


def run_ocr(image: "Image.Image", lang: str = DEFAULT_LANG) -> OcrResult:
    """OCR a single image. Returns an empty, ``ran=False`` result if Tesseract
    is unavailable — it does not raise for that case."""
    status = tesseract_status()
    if not status["available"]:
        return OcrResult()

    pytesseract.pytesseract.tesseract_cmd = str(status["path"])
    # --oem 3: default LSTM engine. --psm 3: fully automatic page segmentation.
    config = "--oem 3 --psm 3"
    data = pytesseract.image_to_data(
        image, lang=lang, config=config, output_type=pytesseract.Output.DICT
    )

    words: list[OcrWord] = []
    confs: list[float] = []
    n = len(data.get("text", []))
    for i in range(n):
        raw = (data["text"][i] or "").strip()
        if not raw:
            continue
        try:
            c = float(data["conf"][i])
        except (TypeError, ValueError):
            c = -1.0
        if c < 0:  # Tesseract uses -1 for non-text blocks
            continue
        conf01 = max(0.0, min(1.0, c / 100.0))
        words.append(
            OcrWord(
                text=raw,
                conf=conf01,
                left=int(data["left"][i]),
                top=int(data["top"][i]),
                width=int(data["width"][i]),
                height=int(data["height"][i]),
            )
        )
        confs.append(conf01)

    text = pytesseract.image_to_string(image, lang=lang, config=config)
    mean_conf = round(sum(confs) / len(confs), 4) if confs else 0.0
    return OcrResult(text=text, words=words, mean_conf=mean_conf, ran=True)


def detect_orientation(image: "Image.Image") -> int:
    """Best-effort page rotation via Tesseract OSD. Returns degrees to rotate
    clockwise to upright (0/90/180/270); 0 if OSD is unavailable or unsure."""
    if not is_available():
        return 0
    try:
        osd = pytesseract.image_to_osd(image, output_type=pytesseract.Output.DICT)
    except (TesseractError, TesseractNotFoundError, OSError, ValueError):
        return 0
    try:
        rotate = int(osd.get("rotate", 0)) % 360
    except (TypeError, ValueError):
        return 0
    return rotate if rotate in (90, 180, 270) else 0
