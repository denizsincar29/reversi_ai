# Reversi with Audio-First UI
This is a Reversi (Othello) game built with an audio-first user interface, designed for accessibility and screen reader users. The game features:
- A standard 8x8 Reversi board rendered in HTML.
- Audio announcements for game events and moves.
- Keyboard navigation for an accessible gameplay experience.

# Controls:
- Click on the board squares to place your black disk.
- Use the "Play with Minimax (Black)" button to let the AI play as black against the AlphaBeta white AI.
- Use the "New Game" button to reset the board.

# how to play:
The game starts with 4 disks in the center.
First player (Black) places a disk by clicking an empty square. Disks must be placed adjacent to an opponent's disk and must flip at least one opponent disk by surrounding it. The game continues until neither player can move, and the player with the most disks on the board wins.
For example, if you have the 3rd row starting with black, than 4 whites, than empty, you can place a black disk in that empty square to flip the 4 white disks to black, gaining a big advantage. The audio will announce your move and any flips, and the screen reader will read out the updated board state after each turn.

# Hotkeys and Accessibility:
- Use Alt+A to have the screen reader announce the current advantage (who is winning and by how much).
- Use Alt+L to have the screen reader announce the legal moves available for black.
