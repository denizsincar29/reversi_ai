from pydub import AudioSegment as seg

# from c++: sounds[snd].Freq=y*1000+16000;

def wipwip(color, coords: list):
    sound_name = "white" if color else "black"
    space_dur = 120
    a = seg.from_wav(f"sounds/{sound_name}.wav")
    result = seg.empty()
    for x, y in coords:
        if len(result) >0:
            result += seg.silent(duration = space_dur - (len(result) % space_dur))
        freq = y*1000+16000
        pan = 2 * y / 7  -1.0
        result += a._spawn(a.raw_data, overrides={'frame_rate': freq}).pan(pan)
    return result

def error(x, y):
    error_sound = AudioSegment.from_file("sounds/error.wav")
    freq = int(y * 1000 + 16000)
    pan = 2 * y / 7 - 1.0
    modified_sound = error_sound._spawn(error_sound.raw_data, overrides={"frame_rate": freq}).pan(pan)
    return modified_sound