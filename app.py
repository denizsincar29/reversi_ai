# -*- coding: utf-8 -*-

import gradio as gr
from reversi import Board
import logic
import os
import json

# ====== ASSET LOADING ======

def load_asset(filename):
    path = os.path.join("assets", filename)
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    return ""

APP_CSS = load_asset("style.css")
APP_JS = load_asset("script.js")
GR_MARKDOWN = load_asset("info.md")

# ====== UI HELPERS ======

import time

def _build_ui_payload(board: Board, status_text: str, moves_metadata=None):
    if moves_metadata is None:
        moves_metadata = []
    final_status = logic.compose_status(board, status_text)
    adv_html, _ = board.get_advantage_info()
    legal_html, _ = board.get_legal_moves_info(board.turn)

    # Use a div with data-attribute for more reliable JS access
    # Include a timestamp to ensure the attribute always changes and triggers JS update
    payload = {
        "moves": moves_metadata,
        "ts": time.time()
    }
    escaped_metadata = json.dumps(payload).replace("'", "&apos;")
    metadata_html = f"<div id='move-metadata' data-payload='{escaped_metadata}'></div>"

    return [
        board,
        final_status,
        metadata_html,
        final_status,
        board.get_screenreader_text(final_status),
        logic.announce_to_screenreader(final_status),
        gr.update(value=adv_html),
        gr.update(value=legal_html),
        *[gr.update(value=lbl) for lbl in board.get_button_labels()],
    ]

def handle_turn(board, r, c, human_color, ai_type, ai_depth):
    new_board, status, metadata = logic.process_turn(board, r, c, human_color, ai_type, ai_depth)
    return _build_ui_payload(new_board, status, metadata)

def handle_assist(board, assist_type, assist_depth, ai_type, ai_depth, human_color):
    if board.turn != human_color:
        return _build_ui_payload(board, "It's not your turn")

    legal_moves = board.legal_moves(human_color)
    if not legal_moves:
        return handle_turn(board, -1, -1, human_color, ai_type, ai_depth)

    assistant = logic.get_player_instance(assist_type, assist_depth)
    move = assistant.choose_move(board, human_color)
    if move is None:
        move = legal_moves[0]

    return handle_turn(board, move[0], move[1], human_color, ai_type, ai_depth)

def handle_new_game(human_color, ai_type, ai_depth):
    board = Board()
    if human_color == 'W':
        return handle_turn(board, -1, -1, human_color, ai_type, ai_depth)
    return _build_ui_payload(board, "New game started. Black goes first.")

# ====== UI ======

with gr.Blocks() as demo:
    state = gr.State(Board())
    status_state = gr.State("")

    gr.Markdown(GR_MARKDOWN)

    with gr.Accordion("Settings", open=False):
        with gr.Row():
            human_color = gr.Radio(choices=[("Black", "B"), ("White", "W")], value="B", label="Your Color")
            ai_type = gr.Radio(choices=["AlphaBeta", "Minimax"], value="AlphaBeta", label="Opponent AI Type")
            ai_depth = gr.Slider(minimum=1, maximum=6, step=1, value=3, label="Opponent AI Depth")

        with gr.Row():
            assist_type = gr.Radio(choices=["AlphaBeta", "Minimax"], value="Minimax", label="Assistant AI Type")
            assist_depth = gr.Slider(minimum=1, maximum=6, step=1, value=3, label="Assistant AI Depth")

    sr_announcement = gr.HTML(value='<div id="sr-announce" aria-live="polite" aria-atomic="true" style="position: absolute; left: -9999px;"></div>')

    with gr.Row():
        # Board Column
        with gr.Column(scale=2, elem_id="board-container"):
            # Chess-style labels A-H top
            with gr.Row(elem_id="col-labels-top"):
                gr.HTML("<div class='edge-label corner'></div>")
                for c in range(8):
                    gr.HTML(f"<div class='edge-label col-label'>{chr(ord('A') + c)}</div>")
                gr.HTML("<div class='edge-label corner'></div>")

            buttons = []
            for r in range(8):
                with gr.Row(elem_id=f"row-{r+1}"):
                    # Row label left
                    gr.HTML(f"<div class='edge-label row-label'>{r+1}</div>")
                    row_btns = []
                    for c in range(8):
                        # Initialize with coordinate for better SR support even before first update
                        initial_label = f"{Board.coord_label(r, c)} empty"
                        btn = gr.Button(initial_label, elem_classes=["board-cell"], min_width=50)
                        row_btns.append(btn)
                    buttons.append(row_btns)
                    # Row label right
                    gr.HTML(f"<div class='edge-label row-label'>{r+1}</div>")

            # Chess-style labels A-H bottom
            with gr.Row(elem_id="col-labels-bottom"):
                gr.HTML("<div class='edge-label corner'></div>")
                for c in range(8):
                    gr.HTML(f"<div class='edge-label col-label'>{chr(ord('A') + c)}</div>")
                gr.HTML("<div class='edge-label corner'></div>")

        # Info Column
        with gr.Column(scale=1):
            status = gr.Textbox(label="Status", value="", interactive=False)
            advantage_view = gr.HTML()
            legal_moves_view = gr.HTML()
            play_assist_btn = gr.Button("AI Assistant Move", variant="primary", elem_id="assist-btn")
            new_btn = gr.Button("New Game", elem_id="new-game-btn")
            gr.Markdown("### Accessibility\nHotkeys: Alt+A announces advantage, Alt+L announces legal moves. Use arrow keys to navigate the board.")

    sr_text = gr.Textbox(label="Screen Reader Announcements", lines=10, interactive=False, visible=False)
    move_metadata_view = gr.HTML(visible=False, elem_id="move-metadata-container")

    flat_buttons = [btn for row in buttons for btn in row]
    event_outputs = [
        state,              # 0
        status_state,       # 1
        move_metadata_view, # 2
        status,             # 3
        sr_text,            # 4
        sr_announcement,    # 5
        advantage_view,     # 6
        legal_moves_view,    # 7
        *flat_buttons,
    ]

    for r in range(8):
        for c in range(8):
            buttons[r][c].click(
                fn=handle_turn,
                inputs=[state, gr.State(r), gr.State(c), human_color, ai_type, ai_depth],
                outputs=event_outputs,
            )

    play_assist_btn.click(
        fn=handle_assist,
        inputs=[state, assist_type, assist_depth, ai_type, ai_depth, human_color],
        outputs=event_outputs,
    )

    new_btn.click(
        fn=handle_new_game,
        inputs=[human_color, ai_type, ai_depth],
        outputs=event_outputs,
    )

    demo.load(
        fn=handle_new_game,
        inputs=[human_color, ai_type, ai_depth],
        outputs=event_outputs,
    )

if __name__ == "__main__":
    # Resolve sounds directory relative to the file location
    base_dir = os.path.dirname(os.path.abspath(__file__))
    sounds_path = os.path.join(base_dir, "sounds")
    demo.launch(css=APP_CSS, js=APP_JS, allowed_paths=[sounds_path])
