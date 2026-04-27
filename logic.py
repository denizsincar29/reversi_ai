# -*- coding: utf-8 -*-

import gradio as gr
from reversi import Board, AlphaBetaPlayer, MinimaxPlayer
from audio import audio as audio_manager

def get_player_instance(player_type, depth):
    if player_type == "AlphaBeta":
        return AlphaBetaPlayer(depth=int(depth))
    return MinimaxPlayer(depth=int(depth))

def _changed_to_player(before: Board, after: Board, player: str):
    changed = []
    for r in range(8):
        for c in range(8):
            if before.grid[r][c] != after.grid[r][c] and after.grid[r][c] == player:
                changed.append((c, r))
    return changed

def _check_game_end(board: Board):
    """Return (is_game_over, announcement_text) tuple."""
    winner = board.get_winner()
    if winner == 'N':
        return False, ""

    black_count = board.count('B')
    white_count = board.count('W')
    if winner == 'B':
        return True, f"Game Over. Black wins {black_count} to {white_count}."
    if winner == 'W':
        return True, f"Game Over. White wins {white_count} to {black_count}."
    if winner == 'D':
        return True, f"Game Over. Draw at {black_count} to {white_count}."
    return False, ""

def compose_status(board: Board, status_text: str):
    is_over, game_end = _check_game_end(board)
    if is_over:
        return f"{status_text}. {game_end}" if status_text else game_end
    return status_text

def announce_to_screenreader(status_text: str):
    return gr.update(
        value=(
            "<div id=\"sr-announce\" aria-live=\"polite\" aria-atomic=\"true\" "
            f"style=\"position: absolute; left: -9999px;\">{status_text}</div>"
        )
    )

def process_turn(board: Board, r, c, human_color, ai_type, ai_depth):
    audio_manager.clear()
    status_parts = []

    # 1. Check if game is already over
    if board.is_terminal():
        return board, "Game already finished"

    # 2. Human turn
    if board.turn == human_color:
        legal_moves = board.legal_moves(human_color)

        if not legal_moves:
            # Player must pass
            status_parts.append(f"{'Black' if human_color == 'B' else 'White'} (You) passed")
            audio_manager.pass_sound()
            board.turn = board.other(human_color)
        else:
            if (r, c) not in legal_moves:
                audio_manager.error(c, r)
                return board, f"Invalid move at {Board.coord_label(r, c)}"

            # Apply human move
            new_board = board.apply_move(human_color, (r, c))
            changed = _changed_to_player(board, new_board, human_color)
            audio_manager.disk_wipwip(is_white=(human_color == 'W'), coords=changed)

            flip_count = len(changed) - 1
            move_status = f"You played at {Board.coord_label(r, c)}"
            if flip_count > 0:
                move_status += f" and flipped {flip_count} disk{'s' if flip_count != 1 else ''}"
            status_parts.append(move_status)
            board = new_board

    # 3. AI turns (loop as long as it's AI's turn and game not over)
    while board.turn != human_color and not board.is_terminal():
        ai_color = board.turn
        ai_moves = board.legal_moves(ai_color)

        if not ai_moves:
            status_parts.append(f"{ai_type} ({'Black' if ai_color == 'B' else 'White'}) passed")
            audio_manager.pass_sound()
            board.turn = board.other(ai_color)
        else:
            ai_player = get_player_instance(ai_type, ai_depth)
            move = ai_player.choose_move(board, ai_color)
            if move is None:
                status_parts.append(f"{ai_type} ({'Black' if ai_color == 'B' else 'White'}) passed")
                audio_manager.pass_sound()
                board.turn = board.other(ai_color)
                continue

            new_board = board.apply_move(ai_color, move)
            changed = _changed_to_player(board, new_board, ai_color)
            audio_manager.disk_wipwip(is_white=(ai_color == 'W'), coords=changed)

            flip_count = len(changed) - 1
            ai_status = f"{ai_type} ({'Black' if ai_color == 'B' else 'White'}) played {Board.coord_label(move[0], move[1])}"
            if flip_count > 0:
                ai_status += f" and flipped {flip_count} disk{'s' if flip_count != 1 else ''}"

            status_parts.append(ai_status)
            board = new_board

            # If human has no moves, pass back to AI to continue the loop
            if not board.legal_moves(human_color) and not board.is_terminal():
                status_parts.append(f"{'Black' if human_color == 'B' else 'White'} (You) passed, you have no legal moves, press on any square to pass")
                audio_manager.pass_sound()
                board.turn = ai_color

    return board, ". ".join(status_parts)
