"""
Audio management module for Reversi game.
Handles all audio concatenation, sound effects, and audio processing.
"""

from pydub import AudioSegment as seg
import io
from pathlib import Path

# Audio parameters
SPACE_DUR = 120
BASE_FREQ = 16000
STEP = 1000
SOUNDS_DIR = Path(__file__).resolve().parent / "sounds"


# ==================
# AUDIO UTILITIES
# ==================

def _pitch(sound, freq):
    """Change the pitch of a sound by resampling."""
    return sound._spawn(sound.raw_data, overrides={"frame_rate": freq})


def _pan(x):
    """Calculate pan value (-1.0 to 1.0) from board column (0-7)."""
    return 2 * x / 7 - 1.0


def _freq(y):
    """Calculate frequency from board row (0-7)."""
    return BASE_FREQ + y * STEP


def _normalize(s, ms):
    """Normalize sound duration to exactly ms milliseconds."""
    if len(s) > ms:
        return s[:ms]
    return s + seg.silent(ms - len(s))


def _to_bytes(s):
    """Convert AudioSegment to WAV bytes."""
    buf = io.BytesIO()
    s.export(buf, format="wav")
    return buf.getvalue()


def _prepend_silence(s, ms=50):
    """Prepend silence (in milliseconds) to prevent audio clipping."""
    return seg.silent(ms) + s


def _load_sound(name):
    """Load a sound file from the sounds directory."""
    return seg.from_wav(str(SOUNDS_DIR / name))


# ==================
# AUDIO CONCAT
# ==================

def concat_audio(clips, gap_ms=350):
    """
    Concatenate multiple audio clips with gaps between them.
    
    Args:
        clips: List of audio byte data
        gap_ms: Gap in milliseconds between clips (default: 350ms)
    
    Returns:
        Combined audio as bytes, or None if no clips
    """
    combined = seg.silent(0)
    first = True

    for clip in clips:
        if not clip:
            continue

        if not first:
            combined += seg.silent(gap_ms)
        first = False

        segment = seg.from_file(io.BytesIO(clip), format="wav")
        combined += segment

    if len(combined) == 0:
        return None

    buffer = io.BytesIO()
    combined.export(buffer, format="wav")
    return buffer.getvalue()


# ==================
# SOUND EFFECTS
# ==================

def disk_wipwip(is_white, coords):
    """
    Generate disk placement sound with piece flip sounds.
    
    Combines:
    - Disk placement sound
    - Flips with pitch and pan based on board position
    
    Args:
        is_white: Whether pieces are white (affects flip sound)
        coords: List of (col, row) tuples for flipped pieces
    
    Returns:
        Audio bytes
    """
    base_disk = _load_sound("disk.wav")
    base_flip = _load_sound("white.wav" if is_white else "black.wav")

    result = seg.silent(0)

    # Add disk sound at the start
    result += _normalize(base_disk, SPACE_DUR)

    # Add flips with spatial audio (pitch based on row, pan based on column)
    for x, y in coords:
        s = _pitch(base_flip, _freq(y)).pan(_pan(x))
        s = _normalize(s, SPACE_DUR)
        result += s

    result = _prepend_silence(result)
    return _to_bytes(result)


def error(x, y):
    """
    Generate error sound with pitch/pan based on board position.
    
    Args:
        x: Column (0-7)
        y: Row (0-7)
    
    Returns:
        Audio bytes
    """
    base = _load_sound("error.wav")

    s = _pitch(base, _freq(y)).pan(_pan(x))
    s = _normalize(s, SPACE_DUR)
    s = _prepend_silence(s)

    return _to_bytes(s)


def pass_sound():
    """
    Generate 'pass' sound when a player passes.
    
    Returns:
        Audio bytes
    """
    base = _load_sound("pass.wav")
    base = _prepend_silence(base)
    return _to_bytes(base)
