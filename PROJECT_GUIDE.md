# Project Guide: Sign Language To Text and Speech Conversion

This project is a real-time Sign Language detection and translation system that uses Computer Vision (OpenCV, MediaPipe) and Deep Learning (CNN) to convert hand gestures into text and speech.

## 🏗️ Architecture Overview

The system follows a **Client-Server architecture**:
1.  **Frontend (Client):** A web-based interface built with HTML, CSS, and Vanilla JavaScript.
2.  **Backend (Server):** A Python-based FastAPI server that hosts the Deep Learning model and handles WebSocket communication.

---

## 🛰️ How the Data Flows

1.  **Webcam Capture:** The frontend uses the browser's `navigator.mediaDevices.getUserMedia` to access your webcam.
2.  **Frame Transmission:** Every 200ms (5 FPS), a frame is captured from the video stream, converted to JPEG (Base64), and sent to the backend via a **WebSocket** connection.
3.  **Backend Processing (`backend_api.py`):**
    *   **Hand Detection:** Uses `cvzone.HandTrackingModule` (MediaPipe) to find your hand.
    *   **Skeleton Generation:** If a hand is found, it extracts hand landmarks (21 points) and draws them onto a 400x400 "white" canvas. This isolates the *shape* of the hand from the background.
    *   **ML Prediction:** The isolated skeleton image is fed into a **Convolutional Neural Network (CNN)** (`cnn8grps_rad1_model.h5`).
    *   **Post-Processing:** The system maps the model's output to a character. It handles specific rules for letters like 'A', 'S', 'T', etc., and manages sentence formation logic.
4.  **Result Feedback:** The backend sends a JSON response back to the frontend containing:
    *   The predicted character.
    *   The current sentence.
    *   Word suggestions (using the `enchant` dictionary).
    *   A small preview image of the detected skeleton.
5.  **UI Update:** The frontend updates the display in real-time. If you perform a "next" gesture, the character is added to the sentence. You can also click word suggestions to complete your sentence.
6.  **Speech Synthesis:** Clicking "Speak" uses the browser's built-in Web Speech API to read the sentence aloud.

---

## 🛠️ Key Technologies

*   **Deep Learning:** Keras/TensorFlow (CNN Model)
*   **Computer Vision:** OpenCV, MediaPipe, Cvzone
*   **Backend:** FastAPI, Uvicorn (WebSocket support)
*   **Natural Language:** PyEnchant (Spell check and word suggestions)
*   **Frontend:** HTML5, CSS3 (Glassmorphism design), JavaScript

---

## 📁 Key Files Explained

*   [index.html](file:///Users/abhinav/Downloads/Sign-Language-To-Text-and-Speech-Conversion/index.html): Main UI structure.
*   [app.js](file:///Users/abhinav/Downloads/Sign-Language-To-Text-and-Speech-Conversion/app.js): Handles webcam, WebSocket communication, and UI updates.
*   [backend_api.py](file:///Users/abhinav/Downloads/Sign-Language-To-Text-and-Speech-Conversion/backend_api.py): The "engine" that runs the ML model and processes hand landmarks.
*   [cnn8grps_rad1_model.h5](file:///Users/abhinav/Downloads/Sign-Language-To-Text-and-Speech-Conversion/cnn8grps_rad1_model.h5): The trained Deep Learning model file.
*   [style.css](file:///Users/abhinav/Downloads/Sign-Language-To-Text-and-Speech-Conversion/style.css): Modern responsive design styles.
*   [howtorun.txt](file:///Users/abhinav/Downloads/Sign-Language-To-Text-and-Speech-Conversion/howtorun.txt): Directions for setting up and running the app.

---

## 🔥 Recent Optimizations
We recently optimized the backend to be **2x faster** by:
1.  Reducing redundant hand detection calls.
2.  Switching to smaller image transfers (200x200 vs 640x480).
3.  Caching assets in memory to avoid constant disk access.
