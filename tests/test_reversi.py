import unittest

from reversi import Board, AlphaBetaPlayer, MinimaxPlayer


class TestBoard(unittest.TestCase):
    def test_initial_counts(self):
        board = Board()
        self.assertEqual(board.count('B'), 2)
        self.assertEqual(board.count('W'), 2)

    def test_initial_legal_moves_black(self):
        board = Board()
        expected = {(2, 3), (3, 2), (4, 5), (5, 4)}
        self.assertEqual(set(board.legal_moves('B')), expected)

    def test_apply_move_flips_disks(self):
        board = Board()
        next_board = board.apply_move('B', (2, 3))

        self.assertEqual(next_board.grid[2][3], 'B')
        self.assertEqual(next_board.grid[3][3], 'B')
        self.assertEqual(next_board.count('B'), 4)
        self.assertEqual(next_board.count('W'), 1)

    def test_apply_move_invalid_raises(self):
        board = Board()
        with self.assertRaises(ValueError):
            board.apply_move('B', (0, 0))

    def test_terminal_and_winner_on_full_board(self):
        board = Board()
        board.grid = [['B' for _ in range(8)] for _ in range(8)]

        self.assertTrue(board.is_terminal())
        self.assertEqual(board.get_winner(), 'B')


class TestPlayers(unittest.TestCase):
    def test_alphabeta_returns_legal_move(self):
        board = Board()
        player = AlphaBetaPlayer(depth=2)
        move = player.choose_move(board, 'W')

        self.assertIn(move, board.legal_moves('W'))

    def test_minimax_returns_legal_move(self):
        board = Board()
        player = MinimaxPlayer(depth=2)
        move = player.choose_move(board, 'B')

        self.assertIn(move, board.legal_moves('B'))


if __name__ == '__main__':
    unittest.main()
