# -*- coding: utf-8 -*-

import gradio as gr
from reversi import Board, AlphaBetaPlayer
import audio


# ====== INIT ======

ai = AlphaBetaPlayer(depth=3)


# ====== ЛОГИКА ======

def new_game():
    return Board(), "New game started", None


def _coord_label(row, col):
    return f"{chr(ord('A') + col)}{row + 1}"


def _piece_name(piece):
    if piece == 'B':
        return "black"
    if piece == 'W':
        return "white"
    return "empty"


def _button_labels(board: Board):
    """Generate accessible button labels for all 64 board squares."""
    labels = []
    for r in range(8):
        for c in range(8):
            coord = _coord_label(r, c)
            piece = _piece_name(board.grid[r][c])
            labels.append(f"{coord} {piece}")
    return labels


def _screenreader_text(board: Board, status_text: str):
    lines = [f"Announcement: {status_text}", "Board state:"]
    for r in range(8):
        row_cells = []
        for c in range(8):
            row_cells.append(f"{_coord_label(r, c)} {_piece_name(board.grid[r][c])}")
        lines.append(", ".join(row_cells))
    return "\n".join(lines)


def _changed_to_player(before: Board, after: Board, player: str):
    changed = []
    for r in range(8):
        for c in range(8):
            if before.grid[r][c] != after.grid[r][c] and after.grid[r][c] == player:
                changed.append((c, r))
    return changed


def player_move(board: Board, row, col):
    row = int(row)
    col = int(col)
    player = 'B'

    moves = board.legal_moves(player)
    coord = _coord_label(row, col)

    if (row, col) not in moves:
        return board, f"Invalid move at {coord}", audio.error(col, row), False

    new_board = board.apply_move(player, (row, col))
    changed = _changed_to_player(board, new_board, player)
    sound = audio.disk_wipwip(is_white=False, coords=changed)
    flip_count = len(changed) - 1  # exclude the placed disk itself

    status_msg = f"You put black disk on {coord}"
    if flip_count > 0:
        status_msg += f" and flipped {flip_count} disk{'s' if flip_count != 1 else ''}"

    return new_board, status_msg, sound, True


def handle_turn(board: Board, row, col):
    row = int(row)
    col = int(col)
    player = 'B'
    coord = _coord_label(row, col)

    if (row, col) not in board.legal_moves(player):
        return board, f"Invalid move at {coord}", audio.error(col, row)

    player_board = board.apply_move(player, (row, col))
    player_changed = _changed_to_player(board, player_board, player)
    player_audio = audio.disk_wipwip(is_white=False, coords=player_changed)
    player_flip_count = len(player_changed) - 1

    status_parts = [f"You put black disk on {coord}"]
    if player_flip_count > 0:
        status_parts[0] += f" and flipped {player_flip_count} disk{'s' if player_flip_count != 1 else ''}"

    ai_player = 'W'
    ai_moves = player_board.legal_moves(ai_player)
    if not ai_moves:
        status_parts.append("AI pass")
        return player_board, ". ".join(status_parts), audio.concat_audio([player_audio, audio.pass_sound()])

    ai_move_pos = ai.choose_move(player_board, ai_player)
    ai_board = player_board.apply_move(ai_player, ai_move_pos)
    ai_changed = _changed_to_player(player_board, ai_board, ai_player)
    ai_audio = audio.disk_wipwip(is_white=True, coords=ai_changed)
    ai_flip_count = len(ai_changed) - 1

    ai_coord = _coord_label(ai_move_pos[0], ai_move_pos[1])
    ai_status = f"AI put white disk on {ai_coord}"
    if ai_flip_count > 0:
        ai_status += f" and flipped {ai_flip_count} disk{'s' if ai_flip_count != 1 else ''}"
    status_parts.append(ai_status)

    return ai_board, ". ".join(status_parts), audio.concat_audio([player_audio, ai_audio])


# ====== UI HELPERS ======

def render_board(board: Board):
    rows = []
    for r in range(8):
        cells = []
        for c in range(8):
            piece = board.grid[r][c]
            symbol = "" if piece == "." else piece
            cells.append(f'<td class="cell cell-{piece}">{symbol}</td>')
        rows.append(f"<tr>{''.join(cells)}</tr>")
    return "<table class='board-grid' aria-label='Reversi board'>" + "".join(rows) + "</table>"


def _announce_to_screenreader(status_text: str):
    return gr.update(value=f'<div id=\"sr-announce\" aria-live=\"polite\" aria-atomic=\"true\" style=\"position: absolute; left: -9999px;\">{status_text}</div>')

def _check_game_end(board: Board):
    """Return (is_game_over, announcement_text) tuple."""
    if not board.is_terminal():
        return False, ""
    
    winner = board.get_winner()
    if winner == 'B':
        return True, "Game Over! Black wins!"
    elif winner == 'W':
        return True, "Game Over! White (AI) wins!"
    elif winner == 'D':
        return True, "Game Over! Draw!"
    return False, ""

# ====== UI ======

APP_JS = """
(() => {
    function getBoardButtons() {
        return Array.from(document.querySelectorAll('button')).filter((b) =>
            /^[A-H][1-8] (black|white|empty)$/.test((b.textContent || '').trim())
        );
    }

    function focusCell(index) {
        const buttons = getBoardButtons();
        if (buttons[index]) {
            buttons[index].focus();
        }
    }

    function hookKeyboardNav() {
        if (window.__reversiNavInstalled) return;
        window.__reversiNavInstalled = true;

        document.addEventListener('keydown', function(e) {
            const buttons = getBoardButtons();
            if (!buttons.length) return;

            const focused = document.activeElement;
            const focusedIdx = buttons.indexOf(focused);
            if (focusedIdx === -1) return;

            const cols = 8;
            let nextIdx = focusedIdx;

            if (e.key === 'ArrowUp') nextIdx = Math.max(0, focusedIdx - cols);
            else if (e.key === 'ArrowDown') nextIdx = Math.min(buttons.length - 1, focusedIdx + cols);
            else if (e.key === 'ArrowLeft' && focusedIdx % cols > 0) nextIdx = focusedIdx - 1;
            else if (e.key === 'ArrowRight' && focusedIdx % cols < cols - 1) nextIdx = focusedIdx + 1;
            else return;

            e.preventDefault();
            focusCell(nextIdx);
        });

        document.addEventListener('click', function(e) {
            if (e.target && e.target.matches('button')) {
                e.target.focus();
            }
        });

        const observer = new MutationObserver(() => {
            const buttons = getBoardButtons();
            if (buttons.length && document.activeElement === document.body) {
                buttons[0].focus();
            }
        });
        observer.observe(document.body, { childList: true, subtree: true });

        window.setTimeout(() => {
            const buttons = getBoardButtons();
            if (buttons.length) {
                buttons[0].focus();
            }
        }, 250);
    }

    hookKeyboardNav();
})();
"""

with gr.Blocks() as demo:

    state = gr.State(Board())
    status_state = gr.State("")

    gr.Markdown("## 🎮 Reversi (audio-first UI)")

    # Aria-live region for screen reader announcements
    sr_announcement = gr.HTML(value='<div id="sr-announce" aria-live="polite" aria-atomic="true" style="position: absolute; left: -9999px;"></div>')

    board_view = gr.HTML()

    status = gr.Textbox(label="Status", value="")
    sr_text = gr.Textbox(label="Screen Reader Announcements", lines=10, interactive=False, visible=False)

    audio = gr.Audio(autoplay=True, interactive=False, label="")

    # координаты клика
    click_row = gr.Number(visible=False)
    click_col = gr.Number(visible=False)

    # ====== КНОПКИ 8x8 ======

    buttons = []
    for r in range(8):
        with gr.Row():
            row_btns = []
            for c in range(8):
                btn = gr.Button(_button_labels(Board())[r * 8 + c], scale=1)
                row_btns.append(btn)
            buttons.append(row_btns)

    new_btn = gr.Button("New Game")

    # ====== EVENTS ======

    for r in range(8):
        for c in range(8):
            buttons[r][c].click(
                fn=lambda r=r, c=c: (r, c),
                outputs=[click_row, click_col]
            ).then(
                fn=handle_turn,
                inputs=[state, click_row, click_col],
                outputs=[state, status_state, audio]
            ).then(
                fn=lambda s, st: _screenreader_text(s, st),
                inputs=[state, status_state],
                outputs=sr_text
            ).then(
                fn=render_board,
                inputs=state,
                outputs=board_view
            ).then(
                fn=lambda st, b: gr.update(value=f"{st} {_check_game_end(b)[1]}") if _check_game_end(b)[0] else gr.update(value=st),
                inputs=[status_state, state],
                outputs=status
            ).then(
                fn=lambda st, b: _announce_to_screenreader(f"{st} {_check_game_end(b)[1]}") if _check_game_end(b)[0] else _announce_to_screenreader(st),
                inputs=[status_state, state],
                outputs=sr_announcement
            ).then(
                fn=lambda b: [gr.update(value=lbl) for lbl in _button_labels(b)],
                inputs=state,
                outputs=[btn for row in buttons for btn in row]
            )

    new_btn.click(
        fn=new_game,
        outputs=[state, status_state, audio],
        api_name="new_game"
    ).then(
        fn=render_board,
        inputs=state,
        outputs=board_view
    ).then(
        fn=lambda st: gr.update(value=st),
        inputs=status_state,
        outputs=status
    ).then(
        fn=_announce_to_screenreader,
        inputs=status_state,
        outputs=sr_announcement
    ).then(
        fn=lambda b: [gr.update(value=lbl) for lbl in _button_labels(b)],
        inputs=state,
        outputs=[btn for row in buttons for btn in row]
    ).then(
        fn=lambda b: _screenreader_text(b, "New game started"),
        inputs=state,
        outputs=sr_text
    )

    # initial render
    demo.load(
        fn=render_board,
        inputs=state,
        outputs=board_view
    ).then(
        fn=lambda b: [gr.update(value=lbl) for lbl in _button_labels(b)],
        inputs=state,
        outputs=[btn for row in buttons for btn in row]
    ).then(
        fn=lambda b: _screenreader_text(b, "New game started"),
        inputs=state,
        outputs=sr_text
    ).then(
        fn=lambda: gr.update(value="New game started"),
        outputs=status
    ).then(
        fn=lambda: _announce_to_screenreader("New game started"),
        outputs=sr_announcement
    )

# ====== RUN ======

def run_app():
    demo.launch(js=APP_JS, footer_links=["api"])


if __name__ == "__main__":
    run_app()