/**
 * premium-ui.js — SignBridge Shared UI Enhancements
 * Handles: Theme toggle, AI Command Palette, toast notifications, micro-interactions
 */

// ── Theme Toggle ─────────────────────────────────────────────────────────────
(function initTheme() {
  const toggle = document.getElementById('themeToggle');
  if (!toggle) return;

  const saved = localStorage.getItem('signbridge-theme') || 'dark';
  document.documentElement.setAttribute('data-theme', saved);
  toggle.textContent = saved === 'dark' ? '🌙' : '☀️';

  toggle.addEventListener('click', () => {
    const current = document.documentElement.getAttribute('data-theme');
    const next = current === 'dark' ? 'light' : 'dark';
    document.documentElement.setAttribute('data-theme', next);
    localStorage.setItem('signbridge-theme', next);
    toggle.textContent = next === 'dark' ? '🌙' : '☀️';
    
    // Animate the toggle
    toggle.style.transform = 'scale(1.2) rotate(180deg)';
    setTimeout(() => { toggle.style.transform = ''; }, 300);
    
    showToast(next === 'dark' ? 'Dark mode activated' : 'Light mode activated');
  });
})();

// ── Toast Notifications ──────────────────────────────────────────────────────
function showToast(message, duration = 2500) {
  const toast = document.getElementById('toast');
  if (!toast) return;
  
  toast.textContent = message;
  toast.classList.add('visible');
  
  clearTimeout(toast._timeout);
  toast._timeout = setTimeout(() => {
    toast.classList.remove('visible');
  }, duration);
}

// Make globally accessible
window.showToast = showToast;

// ── AI Command Palette (Bonus Futuristic Feature) ────────────────────────────
(function initCommandPalette() {
  const overlay = document.getElementById('commandOverlay');
  const input = document.getElementById('commandInput');
  const results = document.getElementById('commandResults');
  if (!overlay || !input) return;

  const commands = [
    { action: 'speak', icon: '🔊', label: 'Speak current sentence', shortcut: '⌘S' },
    { action: 'clear', icon: '🗑️', label: 'Clear all text', shortcut: '⌘⌫' },
    { action: 'toggle', icon: '⏯️', label: 'Start / Stop detection', shortcut: 'Space' },
    { action: 'theme', icon: '🌓', label: 'Toggle dark / light mode', shortcut: '⌘D' },
    { action: 'navigate-speech', icon: '🎙️', label: 'Go to Speech Assist', shortcut: '' },
    { action: 'navigate-sign', icon: '📝', label: 'Go to Text to Sign', shortcut: '' },
    { action: 'navigate-detect', icon: '🤟', label: 'Go to Sign Detection', shortcut: '' },
  ];

  let focusedIndex = -1;

  function open() {
    overlay.classList.add('open');
    input.value = '';
    input.focus();
    focusedIndex = -1;
    renderCommands('');
  }

  function close() {
    overlay.classList.remove('open');
    input.blur();
  }

  function renderCommands(filter) {
    if (!results) return;
    const filtered = commands.filter(c => 
      c.label.toLowerCase().includes(filter.toLowerCase())
    );

    results.innerHTML = filtered.map((c, i) => `
      <div class="command-item${i === focusedIndex ? ' focused' : ''}" data-action="${c.action}" data-index="${i}">
        <div class="cmd-icon">${c.icon}</div>
        <span class="cmd-label">${c.label}</span>
        ${c.shortcut ? `<span class="cmd-shortcut">${c.shortcut}</span>` : ''}
      </div>
    `).join('');

    // Click handlers
    results.querySelectorAll('.command-item').forEach(item => {
      item.addEventListener('click', () => {
        executeCommand(item.dataset.action);
        close();
      });
    });
  }

  function executeCommand(action) {
    switch (action) {
      case 'speak':
        const btnSpeak = document.getElementById('btn-speak');
        if (btnSpeak) btnSpeak.click();
        showToast('🔊 Speaking…');
        break;
      case 'clear':
        const btnClear = document.getElementById('btn-clear');
        if (btnClear) btnClear.click();
        showToast('🗑️ Cleared');
        break;
      case 'toggle':
        const btnToggle = document.getElementById('btn-toggle');
        if (btnToggle) btnToggle.click();
        break;
      case 'theme':
        const themeToggle = document.getElementById('themeToggle');
        if (themeToggle) themeToggle.click();
        break;
      case 'navigate-speech':
        window.location.href = 'speech.html';
        break;
      case 'navigate-sign':
        window.location.href = 'text_to_sign.html';
        break;
      case 'navigate-detect':
        window.location.href = 'index.html';
        break;
    }
  }

  // Keyboard shortcut: Cmd+K or Ctrl+K to open
  document.addEventListener('keydown', (e) => {
    if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
      e.preventDefault();
      if (overlay.classList.contains('open')) {
        close();
      } else {
        open();
      }
    }
    if (e.key === 'Escape' && overlay.classList.contains('open')) {
      close();
    }
  });

  // Filter on input
  input.addEventListener('input', () => {
    focusedIndex = -1;
    renderCommands(input.value);
  });

  // Keyboard navigation
  input.addEventListener('keydown', (e) => {
    const items = results.querySelectorAll('.command-item');
    
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      focusedIndex = Math.min(focusedIndex + 1, items.length - 1);
      updateFocus(items);
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      focusedIndex = Math.max(focusedIndex - 1, 0);
      updateFocus(items);
    } else if (e.key === 'Enter' && focusedIndex >= 0) {
      e.preventDefault();
      const focused = items[focusedIndex];
      if (focused) {
        executeCommand(focused.dataset.action);
        close();
      }
    }
  });

  function updateFocus(items) {
    items.forEach((item, i) => {
      item.classList.toggle('focused', i === focusedIndex);
    });
  }

  // Close on overlay click
  overlay.addEventListener('click', (e) => {
    if (e.target === overlay) close();
  });

  // Initial render
  renderCommands('');
})();

// ── Button Micro-interactions ────────────────────────────────────────────────
document.querySelectorAll('.btn, .phrase-btn, .suggestion-btn, .example-chip, .ctrl-btn, .word-chip, .icon-btn, .nav-link').forEach(el => {
  // Haptic-like press feedback
  el.addEventListener('mousedown', () => {
    el.style.transition = 'transform 0.1s cubic-bezier(0.4, 0, 0.2, 1)';
    el.style.transform = 'scale(0.96)';
  });
  
  el.addEventListener('mouseup', () => {
    el.style.transform = '';
    setTimeout(() => { el.style.transition = ''; }, 150);
  });
  
  el.addEventListener('mouseleave', () => {
    el.style.transform = '';
    setTimeout(() => { el.style.transition = ''; }, 150);
  });
});

// ── Page Load Animation ──────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  // Stagger animate sidebar cards
  document.querySelectorAll('.sidebar .card, .col-side .card').forEach((card, i) => {
    card.style.opacity = '0';
    card.style.transform = 'translateY(16px)';
    card.style.transition = `opacity 0.4s cubic-bezier(0.16, 1, 0.3, 1) ${i * 0.1}s, transform 0.4s cubic-bezier(0.16, 1, 0.3, 1) ${i * 0.1}s`;
    requestAnimationFrame(() => {
      card.style.opacity = '1';
      card.style.transform = 'translateY(0)';
    });
  });
});
