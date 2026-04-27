(() => {
    // --- Reversi Logic ---
    const SIZE = 8;
    const DIRECTIONS = [
        [-1, -1], [-1, 0], [-1, 1],
        [0, -1],           [0, 1],
        [1, -1],  [1, 0],  [1, 1]
    ];

    const Reversi = {
        getFlips(grid, player, r, c) {
            const flips = [];
            const opponent = player === 'B' ? 'W' : 'B';

            for (const [dr, dc] of DIRECTIONS) {
                let nr = r + dr;
                let nc = c + dc;
                const temp = [];

                while (nr >= 0 && nr < SIZE && nc >= 0 && nc < SIZE) {
                    const piece = grid[nr][nc];
                    if (piece === opponent) {
                        temp.push([nr, nc]);
                    } else if (piece === player) {
                        flips.push(...temp);
                        break;
                    } else {
                        break;
                    }
                    nr += dr;
                    nc += dc;
                }
            }
            return flips;
        },

        isValidMove(grid, player, r, c) {
            if (grid[r][c] !== '.') return false;
            return this.getFlips(grid, player, r, c).length > 0;
        },

        getLegalMoves(grid, player) {
            const moves = [];
            for (let r = 0; r < SIZE; r++) {
                for (let c = 0; c < SIZE; c++) {
                    if (this.isValidMove(grid, player, r, c)) {
                        moves.push([r, c]);
                    }
                }
            }
            return moves;
        },

        applyMove(grid, player, r, c) {
            const flips = this.getFlips(grid, player, r, c);
            const newGrid = grid.map(row => [...row]);
            newGrid[r][c] = player;
            flips.forEach(([fr, fc]) => {
                newGrid[fr][fc] = player;
            });
            return { grid: newGrid, flips };
        }
    };

    // --- Audio Engine ---
    const AudioEngine = {
        ctx: null,
        buffers: {},
        sounds: ['disk.wav', 'white.wav', 'black.wav', 'error.wav', 'pass.wav'],
        BASE_FREQ: 16000,
        STEP: 1000,
        DEFAULT_SAMPLE_RATE: 22050,

        async init() {
            if (this.ctx) return;
            this.ctx = new (window.AudioContext || window.webkitAudioContext)();
            const loadPromises = this.sounds.map(async (sound) => {
                try {
                    const response = await fetch(`/file=sounds/${sound}`);
                    if (!response.ok) throw new Error(`Status ${response.status}`);
                    const arrayBuffer = await response.arrayBuffer();
                    this.buffers[sound] = await this.ctx.decodeAudioData(arrayBuffer);
                } catch (e) {
                    console.error(`Failed to load sound: ${sound}`, e);
                }
            });
            await Promise.all(loadPromises);
        },

        play(soundName, r, c) {
            if (!this.ctx || !this.buffers[soundName]) return;

            const source = this.ctx.createBufferSource();
            source.buffer = this.buffers[soundName];

            if (r !== undefined) {
                const targetFreq = this.BASE_FREQ + r * this.STEP;
                source.playbackRate.value = targetFreq / this.DEFAULT_SAMPLE_RATE;
            }

            const panner = this.ctx.createStereoPanner();
            if (c !== undefined) {
                panner.pan.value = (2 * c / 7) - 1.0;
            } else {
                panner.pan.value = 0;
            }

            source.connect(panner).connect(this.ctx.destination);
            source.start();
        },

        async playMoveSequence(player, r, c, flips) {
            this.play('disk.wav', r, c);
            const sound = player === 'W' ? 'white.wav' : 'black.wav';
            const totalWait = (flips.length + 1) * 120;

            for (let i = 0; i < flips.length; i++) {
                const [fr, fc] = flips[i];
                setTimeout(() => {
                    this.play(sound, fr, fc);
                }, (i + 1) * 120);
            }

            return new Promise(resolve => setTimeout(resolve, totalWait + 100));
        }
    };

    // --- Global State & UI ---
    let localGrid = Array(SIZE).fill(null).map(() => Array(SIZE).fill('.'));
    let humanColor = 'B';
    let isProcessing = false;
    let localErrorPlayed = false;

    function syncFromUI() {
        const buttons = getBoardButtons();
        if (buttons.length !== 64) return;

        buttons.forEach((btn, idx) => {
            const r = Math.floor(idx / SIZE);
            const c = idx % SIZE;
            const piece = btn.getAttribute('data-piece') || 'empty';
            localGrid[r][c] = piece === 'black' ? 'B' : (piece === 'white' ? 'W' : '.');
        });

        // Gradio Radio labels for Color: "Black", "White"
        // But values are "B", "W". The radio buttons should have value attributes.
        const colorInput = document.querySelector('input[name="radio-option-your-color"]:checked');
        if (colorInput) {
            // Gradio Radio values are B and W
            humanColor = colorInput.value;
        }
    }

    function updatePieceDataAttributes() {
        const buttons = getBoardButtons();
        buttons.forEach(btn => {
            const text = (btn.textContent || '').trim().toLowerCase();
            let newPiece = '';
            if (text.includes('black')) {
                newPiece = 'black';
            } else if (text.includes('white')) {
                newPiece = 'white';
            } else {
                newPiece = 'empty';
            }

            const oldPiece = btn.getAttribute('data-piece');
            if (oldPiece !== newPiece) {
                if ((oldPiece === 'white' && newPiece === 'black') ||
                    (oldPiece === 'black' && newPiece === 'white')) {
                    btn.classList.remove('flipping');
                    void btn.offsetWidth;
                    btn.classList.add('flipping');
                }
                btn.setAttribute('data-piece', newPiece);
            }
            // Avoid setting aria-label if not changed to prevent observer cycles
            const newAria = text;
            if (btn.getAttribute('aria-label') !== newAria) {
                btn.setAttribute('aria-label', newAria);
            }
        });
        syncFromUI();
    }

    function getBoardButtons() {
        return Array.from(document.querySelectorAll('button')).filter((b) =>
            b.classList.contains('board-cell') || /^[A-H][1-8] (black|white|empty)$/i.test((b.textContent || '').trim())
        );
    }

    function focusCell(index) {
        const buttons = getBoardButtons();
        if (buttons[index]) {
            buttons[index].focus();
        }
    }

    async function handleCellClick(btn, index) {
        if (isProcessing) return;
        await AudioEngine.init();

        const r = Math.floor(index / SIZE);
        const c = index % SIZE;

        if (Reversi.isValidMove(localGrid, humanColor, r, c)) {
            isProcessing = true;
            localErrorPlayed = false;
            const result = Reversi.applyMove(localGrid, humanColor, r, c);
            localGrid = result.grid;

            // Play sound locally (optimistic)
            await AudioEngine.playMoveSequence(humanColor, r, c, result.flips);

            const buttons = getBoardButtons();
            buttons[index].setAttribute('data-piece', humanColor === 'B' ? 'black' : 'white');
            result.flips.forEach(([fr, fc]) => {
                const flipBtn = buttons[fr * SIZE + fc];
                flipBtn.classList.remove('flipping');
                void flipBtn.offsetWidth;
                flipBtn.classList.add('flipping');
                flipBtn.setAttribute('data-piece', humanColor === 'B' ? 'black' : 'white');
            });
        } else if (localGrid[r][c] === '.') {
            AudioEngine.play('error.wav', r, c);
            localErrorPlayed = true;
        }
    }

    async function handleMetadataUpdate(metadataStr) {
        if (!metadataStr) return;
        let metadata;
        try {
            metadata = JSON.parse(metadataStr);
        } catch (e) {
            return;
        }

        // Replay AI moves sequentially
        for (const move of metadata) {
            if (move.player === humanColor && move.type === 'move') {
                continue;
            }

            if (move.type === 'move') {
                await AudioEngine.playMoveSequence(move.player, move.r, move.c, move.flips);
                await new Promise(resolve => setTimeout(resolve, 300)); // Gap between moves
            } else if (move.type === 'pass') {
                AudioEngine.play('pass.wav');
                await new Promise(resolve => setTimeout(resolve, 600));
            } else if (move.type === 'error' && move.player === humanColor) {
                if (!localErrorPlayed) {
                    AudioEngine.play('error.wav', move.coords[0], move.coords[1]);
                }
                localErrorPlayed = false;
            }
        }

        isProcessing = false;
        localErrorPlayed = false;
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

        document.addEventListener('keydown', async function(e) {
            await AudioEngine.init();

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
            else if (e.key === 'Enter' || e.key === ' ') {
                handleCellClick(focused, focusedIdx);
                return;
            }
            else return;

            e.preventDefault();
            focusCell(nextIdx);
        });

        document.addEventListener('click', async function(e) {
            const btn = e.target.closest('button.board-cell');
            if (btn) {
                const buttons = getBoardButtons();
                const idx = buttons.indexOf(btn);
                await handleCellClick(btn, idx);
                btn.focus();
            }
        });

        const observer = new MutationObserver((mutations) => {
            let boardChanged = false;
            let metadataChanged = false;

            for (const mutation of mutations) {
                if (mutation.type === 'childList' || mutation.type === 'characterData') {
                    // Check if mutation is within the board
                    if (mutation.target.closest && mutation.target.closest('#board-container')) {
                        boardChanged = true;
                    }
                    // Check if mutation is the metadata container
                    if (mutation.target.id === 'move-metadata-container' ||
                        (mutation.target.parentElement && mutation.target.parentElement.id === 'move-metadata-container')) {
                        metadataChanged = true;
                    }
                }
            }

            if (boardChanged) updatePieceDataAttributes();
            if (metadataChanged) {
                const metaElem = document.getElementById('move-metadata');
                if (metaElem) {
                    const currentMeta = metaElem.getAttribute('data-payload');
                    if (currentMeta && currentMeta !== window.__lastMeta) {
                        window.__lastMeta = currentMeta;
                        handleMetadataUpdate(currentMeta);
                    }
                }
            }
        });

        observer.observe(document.body, {
            childList: true,
            subtree: true,
            characterData: true
            // attributes: false to avoid loops
        });

        window.setTimeout(updatePieceDataAttributes, 500);
    }

    hookKeyboardNav();
    window.AudioEngine = AudioEngine;
    window.Reversi = Reversi;
})();
