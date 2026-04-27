# -*- coding: utf-8 -*-

import gradio as gr
from reversi import Board, AlphaBetaPlayer, MinimaxPlayer
from audio import audio as audio_manager


# ====== LOGIC ======

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


def _coord_list_text(moves):
    if not moves:
        return "none"
    return ", ".join(_coord_label(r, c) for r, c in moves)


def _changed_to_player(before: Board, after: Board, player: str):
    changed = []
    for r in range(8):
        for c in range(8):
            if before.grid[r][c] != after.grid[r][c] and after.grid[r][c] == player:
                changed.append((c, r))
    return changed


def _render_advantage(board: Board):
    black_count = board.count('B')
    white_count = board.count('W')
    diff = abs(black_count - white_count)

    if black_count > white_count:
        summary = f"Black advantage: +{diff} ({black_count} to {white_count})"
        leader_class = "leader-black"
    elif white_count > black_count:
        summary = f"White advantage: +{diff} ({white_count} to {black_count})"
        leader_class = "leader-white"
    else:
        summary = f"No advantage: tied at {black_count} each"
        leader_class = "leader-tie"

    return (
        f"<div id='advantage-panel' class='info-card {leader_class}' data-announce='{summary}'>"
        f"<strong>Advantage</strong><br>{summary}</div>"
    )


def _render_legal_moves(board: Board):
    black_moves = board.legal_moves('B')
    moves_text = _coord_list_text(black_moves)
    summary = f"Black legal moves: {moves_text}"
    return (
        f"<div id='legal-panel' class='info-card legal-card' data-announce='{summary}'>"
        f"<strong>Legal Moves (Black)</strong><br>{moves_text}</div>"
    )


def _check_game_end(board: Board):
    """Return (is_game_over, announcement_text) tuple."""
    if not board.is_terminal():
        return False, ""

    black_count = board.count('B')
    white_count = board.count('W')
    winner = board.get_winner()
    if winner == 'B':
        return True, f"Game Over. Black wins {black_count} to {white_count}."
    if winner == 'W':
        return True, f"Game Over. White wins {white_count} to {black_count}."
    return True, f"Game Over. Draw at {black_count} to {white_count}."


def _compose_status(board: Board, status_text: str):
    is_over, game_end = _check_game_end(board)
    if is_over:
        if status_text:
            return f"{status_text} {game_end}"
        return game_end
    return status_text


def _announce_to_screenreader(status_text: str):
    return gr.update(
        value=(
            "<div id=\"sr-announce\" aria-live=\"polite\" aria-atomic=\"true\" "
            f"style=\"position: absolute; left: -9999px;\">{status_text}</div>"
        )
    )


def _apply_white_turn(board: Board, status_parts, clips, alphabeta_depth):
    if board.is_terminal():
        return board, status_parts, clips

    white_moves = board.legal_moves('W')
    if not white_moves:
        status_parts.append("AlphaBeta (White) pass")
        clips.append(audio_manager.pass_sound())
        return board, status_parts, clips

    ai = AlphaBetaPlayer(depth=int(alphabeta_depth))
    ai_move_pos = ai.choose_move(board, 'W')
    if ai_move_pos is None:
        status_parts.append("AlphaBeta (White) pass")
        clips.append(audio_manager.pass_sound())
        return board, status_parts, clips

    ai_board = board.apply_move('W', ai_move_pos)
    ai_changed = _changed_to_player(board, ai_board, 'W')
    ai_audio = audio_manager.disk_wipwip(is_white=True, coords=ai_changed)
    ai_flip_count = len(ai_changed) - 1

    ai_coord = _coord_label(ai_move_pos[0], ai_move_pos[1])
    ai_status = f"AlphaBeta (White) played {ai_coord}"
    if ai_flip_count > 0:
        ai_status += f" and flipped {ai_flip_count} disk{'s' if ai_flip_count != 1 else ''}"
    status_parts.append(ai_status)
    clips.append(ai_audio)

    return ai_board, status_parts, clips


def handle_turn(board: Board, row, col, alphabeta_depth):
    row = int(row)
    col = int(col)
    coord = _coord_label(row, col)

    if board.is_terminal():
        return board, "Game already finished", None

    black_moves = board.legal_moves('B')
    if not black_moves:
        return board, "Black has no legal moves. Use Play with Minimax.", audio_manager.pass_sound()

    if (row, col) not in black_moves:
        return board, f"Invalid move at {coord}", audio_manager.error(col, row)

    player_board = board.apply_move('B', (row, col))
    player_changed = _changed_to_player(board, player_board, 'B')
    player_audio = audio_manager.disk_wipwip(is_white=False, coords=player_changed)
    player_flip_count = len(player_changed) - 1

    status_parts = [f"You played black at {coord}"]
    if player_flip_count > 0:
        status_parts[0] += f" and flipped {player_flip_count} disk{'s' if player_flip_count != 1 else ''}"

    clips = [player_audio]
    ai_board, status_parts, clips = _apply_white_turn(player_board, status_parts, clips, alphabeta_depth)
    return ai_board, ". ".join(status_parts), audio_manager.concat_audio(clips)


def play_minimax_turn(board: Board, minimax_depth, alphabeta_depth):
    if board.is_terminal():
        return board, "Game already finished", None

    status_parts = []
    clips = []

    black_moves = board.legal_moves('B')
    if black_moves:
        minimax = MinimaxPlayer(depth=int(minimax_depth))
        black_move = minimax.choose_move(board, 'B')
        if black_move is None or black_move not in black_moves:
            black_move = black_moves[0]

        black_board = board.apply_move('B', black_move)
        black_changed = _changed_to_player(board, black_board, 'B')
        black_audio = audio_manager.disk_wipwip(is_white=False, coords=black_changed)
        black_flip_count = len(black_changed) - 1

        black_coord = _coord_label(black_move[0], black_move[1])
        black_status = f"Minimax (Black) played {black_coord}"
        if black_flip_count > 0:
            black_status += f" and flipped {black_flip_count} disk{'s' if black_flip_count != 1 else ''}"
        status_parts.append(black_status)
        clips.append(black_audio)
    else:
        black_board = board
        status_parts.append("Minimax (Black) pass")
        clips.append(audio_manager.pass_sound())

    after_white_board, status_parts, clips = _apply_white_turn(
        black_board,
        status_parts,
        clips,
        alphabeta_depth,
    )

    return after_white_board, ". ".join(status_parts), audio_manager.concat_audio(clips)


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


def _build_ui_payload(board: Board, status_text: str, audio_clip):
    final_status = _compose_status(board, status_text)
    return [
        board,
        final_status,
        audio_clip,
        render_board(board),
        gr.update(value=final_status),
        _screenreader_text(board, final_status),
        _announce_to_screenreader(final_status),
        gr.update(value=_render_advantage(board)),
        gr.update(value=_render_legal_moves(board)),
        *[gr.update(value=lbl) for lbl in _button_labels(board)],
    ]


def _play_human_turn(board: Board, alphabeta_depth, row: int, col: int):
    next_board, status_text, audio_clip = handle_turn(board, row, col, alphabeta_depth)
    return _build_ui_payload(next_board, status_text, audio_clip)


def _play_minimax_vs_alphabeta(board: Board, minimax_depth, alphabeta_depth):
    next_board, status_text, audio_clip = play_minimax_turn(board, minimax_depth, alphabeta_depth)
    return _build_ui_payload(next_board, status_text, audio_clip)


# ====== UI ======

APP_CSS = """
.info-card {
    border-radius: 10px;
    padding: 12px;
    margin-bottom: 10px;
    border: 1px solid #d9d9d9;
    font-size: 14px;
}

.leader-black {
    background: #eef6ff;
    border-color: #8bb8ea;
    color: #103d6b;
}

.leader-white {
    background: #fff7ea;
    border-color: #edc88a;
    color: #6a4200;
}

.leader-tie {
    background: #f5f5f5;
    color: #333333;
}

.legal-card {
    background: #effaef;
    border-color: #91cc91;
    color: #1f5e1f;
}
"""

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

        function announceFromPanel(panelId, fallbackText) {
            const panel = document.getElementById(panelId);
            const live = document.getElementById('sr-announce');
            if (!live) return;
            const text = panel?.dataset?.announce || fallbackText;
            live.textContent = text;
        }

        document.addEventListener('keydown', function(e) {
            if (e.altKey && (e.key === 'a' || e.key === 'A')) {
                e.preventDefault();
                announceFromPanel('advantage-panel', 'Advantage information unavailable');
                return;
            }

            if (e.altKey && (e.key === 'l' || e.key === 'L')) {
                e.preventDefault();
                announceFromPanel('legal-panel', 'Legal move information unavailable');
                return;
            }

            const buttons = getBoardButtons();
            if (!buttons.length) return;

            const focused = document.activeElement;
            const focusedIdx = buttons.indexOf(focused);
            if (focusedIdx === -1) return;

            const cols = 8;
            let nextIdx = focusedIdx;

            if (e.key === 'ArrowUp' && focusedIdx >= cols) nextIdx = focusedIdx - cols;
            else if (e.key === 'ArrowDown' && focusedIdx < cols * (cols - 1)) nextIdx = focusedIdx + cols;
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

with gr.Blocks(css=APP_CSS) as demo:

    state = gr.State(Board())
    status_state = gr.State("")

    gr.Markdown("## Reversi (audio-first UI)")

    with gr.Accordion("Settings", open=True):
        alphabeta_depth = gr.Slider(
            minimum=1,
            maximum=6,
            step=1,
            value=3,
            label="AlphaBeta depth (White AI)",
        )
        minimax_depth = gr.Slider(
            minimum=1,
            maximum=6,
            step=1,
            value=3,
            label="Minimax depth (Black autoplay)",
        )
        gr.Markdown(
            "Depth examples and notes:\n"
            "- Depth 2: fast, beginner-level search.\n"
            "- Depth 3: recommended default, good speed/strength balance (optimal for most CPUs).\n"
            "- Depth 4: very strong, noticeably slower but usually better moves.\n"
            "- Depth 5-6: strongest settings, can be slow on each move."
        )

    gr.Markdown("Hotkeys: Alt+A announces advantage, Alt+L announces legal moves.")

    # Aria-live region for screen reader announcements
    sr_announcement = gr.HTML(value='<div id="sr-announce" aria-live="polite" aria-atomic="true" style="position: absolute; left: -9999px;"></div>')

    advantage_view = gr.HTML(value=_render_advantage(Board()))
    legal_moves_view = gr.HTML(value=_render_legal_moves(Board()))

    with gr.Row():
        board_view = gr.HTML()
        with gr.Column(scale=1):
            play_minimax_btn = gr.Button("Play with Minimax (Black)")
            new_btn = gr.Button("New Game")

    status = gr.Textbox(label="Status", value="")
    sr_text = gr.Textbox(label="Screen Reader Announcements", lines=10, interactive=False, visible=False)

    audio_output = gr.Audio(autoplay=True, interactive=False, label="")

    # ====== BUTTONS 8x8 ======

    buttons = []
    for r in range(8):
        with gr.Row():
            row_btns = []
            for c in range(8):
                btn = gr.Button(_button_labels(Board())[r * 8 + c], scale=1)
                row_btns.append(btn)
            buttons.append(row_btns)

    flat_buttons = [btn for row in buttons for btn in row]
    event_outputs = [
        state,
        status_state,
        audio_output,
        board_view,
        status,
        sr_text,
        sr_announcement,
        advantage_view,
        legal_moves_view,
        *flat_buttons,
    ]

    # ====== EVENTS ======

    for r in range(8):
        for c in range(8):
            buttons[r][c].click(
                fn=lambda board, ab_depth, r=r, c=c: _play_human_turn(board, ab_depth, r, c),
                inputs=[state, alphabeta_depth],
                outputs=event_outputs,
            )

    play_minimax_btn.click(
        fn=_play_minimax_vs_alphabeta,
        inputs=[state, minimax_depth, alphabeta_depth],
        outputs=event_outputs,
    )

    new_btn.click(
        fn=lambda: _build_ui_payload(*new_game()),
        outputs=event_outputs,
        api_name="new_game",
    )

    # initial render
    demo.load(
        fn=lambda: _build_ui_payload(*new_game()),
        outputs=event_outputs,
    )

# ====== RUN ======

def run_app():
    demo.launch(js=APP_JS, footer_links=["api"])


if __name__ == "__main__":
    run_app()