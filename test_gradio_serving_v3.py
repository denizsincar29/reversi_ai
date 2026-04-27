import gradio as gr
import os
import requests
import threading
import time

def run_app():
    with gr.Blocks() as demo:
        gr.Markdown("test")
        # Try using gr.File to see if it allows access
        gr.File(["sounds/black.wav"], label="sounds")
    base_dir = os.path.dirname(os.path.abspath(__file__))
    sounds_path = os.path.join(base_dir, "sounds")
    demo.launch(allowed_paths=[sounds_path], server_port=7863, prevent_thread_lock=True)

t = threading.Thread(target=run_app)
t.daemon = True
t.start()
time.sleep(10)

base_dir = os.path.dirname(os.path.abspath(__file__))
abs_path = os.path.join(base_dir, "sounds", "black.wav")

urls = [
    "http://127.0.0.1:7863/file=sounds/black.wav",
    f"http://127.0.0.1:7863/file={abs_path}",
]

for url in urls:
    try:
        r = requests.head(url)
        print(f"{url}: {r.status_code}")
    except Exception as e:
        print(f"{url}: Error {e}")
