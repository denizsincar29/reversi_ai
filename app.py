# -*- coding: utf-8 -*-

import gradio as gr
from reversi import Board
from audio import audio as audio_manager
import logic
import os

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

def _build_ui_payload(board: Board, status_text: str):
    final_status = logic.compose_status(board, status_text)
    adv_html, _ = board.get_advantage_info()
    legal_html, _ = board.get_legal_moves_info(board.turn)

    return [
        board,
        final_status,
        audio_manager.get_audio_bytes(),
        board.render_html(),
        gr.update(value=final_status),
        board.get_screenreader_text(final_status),
        logic.announce_to_screenreader(final_status),
        gr.update(value=adv_html),
        gr.update(value=legal_html),
        *[gr.update(value=lbl) for lbl in board.get_button_labels()],
    ]

def handle_turn(board, r, c, human_color, ai_type, ai_depth):
    new_board, status = logic.process_turn(board, r, c, human_color, ai_type, ai_depth)
    return _build_ui_payload(new_board, status)

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
    audio_manager.clear()
    board = Board()
    if human_color == 'W':
        return handle_turn(board, -1, -1, human_color, ai_type, ai_depth)
    return _build_ui_payload(board, "New game started. Black goes first.")

# ====== UI ======

with gr.Blocks() as demo:
    state = gr.State(Board())
    status_state = gr.State("")

    gr.Markdown(GR_MARKDOWN)

    with gr.Accordion("Settings", open=True):
        with gr.Row():
            human_color = gr.Radio(choices=[("Black", "B"), ("White", "W")], value="B", label="Your Color")
            ai_type = gr.Radio(choices=["AlphaBeta", "Minimax"], value="AlphaBeta", label="Opponent AI Type")
            ai_depth = gr.Slider(minimum=1, maximum=6, step=1, value=3, label="Opponent AI Depth")

        with gr.Row():
            assist_type = gr.Radio(choices=["AlphaBeta", "Minimax"], value="Minimax", label="Assistant AI Type")
            assist_depth = gr.Slider(minimum=1, maximum=6, step=1, value=3, label="Assistant AI Depth")

    gr.Markdown("Hotkeys: Alt+A announces advantage, Alt+L announces legal moves.")

    sr_announcement = gr.HTML(value='<div id="sr-announce" aria-live="polite" aria-atomic="true" style="position: absolute; left: -9999px;"></div>')

    advantage_view = gr.HTML()
    legal_moves_view = gr.HTML()

    with gr.Row():
        board_view = gr.HTML()
        with gr.Column(scale=1):
            play_assist_btn = gr.Button("AI Assistant Move")
            new_btn = gr.Button("New Game")

    status = gr.Textbox(label="Status", value="")
    sr_text = gr.Textbox(label="Screen Reader Announcements", lines=10, interactive=False, visible=False)

    audio_output = gr.Audio(autoplay=True, interactive=False, label="")

    buttons = []
    for r in range(8):
        with gr.Row():
            row_btns = []
            for c in range(8):
                btn = gr.Button("empty", scale=1)
                row_btns.append(btn)
            buttons.append(row_btns)

    flat_buttons = [btn for row in buttons for btn in row]
    event_outputs = [
        state,              # 0
        status_state,       # 1
        audio_output,       # 2
        board_view,         # 3
        status,             # 4
        sr_text,            # 5
        sr_announcement,    # 6
        advantage_view,     # 7
        legal_moves_view,    # 8
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
    demo.launch(js=APP_JS, css=APP_CSS)
