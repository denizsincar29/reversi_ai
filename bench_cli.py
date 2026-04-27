import argparse
import time

from reversi import Board, MinimaxPlayer, AlphaBetaPlayer


def play_game(minimax_depth: int, alphabeta_depth: int):
    board = Board()
    black_player = MinimaxPlayer(depth=minimax_depth)
    white_player = AlphaBetaPlayer(depth=alphabeta_depth)

    current = 'B'
    passes = 0
    move_count = 0

    while True:
        if board.is_terminal() or passes >= 2:
            break

        moves = board.legal_moves(current)
        if not moves:
            passes += 1
            current = board.other(current)
            continue

        passes = 0
        player = black_player if current == 'B' else white_player
        move = player.choose_move(board, current)
        if move is None:
            current = board.other(current)
            continue

        board = board.apply_move(current, move)
        move_count += 1
        current = board.other(current)

    return board.get_winner(), board.count('B'), board.count('W'), move_count


def run_bench(games: int, minimax_depth: int, alphabeta_depth: int):
    results = {'B': 0, 'W': 0, 'D': 0}
    total_moves = 0

    started = time.perf_counter()
    for _ in range(games):
        winner, b_count, w_count, moves = play_game(minimax_depth, alphabeta_depth)
        if winner not in results:
            winner = 'D'
        results[winner] += 1
        total_moves += moves
    elapsed = time.perf_counter() - started

    print('=== Reversi AI Bench ===')
    print(f'Games: {games}')
    print(f'Minimax depth (Black): {minimax_depth}')
    print(f'AlphaBeta depth (White): {alphabeta_depth}')
    print(f'Total time: {elapsed:.3f}s')
    print(f'Average/game: {elapsed / games:.3f}s')
    print(f'Average moves/game: {total_moves / games:.2f}')
    print('--- Results ---')
    print(f'Black (Minimax) wins: {results["B"]}')
    print(f'White (AlphaBeta) wins: {results["W"]}')
    print(f'Draws: {results["D"]}')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Benchmark Minimax vs AlphaBeta in CLI.')
    parser.add_argument('--games', type=int, default=10, help='Number of games to simulate.')
    parser.add_argument('--minimax-depth', type=int, default=3, help='Black (Minimax) search depth.')
    parser.add_argument('--alphabeta-depth', type=int, default=3, help='White (AlphaBeta) search depth.')
    args = parser.parse_args()

    run_bench(args.games, args.minimax_depth, args.alphabeta_depth)
