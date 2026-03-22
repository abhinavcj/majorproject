// ===== VoiceAssist — Speech Engine =====

const $ = id => document.getElementById(id);

const textarea      = $('speech-input');
const btnSpeak       = $('btn-speak');
const btnStop        = $('btn-stop');
const btnClear       = $('btn-clear');
const btnMic         = $('btn-mic');
const micStatus      = $('mic-status');
const voiceSelect    = $('voice-select');
const historyList    = $('history-list');
const indicator      = $('speaking-indicator');
const indicatorText  = $('speaking-text');
const speedSlider    = $('speed-slider');
const speedValue     = $('speed-value');
const langFrom       = $('lang-from');
const langTo         = $('lang-to');
const btnTranslate   = $('btn-translate');
const btnSwap        = $('btn-swap');
const translateStatus = $('translate-status');
const translatedOutput = $('translated-output');
const translatedText = $('translated-text');
const voiceWarning   = $('voice-warning');
const fallbackInfo   = $('fallback-info');
const btnSpeakTrans  = $('btn-speak-translated');

// ===== State =====
let voices = [];
let history = [];

// ===== Voices =====
let preferredVoice = null;
function loadVoices() {
    voices = speechSynthesis.getVoices();
    preferredVoice = voices.find(v => v.name.includes('Rishi') || v.lang === 'en-IN') || voices.find(v => v.lang.startsWith('en'));
}
speechSynthesis.onvoiceschanged = loadVoices;
loadVoices();

// Speed logic removed (UI gone)
if (speedSlider) {
    speedSlider.addEventListener('input', () => {
        if (speedValue) speedValue.textContent = `${speedSlider.value}×`;
    });
}
function speak(text, targetLang, voiceOverride) {
    if (!text || !text.trim()) return;
    speechSynthesis.cancel();

    const utt = new SpeechSynthesisUtterance(text.trim());
    utt.rate = 1.0;
    utt.pitch = 1.0;

    if (voiceOverride) {
        utt.voice = voiceOverride;
    } else if (targetLang) {
        utt.lang = targetLang;
    } else if (preferredVoice) {
        utt.voice = preferredVoice;
    }

    utt.onstart = () => {
        indicator.classList.add('active');
        indicatorText.textContent = text.trim().length > 40 ? text.trim().slice(0, 40) + '…' : text.trim();
        btnSpeak.classList.add('speaking');
    };
    const done = () => { indicator.classList.remove('active'); btnSpeak.classList.remove('speaking'); };
    utt.onend = done;
    utt.onerror = done;

    speechSynthesis.speak(utt);
    addToHistory(text.trim());
}

// ===== History =====
function addToHistory(text) {
    if (history.length > 0 && history[0].text === text) return;
    const t = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    history.unshift({ text, time: t });
    if (history.length > 20) history.pop();
    renderHistory();
}

function renderHistory() {
    historyList.innerHTML = '';
    if (history.length === 0) {
        historyList.innerHTML = '<div class="empty-state">Nothing spoken yet</div>';
        return;
    }
    history.forEach(item => {
        const el = document.createElement('div');
        el.className = 'history-item';
        el.innerHTML = `<span class="replay">▶</span><span class="htxt">${esc(item.text)}</span><span class="htime">${item.time}</span>`;
        el.addEventListener('click', () => { textarea.value = item.text; speak(item.text); });
        historyList.appendChild(el);
    });
}

function esc(s) { const d = document.createElement('div'); d.textContent = s; return d.innerHTML; }

// ===== (Tone chips removed) =====

// ===== Quick Phrases =====
document.querySelectorAll('.phrase-btn').forEach(btn => {
    btn.addEventListener('click', () => {
        const p = btn.dataset.phrase;
        textarea.value = p;
        speak(p);
        btn.classList.add('flash');
        setTimeout(() => btn.classList.remove('flash'), 350);
    });
});

// ===== Controls =====
btnSpeak.addEventListener('click', () => speak(textarea.value));
btnStop.addEventListener('click', () => { speechSynthesis.cancel(); indicator.classList.remove('active'); btnSpeak.classList.remove('speaking'); });
btnClear.addEventListener('click', () => { textarea.value = ''; textarea.focus(); });

textarea.addEventListener('keydown', e => {
    if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') { e.preventDefault(); speak(textarea.value); }
    if ((e.ctrlKey || e.metaKey) && e.shiftKey && e.key === 'Enter') { e.preventDefault(); btnTranslate.click(); }
});

// ===========================================================================
// ===== Voice-to-Text (Speech Recognition) =====
// ===========================================================================

const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
let recognition = null;

if (SpeechRecognition) {
    recognition = new SpeechRecognition();
    recognition.continuous = false;
    recognition.interimResults = true;
    recognition.lang = 'en-US';

    let finalTranscript = '';

    recognition.onstart = () => {
        btnMic.classList.add('recording');
        micStatus.textContent = '🎤 Listening… speak now';
        micStatus.className = 'mic-status active';
    };

    recognition.onresult = (e) => {
        let interim = '';
        finalTranscript = '';
        for (let i = 0; i < e.results.length; i++) {
            if (e.results[i].isFinal) {
                finalTranscript += e.results[i][0].transcript;
            } else {
                interim += e.results[i][0].transcript;
            }
        }
        textarea.value = finalTranscript || interim;
    };

    recognition.onend = () => {
        btnMic.classList.remove('recording');
        if (finalTranscript) {
            micStatus.textContent = '✅ Got it!';
            micStatus.className = 'mic-status';
            textarea.value = finalTranscript;
        } else {
            micStatus.textContent = '';
            micStatus.className = 'mic-status';
        }
    };

    recognition.onerror = (e) => {
        btnMic.classList.remove('recording');
        if (e.error === 'not-allowed') {
            micStatus.textContent = '🚫 Microphone access denied. Allow in browser settings.';
        } else if (e.error === 'no-speech') {
            micStatus.textContent = 'No speech detected. Try again.';
        } else {
            micStatus.textContent = `Error: ${e.error}`;
        }
        micStatus.className = 'mic-status';
    };

    btnMic.addEventListener('click', () => {
        if (btnMic.classList.contains('recording')) {
            recognition.stop();
        } else {
            // Set recognition language to match the "from" language
            recognition.lang = langFrom.value === 'zh-CN' ? 'zh-CN' : langFrom.value;
            finalTranscript = '';
            recognition.start();
        }
    });
} else {
    btnMic.style.display = 'none';
    micStatus.textContent = 'Speech recognition not supported in this browser.';
}

// ===========================================================================
// ===== Translation (Google Translate API) =====
// ===========================================================================

async function translateText(text, from, to) {
    if (!text || !text.trim()) {
        translateStatus.textContent = 'Type something first.';
        translateStatus.className = 'status-msg error';
        return null;
    }
    if (from === to) {
        translateStatus.textContent = 'Source & target are the same.';
        translateStatus.className = 'status-msg error';
        return text;
    }

    translateStatus.textContent = 'Translating…';
    translateStatus.className = 'status-msg';
    btnTranslate.classList.add('loading');

    try {
        const url = `https://translate.googleapis.com/translate_a/single?client=gtx&sl=${from}&tl=${to}&dt=t&q=${encodeURIComponent(text.trim())}`;
        const res = await fetch(url);
        const data = await res.json();
        btnTranslate.classList.remove('loading');

        // data[0] is an array of translation segments
        if (data && data[0]) {
            const translated = data[0].map(seg => seg[0]).join('');
            translateStatus.textContent = '';
            return translated;
        }
        translateStatus.textContent = 'Translation failed.';
        translateStatus.className = 'status-msg error';
        return null;
    } catch (err) {
        btnTranslate.classList.remove('loading');
        translateStatus.textContent = 'Network error. Check connection.';
        translateStatus.className = 'status-msg error';
        console.error('Translation error:', err);
        return null;
    }
}

// Find a voice for a given language code
function findVoiceForLang(lang) {
    if (voices.length === 0) return null;
    const base = lang.split('-')[0].toLowerCase();
    return voices.find(v => v.lang.toLowerCase().startsWith(base)) || null;
}

let lastTranslation = '';
let lastTargetLang = '';

btnTranslate.addEventListener('click', async () => {
    const result = await translateText(textarea.value, langFrom.value, langTo.value);
    if (result !== null) {
        lastTranslation = result;
        lastTargetLang = langTo.value;
        translatedText.textContent = result;
        translatedOutput.style.display = 'block';

        // Check voice availability
        const v = findVoiceForLang(lastTargetLang);
        if (!v) {
            voiceWarning.style.display = 'flex';
            fallbackInfo.textContent = `No voice for "${lastTargetLang}" — will use system default.`;
        } else {
            voiceWarning.style.display = 'none';
        }
    }
});

btnSpeakTrans.addEventListener('click', () => {
    if (!lastTranslation) return;
    const v = voices.find(x => x.lang.startsWith(lastTargetLang) || x.lang.includes(lastTargetLang.split('-')[0]));
    speak(lastTranslation, lastTargetLang, v);
});

btnSwap.addEventListener('click', () => {
    const tmp = langFrom.value;
    for (const o of langFrom.options) if (o.value === langTo.value) { o.selected = true; break; }
    for (const o of langTo.options) if (o.value === tmp) { o.selected = true; break; }
    if (translatedOutput.style.display !== 'none' && lastTranslation) {
        textarea.value = lastTranslation;
        translatedOutput.style.display = 'none';
        lastTranslation = '';
    }
});

// ===== Init =====
if (historyList) renderHistory();
if (textarea) textarea.focus();

// ===========================================================================
// ===== MODE TABS (Listen / Compose) =====
// ===========================================================================

const listenPanel = $('listen-panel');
const composePanel = $('compose-panel');

document.querySelectorAll('.mode-tab').forEach(tab => {
    tab.addEventListener('click', () => {
        document.querySelectorAll('.mode-tab').forEach(t => t.classList.remove('active'));
        tab.classList.add('active');

        const mode = tab.dataset.mode;
        if (mode === 'listen') {
            listenPanel.style.display = '';
            composePanel.style.display = 'none';
        } else {
            listenPanel.style.display = 'none';
            composePanel.style.display = '';
        }
    });
});

// ===========================================================================
// ===== LISTEN MODE — 2-Way Communication (Hearing → Deaf) =====
// ===========================================================================

const btnListen = $('btn-listen');
const listenBtnText = $('listen-btn-text');
const listenStatus = $('listen-status');
const listenOutput = $('listen-output');
const listenTranscript = $('listen-transcript');
const btnClearTranscript = $('btn-clear-transcript');

let listenRecognition = null;
let isListening = false;
let transcriptLines = [];

if (SpeechRecognition) {
    listenRecognition = new SpeechRecognition();
    listenRecognition.continuous = false; // Changed to false for better mobile stability
    listenRecognition.interimResults = true;
    listenRecognition.lang = 'en-US';

    listenRecognition.onstart = () => {
        isListening = true;
        btnListen.classList.add('active');
        listenBtnText.textContent = 'Stop Listening';
        listenStatus.textContent = '🎤 Listening… the other person can speak now';
        listenStatus.className = 'listen-status active';
        listenOutput.textContent = '…';
        listenOutput.className = 'listen-output interim';
    };

    listenRecognition.onresult = (e) => {
        let final = '';
        let interim = '';

        for (let i = e.resultIndex; i < e.results.length; i++) {
            if (e.results[i].isFinal) {
                final += e.results[i][0].transcript;
            } else {
                interim += e.results[i][0].transcript;
            }
        }

        if (final) {
            listenOutput.textContent = final;
            listenOutput.className = 'listen-output';
            addTranscriptLine(final.trim());
        } else if (interim) {
            listenOutput.textContent = interim;
            listenOutput.className = 'listen-output interim';
        }
    };

    listenRecognition.onend = () => {
        // Auto-restart if still in listen mode (continuous listening)
        if (isListening) {
            try {
                listenRecognition.start();
            } catch (e) {
                stopListening();
            }
        }
    };

    listenRecognition.onerror = (e) => {
        if (e.error === 'not-allowed') {
            listenStatus.textContent = '🚫 Microphone access denied.';
            stopListening();
        } else if (e.error === 'no-speech') {
            // Don't stop — keep listening
            listenStatus.textContent = '⏳ Waiting for speech…';
        } else if (e.error === 'aborted') {
            // Do nothing, this is normal when we stop
        } else {
            listenStatus.textContent = `Error: ${e.error}`;
        }
    };

    btnListen.addEventListener('click', () => {
        if (isListening) {
            stopListening();
        } else {
            startListening();
        }
    });
} else {
    btnListen.style.opacity = '0.5';
    btnListen.style.pointerEvents = 'none';
    listenStatus.textContent = 'Speech recognition is not supported in this browser.';
}

function startListening() {
    isListening = true;
    listenRecognition.lang = langFrom.value === 'zh-CN' ? 'zh-CN' : langFrom.value;
    try {
        listenRecognition.start();
    } catch (e) {
        stopListening();
    }
}

function stopListening() {
    isListening = false;
    try { listenRecognition.stop(); } catch (e) {}
    btnListen.classList.remove('active');
    listenBtnText.textContent = 'Start Listening';
    listenStatus.textContent = '';
    listenStatus.className = 'listen-status';
}

function addTranscriptLine(text) {
    if (!text) return;
    const t = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
    transcriptLines.push({ text, time: t });
    renderTranscript();
}

function renderTranscript() {
    if (transcriptLines.length === 0) {
        listenTranscript.innerHTML = '<div class="empty-state">Transcript will appear here…</div>';
        return;
    }
    listenTranscript.innerHTML = transcriptLines.map(l =>
        `<div class="transcript-line"><span class="ttime">${l.time}</span>${esc(l.text)}</div>`
    ).join('');
    listenTranscript.scrollTop = listenTranscript.scrollHeight;
}

btnClearTranscript.addEventListener('click', () => {
    transcriptLines = [];
    renderTranscript();
    listenOutput.textContent = 'Tap the button above and ask them to speak…';
    listenOutput.className = 'listen-output placeholder';
});
