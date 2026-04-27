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
        sounds: ['disk.wav', 'white.wav', 'black.wav', 'error.wav', 'pass.wav', 'border.wav'],
        BASE_FREQ: 16000,
        STEP: 1000,
        DEFAULT_SAMPLE_RATE: 22050,
        initPromise: null,

        async init() {
            if (this.ctx && this.ctx.state === 'closed') {
                this.ctx = null;
                this.initPromise = null;
            }
            if (this.initPromise) return this.initPromise;

            const doInit = async () => {
                if (this.ctx) {
                    if (this.ctx.state === 'suspended') {
                        await this.ctx.resume().catch(() => {});
                    }
                    return;
                }
                this.ctx = new (window.AudioContext || window.webkitAudioContext)();

                if (this.ctx.state === 'suspended') {
                    this.ctx.resume().catch(() => {});
                }

                const loadPromises = this.sounds.map(async (sound) => {
                    try {
                        // Use a more robust path, ensuring correct slash separator
                        // In Gradio 6+, files are served under /gradio_api/file=... or /file=...
                        const base = window.location.pathname.endsWith('/') ? window.location.pathname : window.location.pathname + '/';

                        let url = window.location.origin + base + `gradio_api/file=sounds/${sound}`;
                        let response = await fetch(url);

                        if (!response.ok) {
                            // Fallback to /file=...
                            url = window.location.origin + base + `file=sounds/${sound}`;
                            response = await fetch(url);
                        }
                        if (!response.ok) throw new Error(`Status ${response.status}`);

                        const contentType = response.headers.get("content-type");
                        if (contentType && contentType.includes("text/html")) {
                            throw new Error("Received HTML instead of audio. Check if path is correct.");
                        }

                        const arrayBuffer = await response.arrayBuffer();
                        if (arrayBuffer.byteLength < 100) {
                            throw new Error("Received too small buffer, likely not a valid audio file.");
                        }
                        this.buffers[sound] = await this.ctx.decodeAudioData(arrayBuffer);
                    } catch (e) {
                        console.error(`Failed to load sound: ${sound}`, e);
                    }
                });
                await Promise.all(loadPromises);
            };

            this.initPromise = doInit();
            this.initPromise.then(() => {}, () => {}); // Handle rejection to avoid unhandled promise rejections
            return this.initPromise;
        },

        async play(soundName, r, c) {
            console.log(`AudioEngine.play: ${soundName} at (${r}, ${c})`);
            try {
                if (!this.ctx || this.ctx.state === 'closed') await this.init();
                if (!this.ctx || !this.buffers[soundName]) {
                    console.warn(`Sound ${soundName} not loaded or ctx missing.`);
                    return;
                }

                if (this.ctx.state === 'suspended') {
                    console.log("Context suspended, attempting resume...");
                    await Promise.race([
                        this.ctx.resume(),
                        new Promise(resolve => setTimeout(resolve, 50))
                    ]).catch(() => {});
                }

                if (this.ctx.state !== 'running') {
                    console.warn(`Cannot play ${soundName}, context state: ${this.ctx.state}`);
                }

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
            } catch (e) {
                console.error("Error playing sound", e);
            }
        },

        async playMoveSequence(player, r, c, flips) {
            await this.play('disk.wav', r, c);
            const sound = player === 'W' ? 'white.wav' : 'black.wav';

            for (let i = 0; i < flips.length; i++) {
                const [fr, fc] = flips[i];
                // Using a small delay between flips
                await new Promise(resolve => setTimeout(resolve, 120));
                await this.play(sound, fr, fc);
            }
        }
    };

    // --- Global State & UI ---
    let localGrid = Array(SIZE).fill(null).map(() => Array(SIZE).fill('.'));
    let humanColor = 'B';
    let isProcessing = false;
    let localErrorPlayed = false;
    let lastProcessedTs = 0;

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
        buttons.forEach((btn, idx) => {
            const text = (btn.textContent || '').trim();
            const lowerText = text.toLowerCase();
            let newPiece = 'empty';
            if (lowerText.includes('black')) {
                newPiece = 'black';
            } else if (lowerText.includes('white')) {
                newPiece = 'white';
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

            // Construct aria-label if it doesn't match the standard format or text is truncated
            const r = Math.floor(idx / SIZE);
            const c = idx % SIZE;
            const coord = String.fromCharCode(65 + c) + (r + 1);
            const expectedAria = `${coord} ${newPiece}`;

            if (btn.getAttribute('aria-label') !== expectedAria) {
                btn.setAttribute('aria-label', expectedAria);
            }
        });
        syncFromUI();
    }

    function getBoardButtons() {
        return Array.from(document.querySelectorAll('button.board-cell'));
    }

    function focusCell(index) {
        const buttons = getBoardButtons();
        if (buttons[index]) {
            buttons[index].focus();
        }
    }

    async function handleCellClick(btn, index) {
        if (isProcessing) {
            console.log("Click ignored: isProcessing is true");
            return;
        }

        console.log(`Cell clicked: index ${index}`);
        // Resume on every click to keep it alive
        if (AudioEngine.ctx && AudioEngine.ctx.state === 'suspended') {
            AudioEngine.ctx.resume().catch(() => {});
        }
        await AudioEngine.init();

        const r = Math.floor(index / SIZE);
        const c = index % SIZE;

        // Block UI immediately to wait for Gradio sync
        isProcessing = true;

        try {
            if (Reversi.isValidMove(localGrid, humanColor, r, c)) {
                console.log("Move is valid locally, applying optimistic update.");
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
                console.log("Move is invalid locally, playing error sound.");
                // Set flag BEFORE playing to prevent race with incoming metadata
                localErrorPlayed = true;
                await AudioEngine.play('error.wav', r, c);
            } else {
                isProcessing = false;
            }
        } catch (e) {
            console.error("Error in handleCellClick", e);
            isProcessing = false;
        }
    }

    async function handleMetadataUpdate(metadataStr) {
        if (!metadataStr) return;
        console.log("Metadata update received");
        let payload;
        try {
            payload = JSON.parse(metadataStr);
        } catch (e) {
            console.error("Failed to parse metadata", e);
            isProcessing = false;
            return;
        }

        if (payload.ts && payload.ts <= lastProcessedTs) {
            console.log("Metadata is old, skipping.");
            isProcessing = false;
            return;
        }
        lastProcessedTs = payload.ts || 0;

        const moves = payload.moves || [];
        console.log(`Processing ${moves.length} moves from metadata`);

        try {
            // Replay moves sequentially
            for (const move of moves) {
                if (move.type === 'move') {
                    // Skip if it's our move and we already played it optimistically
                    // But if it's AI or assistant move, we play it.
                    if (move.player !== humanColor || !isProcessing) {
                        await AudioEngine.playMoveSequence(move.player, move.r, move.c, move.flips);
                        await new Promise(resolve => setTimeout(resolve, 300));
                    }
                } else if (move.type === 'pass') {
                    await AudioEngine.play('pass.wav');
                    await new Promise(resolve => setTimeout(resolve, 600));
                } else if (move.type === 'error' && move.player === humanColor) {
                    // Error sound is already handled optimistically in handleCellClick.
                    // We only play it here if we somehow didn't catch it locally.
                    if (!localErrorPlayed) {
                        await AudioEngine.play('error.wav', move.coords[0], move.coords[1]);
                    }
                    localErrorPlayed = false;
                }
            }
        } catch (e) {
            console.error("Error in metadata update", e);
        } finally {
            isProcessing = false;
            localErrorPlayed = false;
            console.log("Metadata processing complete, isProcessing reset.");
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

            if (e.key === 'ArrowUp') {
                if (focusedIdx >= cols) nextIdx = focusedIdx - cols;
                else AudioEngine.play('border.wav');
            }
            else if (e.key === 'ArrowDown') {
                if (focusedIdx < cols * (cols - 1)) nextIdx = focusedIdx + cols;
                else AudioEngine.play('border.wav');
            }
            else if (e.key === 'ArrowLeft') {
                if (focusedIdx % cols > 0) nextIdx = focusedIdx - 1;
                else AudioEngine.play('border.wav');
            }
            else if (e.key === 'ArrowRight') {
                if (focusedIdx % cols < cols - 1) nextIdx = focusedIdx + 1;
                else AudioEngine.play('border.wav');
            }
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
                return;
            }

            const assistBtn = e.target.closest('#assist-btn');
            const newGameBtn = e.target.closest('#new-game-btn');
            if (assistBtn || newGameBtn) {
                if (isProcessing) {
                    e.preventDefault();
                    e.stopPropagation();
                    return;
                }
                isProcessing = true;
                if (AudioEngine.ctx && AudioEngine.ctx.state === 'suspended') {
                    await AudioEngine.ctx.resume().catch(console.warn);
                }
                await AudioEngine.init();
            }
        });

        const observer = new MutationObserver((mutations) => {
            let boardChanged = false;
            let metadataChanged = false;

            for (const mutation of mutations) {
                console.log(`Mutation observed: ${mutation.type}`, mutation.target);
                let target = mutation.target;
                if (mutation.type === 'characterData') {
                    target = target.parentElement;
                }

                if (!target) continue;

                if (mutation.type === 'childList' || mutation.type === 'characterData') {
                    // Check if mutation is within the board
                    if (target.closest && target.closest('#board-container')) {
                        boardChanged = true;
                    }
                    // Check if mutation is the metadata container
                    if (target.id === 'move-metadata-container' ||
                        (target.parentElement && target.parentElement.id === 'move-metadata-container')) {
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

        // Safety reset for isProcessing in case of unexpected hangs
        window.setInterval(() => {
            if (isProcessing) {
                console.warn("Safety reset: isProcessing was stuck.");
                isProcessing = false;
            }
        }, 5000);

        // Resume audio context on visibility change (tab back)
        document.addEventListener('visibilitychange', () => {
            if (document.visibilityState === 'visible' && AudioEngine.ctx && AudioEngine.ctx.state === 'suspended') {
                AudioEngine.ctx.resume().catch(() => {});
            }
        });

        // Global unlock on any interaction
        const unlock = () => {
            if (AudioEngine.ctx && AudioEngine.ctx.state === 'suspended') {
                AudioEngine.ctx.resume().catch(() => {});
            }
        };
        document.addEventListener('click', unlock);
        document.addEventListener('keydown', unlock);
        document.addEventListener('touchstart', unlock);
    }

    hookKeyboardNav();
    window.AudioEngine = AudioEngine;
    window.Reversi = Reversi;
})();
