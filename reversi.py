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

    def clone(self):
        b = Board()
        b.grid = [row.copy() for row in self.grid]
        return b

    # ---- Conversion ----

    def to_1d(self):
        return [self.grid[r][c] for r in range(SIZE) for c in range(SIZE)]

    @staticmethod
    def from_1d(arr):
        b = Board()
        for i in range(64):
            r, c = divmod(i, SIZE)
            b.grid[r][c] = arr[i]
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

        return new

    def count(self, player):
        return sum(row.count(player) for row in self.grid)

    def is_terminal(self):
        if self.get_winner() != 'N':
            return True
        return not self.legal_moves('B') and not self.legal_moves('W')

    def get_winner(self):
        flat = self.to_1d()

        if '.' not in flat:
            b, w = flat.count('B'), flat.count('W')
            return 'B' if b > w else 'W' if w > b else 'D'

        if flat.count('B') == 0:
            return 'W'
        if flat.count('W') == 0:
            return 'B'

        return 'N'

    def print(self):
        print("\n   A B C D E F G H")
        for r in range(SIZE):
            row = f"{r+1}| "
            for c in range(SIZE):
                row += self.grid[r][c] + " "
            print(row)

        print(f"B: {self.count('B')} | W: {self.count('W')}")
        print("-" * 30)


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
                return minv(s, alpha, beta, d-1)

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
                return maxv(s, alpha, beta, d-1)

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


# =========================
# Game
# =========================

class Game:
    def __init__(self, black, white):
        self.board = Board()
        self.black = black
        self.white = white

    def play(self):
        board = self.board
        player = 'B'
        passes = 0

        board.print()

        while True:
            current = self.black if player == 'B' else self.white

            moves = board.legal_moves(player)

            if moves:
                passes = 0
                t0 = time.time()

                move = current.choose_move(board, player)

                dt = time.time() - t0

                print(f"{player} -> {move} [{dt:.4f}s]")

                board = board.apply_move(player, move)
                board.print()
            else:
                print(f"{player} pass")
                passes += 1
                if passes >= 2:
                    break

            if board.is_terminal():
                break

            player = board.other(player)

        print("Winner:", board.get_winner())


# =========================
# Run
# =========================

if __name__ == "__main__":
    game = Game(
        black=RandomPlayer(),
        white=AlphaBetaPlayer(depth=3)
    )
    game.play()