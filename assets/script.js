(() => {
    /**
     * Updates the data-piece attribute of buttons based on their text content
     * to trigger CSS animations.
     */
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
                // If it was white and now black, or vice versa, it's a flip
                if ((oldPiece === 'white' && newPiece === 'black') ||
                    (oldPiece === 'black' && newPiece === 'white')) {
                    btn.classList.remove('flipping');
                    void btn.offsetWidth; // trigger reflow
                    btn.classList.add('flipping');
                }
                btn.setAttribute('data-piece', newPiece);
            }
            btn.setAttribute('aria-label', text);
        });
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
            else if (e.key === 'ArrowRight' && focusedIdx % cols < cols - 1) nextIdx = focusedIdx + cols === buttons.length ? focusedIdx : focusedIdx + 1;
            else return;

            e.preventDefault();
            focusCell(nextIdx);
        });

        document.addEventListener('click', function(e) {
            if (e.target && e.target.matches('button.board-cell')) {
                e.target.focus();
            }
        });

        const observer = new MutationObserver((mutations) => {
            updatePieceDataAttributes();
        });

        observer.observe(document.body, {
            childList: true,
            subtree: true,
            characterData: true
        });

        window.setTimeout(updatePieceDataAttributes, 500);
    }

    hookKeyboardNav();
})();
