---
title: Reversi Ai
emoji: 💻
colorFrom: gray
colorTo: purple
sdk: gradio
sdk_version: 6.13.0
app_file: app.py
pinned: false
license: mit
short_description: An AI that plays reversi game
---

# Reversi AI (Gradio + audio)

This project runs a small Reversi game where each move plays spatialized audio.

## Audio behavior

- Valid move: one combined sound clip (`disk + flips`) is generated.
- Invalid move: only `error.wav` is played.
- AI pass: `pass.wav` is played.

## Run locally

```bash
python -m main
```

## Requirements

- Python 3.10+

The current build uses WAV assets only, so no extra system audio packages are required.

## Notes

- Sound files are loaded from the local `sounds/` directory.
- Board logic is implemented in `reversi.py`.
