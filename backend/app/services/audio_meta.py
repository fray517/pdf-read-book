"""Длительность аудио через ffprobe."""

import json
import logging
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)


def audio_duration_sec(path: Path) -> float:
    """Возвращает длительность файла в секундах."""
    try:
        result = subprocess.run(
            [
                "ffprobe",
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "json",
                str(path),
            ],
            capture_output=True,
            text=True,
            check=True,
            timeout=60,
        )
        data = json.loads(result.stdout)
        dur = float(data["format"]["duration"])
        return round(dur, 3)
    except (OSError, subprocess.CalledProcessError, KeyError, ValueError) as e:
        logger.warning("ffprobe failed for %s: %s", path, e)
        return 0.0
