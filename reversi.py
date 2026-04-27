# -*- coding: utf-8 -*-

import time
import random
import math

SIZE = 8

DIRECTIONS = [(-1, -1), (-1, 0), (-1, 1),
              (0, -1),           (0, 1),
              (1, -1),  (1, 0),  (1, 1)]

CORNERS = [0, 7, 56, 63]


# =========================
# Board (2D)
# =========================

class Board:
    def __init__(self):
        self.grid = [['.' for _ in range(SIZE)] for _ in range(SIZE)]
        self.grid[3][3] = 'W'
        self.grid[4][4] = 'W'
        self.grid[3][4] = 'B'
        self.grid[4][3] = 'B'
        self.turn = 'B'

    def clone(self):
        b = Board()
        b.grid = [row.copy() for row in self.grid]
        b.turn = self.turn
        return b

    # ---- Conversion ----

    def to_1d(self):
        return [self.grid[r][c] for r in range(SIZE) for c in range(SIZE)]

    @staticmethod
    def from_1d(arr, turn='B'):
        b = Board()
        for i in range(64):
            r, c = divmod(i, SIZE)
            b.grid[r][c] = arr[i]
        b.turn = turn
        return b

    # ---- Logic ----

    def is_on_board(self, x, y):
        return 0 <= x < SIZE and 0 <= y < SIZE

    def other(self, player):
        return 'W' if player == 'B' else 'B'

    def get_flips(self, player, x, y):
        flips = []
        opponent = self.other(player)

        for dx, dy in DIRECTIONS:
            nx, ny = x + dx, y + dy
            temp = []

            while self.is_on_board(nx, ny):
                piece = self.grid[ny][nx]

                if piece == opponent:
                    temp.append((nx, ny))
                elif piece == player:
                    flips.extend(temp)
                    break
                else:
                    break

                nx += dx
                ny += dy

        return flips

    def legal_moves(self, player):
        moves = []
        for r in range(SIZE):
            for c in range(SIZE):
                if self.grid[r][c] == '.':
                    if self.get_flips(player, c, r):
                        moves.append((r, c))
        return moves

    def apply_move(self, player, move):
        r, c = move
        if move not in self.legal_moves(player):
            raise ValueError(f"Invalid move {move} for player {player}")

        new = self.clone()
        new.grid[r][c] = player
        for fx, fy in self.get_flips(player, c, r):
            new.grid[fy][fx] = player

        new.turn = self.other(player)
        return new

    def count(self, player):
        return sum(row.count(player) for row in self.grid)

    def is_terminal(self):
        return not self.legal_moves('B') and not self.legal_moves('W')

    def get_winner(self):
        b, w = self.count('B'), self.count('W')
        if not self.legal_moves('B') and not self.legal_moves('W'):
            return 'B' if b > w else 'W' if w > b else 'D'
        if b == 0: return 'W'
        if w == 0: return 'B'
        return 'N'

    # ---- Rendering Helpers ----

    @staticmethod
    def coord_label(row, col):
        return f"{chr(ord('A') + col)}{row + 1}"

    @staticmethod
    def piece_name(piece):
        if piece == 'B': return "black"
        if piece == 'W': return "white"
        return "empty"

    def get_button_labels(self):
        labels = []
        for r in range(SIZE):
            for c in range(SIZE):
                coord = self.coord_label(r, c)
                piece = self.piece_name(self.grid[r][c])
                labels.append(f"{coord} {piece}")
        return labels

    def get_advantage_info(self):
        b_count = self.count('B')
        w_count = self.count('W')
        diff = abs(b_count - w_count)

        if b_count > w_count:
            summary = f"Black advantage: +{diff} ({b_count} to {w_count})"
            css_class = "leader-black"
        elif w_count > b_count:
            summary = f"White advantage: +{diff} ({w_count} to {b_count})"
            css_class = "leader-white"
        else:
            summary = f"No advantage: tied at {b_count} each"
            css_class = "leader-tie"

        html = f"<div id='advantage-panel' class='info-card {css_class}' data-announce='{summary}'><strong>Advantage</strong><br>{summary}</div>"
        return html, summary

    def get_legal_moves_info(self, player):
        moves = self.legal_moves(player)
        moves_text = ", ".join(self.coord_label(r, c) for r, c in moves) if moves else "none"
        p_name = "Black" if player == 'B' else "White"
        summary = f"{p_name} legal moves: {moves_text}"
        html = f"<div id='legal-panel' class='info-card legal-card' data-announce='{summary}'><strong>Legal Moves ({p_name})</strong><br>{moves_text}</div>"
        return html, summary

    def get_screenreader_text(self, status_text):
        lines = [f"Announcement: {status_text}", "Board state:"]
        for r in range(SIZE):
            row_cells = []
            for c in range(SIZE):
                row_cells.append(f"{self.coord_label(r, c)} {self.piece_name(self.grid[r][c])}")
            lines.append(", ".join(row_cells))
        return "\n".join(lines)


# =========================
# AI (работает с 1D)
# =========================

class AIUtils:

    @staticmethod
    def other(player):
        return 'W' if player == 'B' else 'B'

    @staticmethod
    def get_flips(board, player, x, y):
        flips = []
        opponent = AIUtils.other(player)

        for dx, dy in DIRECTIONS:
            nx, ny = x + dx, y + dy
            temp = []

            while 0 <= nx < SIZE and 0 <= ny < SIZE:
                idx = ny * SIZE + nx
                piece = board[idx]

                if piece == opponent:
                    temp.append(idx)
                elif piece == player:
                    flips.extend(temp)
                    break
                else:
                    break

                nx += dx
                ny += dy

        return flips

    @staticmethod
    def actions(board, player):
        moves = []
        for i in range(64):
            if board[i] == '.':
                r, c = divmod(i, SIZE)
                if AIUtils.get_flips(board, player, c, r):
                    moves.append(i)
        return moves

    @staticmethod
    def result(board, player, action):
        new = list(board)
        new[action] = player

        r, c = divmod(action, SIZE)
        for idx in AIUtils.get_flips(board, player, c, r):
            new[idx] = player

        return new

    @staticmethod
    def heuristic(board, player):
        opponent = AIUtils.other(player)

        disc = board.count(player) - board.count(opponent)
        mobility = len(AIUtils.actions(board, player)) - len(AIUtils.actions(board, opponent))

        corner_score = 0
        for i in CORNERS:
            if board[i] == player:
                corner_score += 25
            elif board[i] == opponent:
                corner_score -= 25

        return disc + 2 * mobility + corner_score


# =========================
# Players
# =========================

class Player:
    def choose_move(self, board: Board, player: str):
        raise NotImplementedError


class RandomPlayer(Player):
    def choose_move(self, board, player):
        moves = board.legal_moves(player)
        return random.choice(moves) if moves else None


class AlphaBetaPlayer(Player):
    def __init__(self, depth=3):
        self.depth = depth

    def choose_move(self, board, player):
        state = board.to_1d()

        def maxv(s, alpha, beta, d):
            if d == 0:
                return AIUtils.heuristic(s, player), None

            moves = AIUtils.actions(s, player)
            if not moves:
                # Check if other player has moves
                if not AIUtils.actions(s, AIUtils.other(player)):
                    return AIUtils.heuristic(s, player), None
                val, _ = minv(s, alpha, beta, d-1)
                return val, None

            v = -math.inf
            best = None

            for m in moves:
                val, _ = minv(AIUtils.result(s, player, m), alpha, beta, d-1)
                if val > v:
                    v, best = val, m
                alpha = max(alpha, v)
                if alpha >= beta:
                    break

            return v, best

        def minv(s, alpha, beta, d):
            op = AIUtils.other(player)

            if d == 0:
                return AIUtils.heuristic(s, player), None

            moves = AIUtils.actions(s, op)
            if not moves:
                if not AIUtils.actions(s, player):
                    return AIUtils.heuristic(s, player), None
                val, _ = maxv(s, alpha, beta, d-1)
                return val, None

            v = math.inf
            best = None

            for m in moves:
                val, _ = maxv(AIUtils.result(s, op, m), alpha, beta, d-1)
                if val < v:
                    v, best = val, m
                beta = min(beta, v)
                if alpha >= beta:
                    break

            return v, best

        _, move = maxv(state, -math.inf, math.inf, self.depth)
        if move is None:
            return None
        return divmod(move, SIZE)


class MinimaxPlayer(Player):
    def __init__(self, depth=3):
        self.depth = depth

    def choose_move(self, board, player):
        state = board.to_1d()

        def maxv(s, d):
            if d == 0:
                return AIUtils.heuristic(s, player), None

            moves = AIUtils.actions(s, player)
            if not moves:
                if not AIUtils.actions(s, AIUtils.other(player)):
                    return AIUtils.heuristic(s, player), None
                val, _ = minv(s, d - 1)
                return val, None

            best_val = -math.inf
            best_move = None
            for m in moves:
                val, _ = minv(AIUtils.result(s, player, m), d - 1)
                if val > best_val:
                    best_val = val
                    best_move = m
            return best_val, best_move

        def minv(s, d):
            op = AIUtils.other(player)
            if d == 0:
                return AIUtils.heuristic(s, player), None

            moves = AIUtils.actions(s, op)
            if not moves:
                if not AIUtils.actions(s, player):
                    return AIUtils.heuristic(s, player), None
                val, _ = maxv(s, d - 1)
                return val, None

            best_val = math.inf
            best_move = None
            for m in moves:
                val, _ = maxv(AIUtils.result(s, op, m), d - 1)
                if val < best_val:
                    best_val = val
                    best_move = m
            return best_val, best_move

        _, move = maxv(state, self.depth)
        if move is None:
            return None
        return divmod(move, SIZE)
