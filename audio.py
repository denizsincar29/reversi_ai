"""
Audio management module for Reversi game.
Handles all audio concatenation, sound effects, and audio processing.
"""

from pydub import AudioSegment as seg
import io
from pathlib import Path


class AudioManager:
    """Manages all audio operations for the Reversi game."""
    
    # Audio parameters
    SPACE_DUR = 120
    BASE_FREQ = 16000
    STEP = 1000
    SOUNDS_DIR = Path(__file__).resolve().parent / "sounds"
    
    def __init__(self):
        self._collected = []

    def _pitch(self, sound, freq):
        """Change the pitch of a sound by resampling."""
        return sound._spawn(sound.raw_data, overrides={"frame_rate": freq})
    
    def _pan(self, x):
        """Calculate pan value (-1.0 to 1.0) from board column (0-7)."""
        return 2 * x / 7 - 1.0
    
    def _freq(self, y):
        """Calculate frequency from board row (0-7)."""
        return self.BASE_FREQ + y * self.STEP
    
    def _normalize(self, s, ms):
        """Normalize sound duration to exactly ms milliseconds."""
        if len(s) > ms:
            return s[:ms]
        return s + seg.silent(ms - len(s))
    
    def _to_bytes(self, s):
        """Convert AudioSegment to WAV bytes."""
        buf = io.BytesIO()
        s.export(buf, format="wav")
        return buf.getvalue()
    
    def _prepend_silence(self, s, ms=50):
        """Prepend silence (in milliseconds) to prevent audio clipping."""
        return seg.silent(ms) + s
    
    def _load_sound(self, name):
        """Load a sound file from the sounds directory."""
        return seg.from_wav(str(self.SOUNDS_DIR / name))
    
    # ==================
    # PUBLIC METHODS
    # ==================
    
    def clear(self):
        """Clear collected audio clips."""
        self._collected = []

    def add_clip(self, clip_bytes):
        """Add raw audio bytes to the collection."""
        if clip_bytes:
            self._collected.append(clip_bytes)

    def get_audio_bytes(self, gap_ms=350):
        """
        Concatenate all collected audio clips and clear the collection.
        
        Returns:
            Combined audio as bytes, or None if no clips
        """
        if not self._collected:
            return None

        combined = seg.silent(0)
        first = True

        for clip in self._collected:
            if not clip:
                continue

            if not first:
                combined += seg.silent(gap_ms)
            first = False

            segment = seg.from_file(io.BytesIO(clip), format="wav")
            combined += segment

        self.clear()

        if len(combined) == 0:
            return None

        buffer = io.BytesIO()
        combined.export(buffer, format="wav")
        return buffer.getvalue()
    
    def disk_wipwip(self, is_white, coords, collect=True):
        """
        Generate disk placement sound with piece flip sounds.
        """
        base_disk = self._load_sound("disk.wav")
        base_flip = self._load_sound("white.wav" if is_white else "black.wav")

        result = seg.silent(0)

        # Add disk sound at the start
        result += self._normalize(base_disk, self.SPACE_DUR)

        # Add flips with spatial audio (pitch based on row, pan based on column)
        for x, y in coords:
            s = self._pitch(base_flip, self._freq(y)).pan(self._pan(x))
            s = self._normalize(s, self.SPACE_DUR)
            result += s

        result = self._prepend_silence(result)
        bytes_data = self._to_bytes(result)

        if collect:
            self.add_clip(bytes_data)
        return bytes_data
    
    def error(self, x, y, collect=True):
        """
        Generate error sound with pitch/pan based on board position.
        """
        base = self._load_sound("error.wav")

        s = self._pitch(base, self._freq(y)).pan(self._pan(x))
        s = self._normalize(s, self.SPACE_DUR)
        s = self._prepend_silence(s)

        bytes_data = self._to_bytes(s)
        if collect:
            self.add_clip(bytes_data)
        return bytes_data
    
    def pass_sound(self, collect=True):
        """
        Generate 'pass' sound when a player passes.
        """
        base = self._load_sound("pass.wav")
        base = self._prepend_silence(base)
        bytes_data = self._to_bytes(base)
        if collect:
            self.add_clip(bytes_data)
        return bytes_data


# ==================
# MODULE INSTANCE
# ==================

audio = AudioManager()
