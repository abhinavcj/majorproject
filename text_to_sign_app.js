/**
 * text_to_sign_app.js  –  SignBridge Frontend Logic
 * Handles: text input, API calls, sequential sign playback, fingerspelling
 */

const API_BASE = 'http://127.0.0.1:8000';  // Points to the unified backend 8000

// ── DOM refs ─────────────────────────────────────────────────────────────────
const textInput       = document.getElementById('textInput');
const charCount       = document.getElementById('charCount');
const translateBtn    = document.getElementById('translateBtn');
const clearBtn        = document.getElementById('clearBtn');
const voiceBtn        = document.getElementById('voiceBtn');
const resultsSection  = document.getElementById('resultsSection');
const emptyState      = document.getElementById('emptyState');
const errorState      = document.getElementById('errorState');
const errorMsg        = document.getElementById('errorMsg');
const wordChips       = document.getElementById('wordChips');
const signVideo       = document.getElementById('signVideo');
const videoContainer  = document.getElementById('videoContainer');
const videoOverlay    = document.getElementById('videoOverlay');
const bigPlayBtn      = document.getElementById('bigPlayBtn');
const fingerspellContainer = document.getElementById('fingerspellContainer');
const fingerspellLetters   = document.getElementById('fingerspellLetters');
const nowPlayingWord  = document.getElementById('nowPlayingWord');
const progressText    = document.getElementById('progressText');
const progressFill    = document.getElementById('progressFill');
const sourceBadge     = document.getElementById('sourceBadge');
const playAllBtn      = document.getElementById('playAllBtn');
const playIcon        = document.getElementById('playIcon');
const pauseIcon       = document.getElementById('pauseIcon');
const prevBtn         = document.getElementById('prevBtn');
const nextBtn         = document.getElementById('nextBtn');
const speedSelect     = document.getElementById('speedSelect');
const statText        = document.getElementById('statText');
const exampleChips    = document.querySelectorAll('.example-chip');

// ── State ────────────────────────────────────────────────────────────────────
let signs = [];           // array of SignResult objects from API
let currentIndex = 0;
let isPlaying = false;
let autoAdvance = false;

// ── Init ─────────────────────────────────────────────────────────────────────
(async function init() {
  try {
    const res = await fetch(`${API_BASE}/stats`);
    const data = await res.json();
    statText.textContent =
      `${data.local_glosses.toLocaleString()} local / ${data.total_glosses.toLocaleString()} glosses`;
  } catch {
    statText.textContent = 'Backend connection issue...';
  }
})();

// ── Text input ────────────────────────────────────────────────────────────────
if (textInput) {
    textInput.addEventListener('input', () => {
    charCount.textContent = `${textInput.value.length} / 500`;
    });

    textInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && e.ctrlKey) doTranslate();
    });
}

if (clearBtn) {
    clearBtn.addEventListener('click', () => {
    textInput.value = '';
    charCount.textContent = '0 / 500';
    textInput.focus();
    hideAll();
    });
}

if (exampleChips) {
    exampleChips.forEach(chip => {
    chip.addEventListener('click', () => {
        textInput.value = chip.dataset.text;
        charCount.textContent = `${textInput.value.length} / 500`;
        doTranslate();
    });
    });
}

// ── Voice input ────────────────────────────────────────────────────────────────
let recognition = null;
if ('SpeechRecognition' in window || 'webkitSpeechRecognition' in window) {
  const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
  recognition = new SR();
  recognition.lang = 'en-US';
  recognition.interimResults = false;
  recognition.continuous = false;

  recognition.onresult = (e) => {
    const transcript = e.results[0][0].transcript;
    textInput.value = transcript;
    charCount.textContent = `${transcript.length} / 500`;
    voiceBtn.classList.remove('recording');
  };
  recognition.onend = () => voiceBtn.classList.remove('recording');
  recognition.onerror = () => voiceBtn.classList.remove('recording');
}

if (voiceBtn) {
    voiceBtn.addEventListener('click', () => {
    if (!recognition) { alert('Voice input not supported in this browser.'); return; }
    if (voiceBtn.classList.contains('recording')) {
        recognition.stop();
    } else {
        voiceBtn.classList.add('recording');
        recognition.start();
    }
    });
}

// ── Translate ─────────────────────────────────────────────────────────────────
if (translateBtn) {
    translateBtn.addEventListener('click', doTranslate);
}

async function doTranslate() {
  const text = textInput.value.trim();
  if (!text) return;

  translateBtn.disabled = true;
  translateBtn.classList.add('loading');
  hideAll();

  try {
    const res = await fetch(`${API_BASE}/translate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text }),
    });
    if (!res.ok) throw new Error(`Server error: ${res.status}`);
    signs = await res.json();

    if (!signs.length) {
      emptyState.style.display = '';
    } else {
      currentIndex = 0;
      isPlaying = false;
      autoAdvance = false;
      renderChips();
      
      // Start playback after translation
      resultsSection.style.display = '';
      resultsSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
      
      // Warm up
      signVideo.load();
      
      setTimeout(() => {
        startPlayback();
      }, 100);
    }
  } catch (err) {
    errorMsg.textContent = `Error: ${err.message}. Make sure the backend is running.`;
    errorState.style.display = '';
  } finally {
    translateBtn.disabled = false;
    translateBtn.classList.remove('loading');
  }
}

// ── Chip rendering ────────────────────────────────────────────────────────────
function renderChips() {
  wordChips.innerHTML = '';
  signs.forEach((sign, i) => {
    if (sign.word === '_SPACE_') {
      const spacer = document.createElement('div');
      spacer.className = 'chip-spacer';
      spacer.setAttribute('data-index', i);
      wordChips.appendChild(spacer);
      return;
    }

    const chip = document.createElement('button');
    chip.className = `word-chip ${sign.found ? '' : 'fingerspell-chip'}`;
    chip.title = sign.found ? `ASL: ${sign.gloss}` : `Fingerspell: ${sign.word}`;

    const badge = document.createElement('span');
    badge.className = `chip-badge ${sign.found ? 'badge-sign' : 'badge-spell'}`;
    badge.textContent = sign.found ? '▶' : 'FS';

    chip.appendChild(badge);
    chip.appendChild(document.createTextNode(sign.word));
    chip.setAttribute('data-index', i);
    chip.addEventListener('click', () => {
      stopPlayback();
      showSign(i);
    });
    wordChips.appendChild(chip);
  });
  updateProgress();
}

function setActiveChip(index) {
  document.querySelectorAll('.word-chip').forEach(c => {
    c.classList.toggle('active', parseInt(c.dataset.index) === index);
  });
}

function updateProgress() {
  const total = signs.filter(s => s.word !== '_SPACE_').length;
  const currentReal = signs.slice(0, currentIndex + 1).filter(s => s.word !== '_SPACE_').length;
  progressText.textContent = total ? `${currentReal} / ${total}` : '0 / 0';
  progressFill.style.width = total ? `${(currentReal / total) * 100}%` : '0%';
}

// ── Display a sign ────────────────────────────────────────────────────────────
function showSign(index) {
  if (index < 0 || index >= signs.length) return;
  
  if (signs[index].word === '_SPACE_') {
    currentIndex = index;
    if (window.signTimeout) clearTimeout(window.signTimeout);
    window.signTimeout = setTimeout(() => {
      if (currentIndex === index) advanceNext();
    }, autoAdvance ? (300 / parseFloat(speedSelect.value)) : 0);
    return;
  }
  
  currentIndex = index;
  const sign = signs[index];

  setActiveChip(index);
  updateProgress();
  nowPlayingWord.textContent = sign.word;

  if (window.signTimeout) clearTimeout(window.signTimeout);

  const chip = document.querySelector(`.word-chip[data-index="${index}"]`);
  if (chip) chip.scrollIntoView({ behavior: 'smooth', block: 'nearest', inline: 'center' });

  let signImg = document.getElementById('signImg');
  if (!signImg) {
    signImg = document.createElement('img');
    signImg.id = 'signImg';
    signImg.className = 'sign-media';
    signImg.style.display = 'none';
    videoContainer.appendChild(signImg);
    signVideo.className = 'sign-media';
  }

  const isGif = sign.local_url?.endsWith('.gif') || sign.remote_url?.endsWith('.gif');

  if (sign.found) {
    fingerspellContainer.style.display = 'none';
    videoContainer.style.display = '';

    const videoUrl = sign.local_url ? (sign.local_url.startsWith('http') ? sign.local_url : API_BASE + sign.local_url) : null;

    if (videoUrl) {
      if (isGif) {
        signVideo.style.display = 'none';
        signImg.style.display = 'block';
        signImg.src = videoUrl;
        videoOverlay.classList.add('hidden');
        
        if (autoAdvance) {
          window.signTimeout = setTimeout(() => { 
            if (autoAdvance && currentIndex === index) advanceNext(); 
          }, 1000 / parseFloat(speedSelect.value));
        }
      } else {
        signImg.style.display = 'none';
        signVideo.style.display = 'block';
        signVideo.src = videoUrl;
        signVideo.loop = false;
        signVideo.load();
        signVideo.defaultPlaybackRate = parseFloat(speedSelect.value);
        signVideo.playbackRate = parseFloat(speedSelect.value);
        signVideo.play().then(() => {
          videoOverlay.classList.add('hidden');
        }).catch(() => {
          videoOverlay.classList.remove('hidden');
        });
      }
      sourceBadge.textContent = sign.source ? `Source: ${sign.source}` : '';
    } else {
      signVideo.src = '';
      videoOverlay.classList.remove('hidden');
      sourceBadge.textContent = 'Video not available locally — download first';
    }
  } else {
    videoContainer.style.display = 'none';
    fingerspellContainer.style.display = '';
    signVideo.pause();
    signVideo.src = '';
    videoOverlay.classList.add('hidden');

    fingerspellLetters.innerHTML = '';
    (sign.fingerspell || []).forEach((letter, i) => {
      const el = document.createElement('div');
      el.className = 'fingerspell-letter';
      el.style.animationDelay = `${(i * 80) / parseFloat(speedSelect.value)}ms`;
      el.textContent = letter;
      fingerspellLetters.appendChild(el);
    });
    sourceBadge.textContent = '';

    if (autoAdvance) {
      const delay = Math.max(1500, (sign.fingerspell?.length || 1) * 600);
      setTimeout(() => { if (autoAdvance && currentIndex === index) advanceNext(); }, delay / parseFloat(speedSelect.value));
    }
  }
}

// ── Video events ──────────────────────────────────────────────────────────────
if (signVideo) {
    signVideo.addEventListener('click', () => {
    if (signVideo.paused) { signVideo.play(); videoOverlay.classList.add('hidden'); }
    else { signVideo.pause(); videoOverlay.classList.remove('hidden'); }
    });

    signVideo.addEventListener('ended', () => {
    if (autoAdvance) advanceNext();
    });

    signVideo.addEventListener('timeupdate', () => {
    if (autoAdvance && signVideo.duration > 0 && signVideo.currentTime >= signVideo.duration - 0.1) {
        if (!signVideo.paused) {
        setTimeout(() => {
            if (autoAdvance && signVideo.currentTime >= signVideo.duration - 0.1) {
            advanceNext();
            }
        }, 100);
        }
    }
    });

    signVideo.addEventListener('error', () => {
    videoOverlay.classList.remove('hidden');
    sourceBadge.textContent = '⚠ Video unavailable — no local or remote source found';
    if (autoAdvance) {
        setTimeout(() => { if (autoAdvance) advanceNext(); }, 800 / parseFloat(speedSelect.value));
    }
    });
}

if (bigPlayBtn) {
    bigPlayBtn.addEventListener('click', () => {
    if (signs.length > 1) {
        autoAdvance = true;
        isPlaying = true;
        updatePlayBtn();
    }
    signVideo.play();
    videoOverlay.classList.add('hidden');
    });
}

// Speed
if (speedSelect) {
    speedSelect.addEventListener('change', () => {
    signVideo.defaultPlaybackRate = parseFloat(speedSelect.value);
    signVideo.playbackRate = parseFloat(speedSelect.value);
    });
}

// ── Playback controls ─────────────────────────────────────────────────────────
if (prevBtn) {
    prevBtn.addEventListener('click', () => {
    stopPlayback();
    if (currentIndex > 0) showSign(currentIndex - 1);
    });
}

if (nextBtn) {
    nextBtn.addEventListener('click', () => {
    stopPlayback();
    advanceNext();
    });
}

function advanceNext() {
  if (currentIndex < signs.length - 1) {
    showSign(currentIndex + 1);
  } else {
    autoAdvance = false;
    isPlaying = false;
    updatePlayBtn();
    showSign(0);
  }
}

if (playAllBtn) {
    playAllBtn.addEventListener('click', () => {
    if (isPlaying) {
        stopPlayback();
    } else {
        startPlayback();
    }
    });
}

function startPlayback() {
  isPlaying = true;
  autoAdvance = true;
  updatePlayBtn();
  showSign(currentIndex);
}

function stopPlayback() {
  isPlaying = false;
  autoAdvance = false;
  updatePlayBtn();
  if (signVideo) signVideo.pause();
  if (window.signTimeout) clearTimeout(window.signTimeout);
}

function updatePlayBtn() {
  if (playIcon) playIcon.style.display = isPlaying ? 'none' : '';
  if (pauseIcon) pauseIcon.style.display = isPlaying ? '' : 'none';
}

// ── Utilities ─────────────────────────────────────────────────────────────────
function hideAll() {
  if (resultsSection) resultsSection.style.display = 'none';
  if (emptyState) emptyState.style.display = 'none';
  if (errorState) errorState.style.display = 'none';
}
