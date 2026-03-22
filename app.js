const video = document.getElementById('webcam-video');
const canvas = document.getElementById('output-canvas');
const ctx = canvas.getContext('2d');
const currentCharDisplay = document.getElementById('current-char');
const sentenceDisplay = document.getElementById('sentence-output');
const suggestionsContainer = document.getElementById('suggestions');
const statusDot = document.getElementById('status-dot');
const statusText = document.getElementById('status-text');
const btnSpeak = document.getElementById('btn-speak');
const btnClear = document.getElementById('btn-clear');
const btnToggle = document.getElementById('btn-toggle');

let socket = null;
let isRunning = false;
let captureInterval = null;
let animationFrameId = null;

// Landmark overlay image (updated asynchronously from backend responses)
let landmarkOverlay = null;

// Initialize Webcam
async function setupWebcam() {
    try {
        const stream = await navigator.mediaDevices.getUserMedia({
            video: { width: 640, height: 480, frameRate: 30 }
        });
        video.srcObject = stream;
        return new Promise((resolve) => {
            video.onloadedmetadata = () => {
                canvas.width = video.videoWidth;
                canvas.height = video.videoHeight;
                resolve();
            };
        });
    } catch (err) {
        console.error("Error accessing webcam:", err);
        statusText.innerText = "Webcam access denied";
        return false;
    }
}

// --- LIVE RENDER LOOP (runs at full FPS, independent of backend) ---
function renderLoop() {
    if (!isRunning) return;

    // Mirror the video horizontally so it looks natural (same as final_pred.py flip)
    ctx.save();
    ctx.scale(-1, 1);
    ctx.drawImage(video, -canvas.width, 0, canvas.width, canvas.height);
    ctx.restore();

    // Overlay the hand-skeleton image from the backend (small, top-right corner)
    if (landmarkOverlay) {
        const overlaySize = 180;
        ctx.drawImage(
            landmarkOverlay,
            canvas.width - overlaySize - 10,
            10,
            overlaySize,
            overlaySize
        );
    }

    animationFrameId = requestAnimationFrame(renderLoop);
}

// Connect to WebSocket Backend
function connectBackend() {
    const wsHost = (window.location.hostname && window.location.hostname !== '' && window.location.protocol !== 'capacitor:')
        ? window.location.hostname
        : 'Abhinavs-MacBook-Air.local';
    socket = new WebSocket(`ws://${wsHost}:8000/ws/sign-language`);

    socket.onopen = () => {
        statusDot.classList.add('active');
        statusText.innerText = "System Ready";
        isRunning = true;
        startCapture();
        renderLoop(); // Start smooth live render loop
    };

    socket.onmessage = (event) => {
        const data = JSON.parse(event.data);
        updateUI(data);
    };

    socket.onclose = () => {
        statusDot.classList.remove('active');
        statusText.innerText = "Disconnected. Reconnecting...";
        isRunning = false;
        clearInterval(captureInterval);
        cancelAnimationFrame(animationFrameId);
        setTimeout(connectBackend, 3000);
    };

    socket.onerror = (err) => {
        console.error("WebSocket error:", err);
        statusText.innerText = "Backend Error";
    };
}

function startCapture() {
    // Send frames to backend at a modest 5 FPS for prediction
    // Lower rate = less backend queue buildup = lower latency on predictions
    captureInterval = setInterval(() => {
        if (socket && socket.readyState === WebSocket.OPEN && isRunning) {
            const tempCanvas = document.createElement('canvas');
            tempCanvas.width = 640;
            tempCanvas.height = 480;
            const tempCtx = tempCanvas.getContext('2d');
            // Send raw (un-mirrored) frame — backend flips it, same as final_pred.py
            tempCtx.drawImage(video, 0, 0, 640, 480);

            const frameData = tempCanvas.toDataURL('image/jpeg', 0.85);
            socket.send(frameData);
        }
    }, 200); // 200ms = 5 FPS
}

function updateUI(data) {
    // Update Character
    currentCharDisplay.innerText = data.current_symbol || "-";

    // Update Sentence
    if (data.sentence && data.sentence.trim() !== "") {
        sentenceDisplay.innerText = data.sentence;
    } else {
        sentenceDisplay.innerText = "Waiting for input...";
    }

    // Update Suggestions
    const suggestionBtns = suggestionsContainer.querySelectorAll('.suggestion-btn');
    if (data.suggestions) {
        data.suggestions.forEach((word, index) => {
            if (index < suggestionBtns.length) {
                if (word && word.trim() !== "") {
                    suggestionBtns[index].innerText = word;
                    suggestionBtns[index].style.display = 'block';
                    suggestionBtns[index].onclick = () => {
                        const words = sentenceDisplay.innerText.trim().split(' ');
                        words[words.length - 1] = word.toUpperCase();
                        sentenceDisplay.innerText = words.join(' ') + ' ';
                    };
                } else {
                    suggestionBtns[index].style.display = 'none';
                }
            }
        });
    }

    // Update landmark skeleton overlay image (decoded async, displayed in render loop)
    if (data.image) {
        const img = new Image();
        img.onload = () => { landmarkOverlay = img; };
        img.src = data.image;
    }
}

// Controls
btnSpeak.onclick = () => {
    const text = sentenceDisplay.innerText;
    if (text && text !== "Waiting for input...") {
        const utterance = new SpeechSynthesisUtterance(text);
        window.speechSynthesis.speak(utterance);
    }
};

btnClear.onclick = () => {
    // Send CLEAR command to backend to reset predictor state
    if (socket && socket.readyState === WebSocket.OPEN) {
        socket.send("CLEAR");
    }
    // Reset local UI immediately
    sentenceDisplay.innerText = "Waiting for input...";
    currentCharDisplay.innerText = "-";
    landmarkOverlay = null;
    suggestionsContainer.querySelectorAll('.suggestion-btn').forEach(btn => {
        btn.style.display = 'none';
    });
};

btnToggle.onclick = () => {
    isRunning = !isRunning;
    if (isRunning) {
        btnToggle.innerHTML = '<svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor"><rect x="6" y="4" width="4" height="16" rx="1"/><rect x="14" y="4" width="4" height="16" rx="1"/></svg> Stop';
        btnToggle.className = "btn btn-danger";
        statusText.innerText = "System Ready";
        renderLoop();
        if (window.showToast) window.showToast('Detection started');
    } else {
        btnToggle.innerHTML = '<svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor"><polygon points="5 3 19 12 5 21 5 3"/></svg> Start';
        btnToggle.className = "btn btn-primary";
        statusText.innerText = "Paused";
        cancelAnimationFrame(animationFrameId);
        landmarkOverlay = null;
        if (window.showToast) window.showToast('Detection paused');
    }
};

// Initialize
setupWebcam().then(() => {
    connectBackend();
});
