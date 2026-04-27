import gradio as gr
import os
import requests
import threading
import time

def run_app():
    with gr.Blocks() as demo:
        gr.Markdown("test")
        # Add a dummy audio component to see if it helps with path registration
        gr.Audio("sounds/black.wav", visible=False)
    base_dir = os.path.dirname(os.path.abspath(__file__))
    sounds_path = os.path.join(base_dir, "sounds")
    demo.launch(allowed_paths=[sounds_path], server_port=7862, prevent_thread_lock=True)

t = threading.Thread(target=run_app)
t.daemon = True
t.start()
time.sleep(10)

base_dir = os.path.dirname(os.path.abspath(__file__))
abs_path = os.path.join(base_dir, "sounds", "black.wav")

urls = [
    "http://127.0.0.1:7862/file=sounds/black.wav",
    f"http://127.0.0.1:7862/file={abs_path}",
    "http://127.0.0.1:7862/file/sounds/black.wav",
    f"http://127.0.0.1:7862/file/{abs_path}"
]

for url in urls:
    try:
        r = requests.head(url)
        print(f"{url}: {r.status_code}")
    except Exception as e:
        print(f"{url}: Error {e}")
