from pydub import AudioSegment as seg
import io
from pathlib import Path

SPACE_DUR = 120
BASE_FREQ = 16000
STEP = 1000
SOUNDS_DIR = Path(__file__).resolve().parent / "sounds"


def _pitch(sound, freq):
    return sound._spawn(sound.raw_data, overrides={"frame_rate": freq})


def _pan(x):
    return 2 * x / 7 - 1.0


def _freq(y):
    return BASE_FREQ + y * STEP


def _normalize(s, ms):
    if len(s) > ms:
        return s[:ms]
    return s + seg.silent(ms - len(s))


def _to_bytes(s):
    buf = io.BytesIO()
    s.export(buf, format="wav")
    return buf.getvalue()


def _prepend_silence(s, ms=50):
    """Prepend silence (in milliseconds) to prevent audio clipping."""
    return seg.silent(ms) + s


def _load_sound(name):
    return seg.from_wav(str(SOUNDS_DIR / name))


# =========================
# MAIN FX: disk + wipwip
# =========================

def disk_wipwip(is_white, coords):
    """
    Один цельный звук:
    disk + flips
    """

    base_disk = _load_sound("disk.wav")
    base_flip = _load_sound("white.wav" if is_white else "black.wav")

    result = seg.silent(0)

    # 1) disk в начале
    result += _normalize(base_disk, SPACE_DUR)

    # 2) flips
    for x, y in coords:
        s = _pitch(base_flip, _freq(y)).pan(_pan(x))
        s = _normalize(s, SPACE_DUR)
        result += s

    result = _prepend_silence(result)
    return _to_bytes(result)


# =========================
# ERROR (ТОЛЬКО ОДИН ЗВУК)
# =========================

def error(x, y):
    base = _load_sound("error.wav")

    s = _pitch(base, _freq(y)).pan(_pan(x))
    s = _normalize(s, SPACE_DUR)
    s = _prepend_silence(s)

    return _to_bytes(s)


def pass_sound():
    base = _load_sound("pass.wav")
    base = _prepend_silence(base)
    return _to_bytes(base)