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
    
    def concat_audio(self, clips, gap_ms=350):
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
    
    def disk_wipwip(self, is_white, coords):
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
        return self._to_bytes(result)
    
    def error(self, x, y):
        """
        Generate error sound with pitch/pan based on board position.
        
        Args:
            x: Column (0-7)
            y: Row (0-7)
        
        Returns:
            Audio bytes
        """
        base = self._load_sound("error.wav")

        s = self._pitch(base, self._freq(y)).pan(self._pan(x))
        s = self._normalize(s, self.SPACE_DUR)
        s = self._prepend_silence(s)

        return self._to_bytes(s)
    
    def pass_sound(self):
        """
        Generate 'pass' sound when a player passes.
        
        Returns:
            Audio bytes
        """
        base = self._load_sound("pass.wav")
        base = self._prepend_silence(base)
        return self._to_bytes(base)


# ==================
# MODULE INSTANCE
# ==================

# Create singleton instance for module-level convenience
audio = AudioManager()
