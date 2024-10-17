import sounddevice as sd
import gradio as gr

def stream_handler(data):
    sr, chunk = data
    stream.write(chunk)


with gr.Blocks() as demo:
    mic = gr.Audio(sources="microphone")
    mic.stream(stream_handler, [mic], [], time_limit=10, stream_every=1)

with sd.OutputStream(48000, channels=2, dtype='int16') as stream:
    demo.launch()