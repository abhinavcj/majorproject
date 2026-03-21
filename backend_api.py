import fastapi
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import numpy as np
import math
import cv2
import os
import base64
from keras.models import load_model
from cvzone.HandTrackingModule import HandDetector
from string import ascii_uppercase
import enchant

import json
import re
from pathlib import Path
from typing import List, Optional
from pydantic import BaseModel
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, StreamingResponse, HTMLResponse
import urllib.request as _urllib_req

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

os.environ["THEANO_FLAGS"] = "device=cuda, assert_no_cpu_op=True"

try:
    ddd = enchant.Dict("en-US")
except Exception as e:
    print(f"Failed to load enchant dictionary: {e}")
    ddd = None

# Global Initialization (Load once for efficiency)
print("Loading Model...")
model = load_model('cnn8grps_rad1_model.h5')
hd = HandDetector(maxHands=1)
hd2 = HandDetector(maxHands=1)
offset = 29

# Cache white template once at startup instead of reading from disk every frame
_white_template = cv2.imread('white.jpg')
if _white_template is None:
    _white_template = np.ones((400, 400, 3), dtype=np.uint8) * 255

print("Model Loaded Successfully!")

class SignLanguagePredictor:
    def __init__(self):
        self.ct = {'blank': 0}
        self.blank_flag = 0
        self.space_flag = False
        self.next_flag = True
        self.prev_char = ""
        self.count = -1
        self.ten_prev_char = [" "] * 10
        self.str = " "
        self.word = " "
        self.current_symbol = "C"
        
        self.word1 = " "
        self.word2 = " "
        self.word3 = " "
        self.word4 = " "
        self.pts = []

        for i in ascii_uppercase:
            self.ct[i] = 0

    def distance(self, x, y):
        return math.sqrt(((x[0] - y[0]) ** 2) + ((x[1] - y[1]) ** 2))

    def process_frame(self, frame_data_b64):
        # Decode base64 frame
        encoded_data = frame_data_b64.split(',')[1] if ',' in frame_data_b64 else frame_data_b64
        nparr = np.frombuffer(base64.b64decode(encoded_data), np.uint8)
        cv2image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        if cv2image is None:
            return None

        # NOTE: Browser webcam is NOT pre-flipped, so we flip here exactly like final_pred.py
        cv2image = cv2.flip(cv2image, 1)

        # Use draw=False exactly like final_pred.py video_loop
        # draw=False returns just the hands list (not a tuple), matching original behaviour
        try:
            hands = hd.findHands(cv2image, draw=False, flipType=True)
        except Exception as e:
            print(f"findHands error: {e}")
            hands = [None]

        cv2image_copy = np.array(cv2image)

        # Match final_pred.py: hands[0] is the detected hands list
        if hands and hands[0]:
            hand = hands[0]
            # hands[0] is the list of hand dicts; take the first hand
            handmap = hand[0] if isinstance(hand, list) else hand

            x, y, w, h = handmap['bbox']

            # Use EXACT same slice as final_pred.py (no bounds clamping)
            image = cv2image_copy[y - offset:y + h + offset, x - offset:x + w + offset]

            # Use cached template (copy so we don't mutate the original)
            white = _white_template.copy()

            if image is not None and image.size > 0:
                handz = hd2.findHands(image, draw=False, flipType=True)
                # Match final_pred.py: handz[0] is the detected hands list
                if handz and handz[0]:
                    handz_list = handz[0]
                    handmap2 = handz_list[0] if isinstance(handz_list, list) else handz_list
                    self.pts = handmap2['lmList']

                    os_val = ((400 - w) // 2) - 15
                    os1 = ((400 - h) // 2) - 15

                    try:
                        for t in range(0, 4, 1):
                            cv2.line(white, (self.pts[t][0] + os_val, self.pts[t][1] + os1), (self.pts[t + 1][0] + os_val, self.pts[t + 1][1] + os1), (0, 255, 0), 3)
                        for t in range(5, 8, 1):
                            cv2.line(white, (self.pts[t][0] + os_val, self.pts[t][1] + os1), (self.pts[t + 1][0] + os_val, self.pts[t + 1][1] + os1), (0, 255, 0), 3)
                        for t in range(9, 12, 1):
                            cv2.line(white, (self.pts[t][0] + os_val, self.pts[t][1] + os1), (self.pts[t + 1][0] + os_val, self.pts[t + 1][1] + os1), (0, 255, 0), 3)
                        for t in range(13, 16, 1):
                            cv2.line(white, (self.pts[t][0] + os_val, self.pts[t][1] + os1), (self.pts[t + 1][0] + os_val, self.pts[t + 1][1] + os1), (0, 255, 0), 3)
                        for t in range(17, 20, 1):
                            cv2.line(white, (self.pts[t][0] + os_val, self.pts[t][1] + os1), (self.pts[t + 1][0] + os_val, self.pts[t + 1][1] + os1), (0, 255, 0), 3)
                        cv2.line(white, (self.pts[5][0] + os_val, self.pts[5][1] + os1), (self.pts[9][0] + os_val, self.pts[9][1] + os1), (0, 255, 0), 3)
                        cv2.line(white, (self.pts[9][0] + os_val, self.pts[9][1] + os1), (self.pts[13][0] + os_val, self.pts[13][1] + os1), (0, 255, 0), 3)
                        cv2.line(white, (self.pts[13][0] + os_val, self.pts[13][1] + os1), (self.pts[17][0] + os_val, self.pts[17][1] + os1), (0, 255, 0), 3)
                        cv2.line(white, (self.pts[0][0] + os_val, self.pts[0][1] + os1), (self.pts[5][0] + os_val, self.pts[5][1] + os1), (0, 255, 0), 3)
                        cv2.line(white, (self.pts[0][0] + os_val, self.pts[0][1] + os1), (self.pts[17][0] + os_val, self.pts[17][1] + os1), (0, 255, 0), 3)

                        for i in range(21):
                            cv2.circle(white, (self.pts[i][0] + os_val, self.pts[i][1] + os1), 2, (0, 0, 255), 1)

                        self.predict(white)

                        # Send back just the skeleton overlay (already 400x400)
                        # Resize to 200x200 for the small preview — much less data
                        skeleton_small = cv2.resize(white, (200, 200))
                        _, buffer = cv2.imencode('.jpg', skeleton_small, [cv2.IMWRITE_JPEG_QUALITY, 70])
                        self._last_skeleton_b64 = base64.b64encode(buffer).decode('utf-8')
                    except Exception as e:
                        print(f"Drawing error: {e}")

        # Build response — no redundant findHands call!
        skeleton_data = getattr(self, '_last_skeleton_b64', None)
        image_field = f"data:image/jpeg;base64,{skeleton_data}" if skeleton_data else None

        return {
            "current_symbol": self.current_symbol,
            "sentence": self.str,
            "suggestions": [self.word1, self.word2, self.word3, self.word4],
            "image": image_field
        }

    def predict(self, test_image):
        white=test_image
        white = white.reshape(1, 400, 400, 3)
        prob = np.array(model.predict(white, verbose=0)[0], dtype='float32')
        ch1 = np.argmax(prob, axis=0)
        prob[ch1] = 0
        ch2 = np.argmax(prob, axis=0)
        prob[ch2] = 0
        ch3 = np.argmax(prob, axis=0)
        prob[ch3] = 0

        pl = [ch1, ch2]

        # condition for [Aemnst]
        l = [[5, 2], [5, 3], [3, 5], [3, 6], [3, 0], [3, 2], [6, 4], [6, 1], [6, 2], [6, 6], [6, 7], [6, 0], [6, 5],
             [4, 1], [1, 0], [1, 1], [6, 3], [1, 6], [5, 6], [5, 1], [4, 5], [1, 4], [1, 5], [2, 0], [2, 6], [4, 6],
             [1, 0], [5, 7], [1, 6], [6, 1], [7, 6], [2, 5], [7, 1], [5, 4], [7, 0], [7, 5], [7, 2]]
        if pl in l:
            if (self.pts[6][1] < self.pts[8][1] and self.pts[10][1] < self.pts[12][1] and self.pts[14][1] < self.pts[16][1] and self.pts[18][1] < self.pts[20][
                1]):
                ch1 = 0

        # condition for [o][s]
        l = [[2, 2], [2, 1]]
        if pl in l:
            if (self.pts[5][0] < self.pts[4][0]):
                ch1 = 0
                print("++++++++++++++++++")
                # print("00000")

        # condition for [c0][aemnst]
        l = [[0, 0], [0, 6], [0, 2], [0, 5], [0, 1], [0, 7], [5, 2], [7, 6], [7, 1]]
        pl = [ch1, ch2]
        if pl in l:
            if (self.pts[0][0] > self.pts[8][0] and self.pts[0][0] > self.pts[4][0] and self.pts[0][0] > self.pts[12][0] and self.pts[0][0] > self.pts[16][
                0] and self.pts[0][0] > self.pts[20][0]) and self.pts[5][0] > self.pts[4][0]:
                ch1 = 2

        # condition for [c0][aemnst]
        l = [[6, 0], [6, 6], [6, 2]]
        pl = [ch1, ch2]
        if pl in l:
            if self.distance(self.pts[8], self.pts[16]) < 52:
                ch1 = 2


        # condition for [gh][bdfikruvw]
        l = [[1, 4], [1, 5], [1, 6], [1, 3], [1, 0]]
        pl = [ch1, ch2]

        if pl in l:
            if self.pts[6][1] > self.pts[8][1] and self.pts[14][1] < self.pts[16][1] and self.pts[18][1] < self.pts[20][1] and self.pts[0][0] < self.pts[8][
                0] and self.pts[0][0] < self.pts[12][0] and self.pts[0][0] < self.pts[16][0] and self.pts[0][0] < self.pts[20][0]:
                ch1 = 3



        # con for [gh][l]
        l = [[4, 6], [4, 1], [4, 5], [4, 3], [4, 7]]
        pl = [ch1, ch2]
        if pl in l:
            if self.pts[4][0] > self.pts[0][0]:
                ch1 = 3

        # con for [gh][pqz]
        l = [[5, 3], [5, 0], [5, 7], [5, 4], [5, 2], [5, 1], [5, 5]]
        pl = [ch1, ch2]
        if pl in l:
            if self.pts[2][1] + 15 < self.pts[16][1]:
                ch1 = 3

        # con for [l][x]
        l = [[6, 4], [6, 1], [6, 2]]
        pl = [ch1, ch2]
        if pl in l:
            if self.distance(self.pts[4], self.pts[11]) > 55:
                ch1 = 4

        # con for [l][d]
        l = [[1, 4], [1, 6], [1, 1]]
        pl = [ch1, ch2]
        if pl in l:
            if (self.distance(self.pts[4], self.pts[11]) > 50) and (
                    self.pts[6][1] > self.pts[8][1] and self.pts[10][1] < self.pts[12][1] and self.pts[14][1] < self.pts[16][1] and self.pts[18][1] <
                    self.pts[20][1]):
                ch1 = 4

        # con for [l][gh]
        l = [[3, 6], [3, 4]]
        pl = [ch1, ch2]
        if pl in l:
            if (self.pts[4][0] < self.pts[0][0]):
                ch1 = 4

        # con for [l][c0]
        l = [[2, 2], [2, 5], [2, 4]]
        pl = [ch1, ch2]
        if pl in l:
            if (self.pts[1][0] < self.pts[12][0]):
                ch1 = 4

        # con for [l][c0]
        l = [[2, 2], [2, 5], [2, 4]]
        pl = [ch1, ch2]
        if pl in l:
            if (self.pts[1][0] < self.pts[12][0]):
                ch1 = 4

        # con for [gh][z]
        l = [[3, 6], [3, 5], [3, 4]]
        pl = [ch1, ch2]
        if pl in l:
            if (self.pts[6][1] > self.pts[8][1] and self.pts[10][1] < self.pts[12][1] and self.pts[14][1] < self.pts[16][1] and self.pts[18][1] < self.pts[20][
                1]) and self.pts[4][1] > self.pts[10][1]:
                ch1 = 5

        # con for [gh][pq]
        l = [[3, 2], [3, 1], [3, 6]]
        pl = [ch1, ch2]
        if pl in l:
            if self.pts[4][1] + 17 > self.pts[8][1] and self.pts[4][1] + 17 > self.pts[12][1] and self.pts[4][1] + 17 > self.pts[16][1] and self.pts[4][
                1] + 17 > self.pts[20][1]:
                ch1 = 5

        # con for [l][pqz]
        l = [[4, 4], [4, 5], [4, 2], [7, 5], [7, 6], [7, 0]]
        pl = [ch1, ch2]
        if pl in l:
            if self.pts[4][0] > self.pts[0][0]:
                ch1 = 5

        # con for [pqz][aemnst]
        l = [[0, 2], [0, 6], [0, 1], [0, 5], [0, 0], [0, 7], [0, 4], [0, 3], [2, 7]]
        pl = [ch1, ch2]
        if pl in l:
            if self.pts[0][0] < self.pts[8][0] and self.pts[0][0] < self.pts[12][0] and self.pts[0][0] < self.pts[16][0] and self.pts[0][0] < self.pts[20][0]:
                ch1 = 5

        # con for [pqz][yj]
        l = [[5, 7], [5, 2], [5, 6]]
        pl = [ch1, ch2]
        if pl in l:
            if self.pts[3][0] < self.pts[0][0]:
                ch1 = 7

        # con for [l][yj]
        l = [[4, 6], [4, 2], [4, 4], [4, 1], [4, 5], [4, 7]]
        pl = [ch1, ch2]
        if pl in l:
            if self.pts[6][1] < self.pts[8][1]:
                ch1 = 7

        # con for [x][yj]
        l = [[6, 7], [0, 7], [0, 1], [0, 0], [6, 4], [6, 6], [6, 5], [6, 1]]
        pl = [ch1, ch2]
        if pl in l:
            if self.pts[18][1] > self.pts[20][1]:
                ch1 = 7

        # condition for [x][aemnst]
        l = [[0, 4], [0, 2], [0, 3], [0, 1], [0, 6]]
        pl = [ch1, ch2]
        if pl in l:
            if self.pts[5][0] > self.pts[16][0]:
                ch1 = 6


        # condition for [yj][x]
        print("2222  ch1=+++++++++++++++++", ch1, ",", ch2)
        l = [[7, 2]]
        pl = [ch1, ch2]
        if pl in l:
            if self.pts[18][1] < self.pts[20][1] and self.pts[8][1] < self.pts[10][1]:
                ch1 = 6

        # condition for [c0][x]
        l = [[2, 1], [2, 2], [2, 6], [2, 7], [2, 0]]
        pl = [ch1, ch2]
        if pl in l:
            if self.distance(self.pts[8], self.pts[16]) > 50:
                ch1 = 6

        # con for [l][x]

        l = [[4, 6], [4, 2], [4, 1], [4, 4]]
        pl = [ch1, ch2]
        if pl in l:
            if self.distance(self.pts[4], self.pts[11]) < 60:
                ch1 = 6

        # con for [x][d]
        l = [[1, 4], [1, 6], [1, 0], [1, 2]]
        pl = [ch1, ch2]
        if pl in l:
            if self.pts[5][0] - self.pts[4][0] - 15 > 0:
                ch1 = 6

        # con for [b][pqz]
        l = [[5, 0], [5, 1], [5, 4], [5, 5], [5, 6], [6, 1], [7, 6], [0, 2], [7, 1], [7, 4], [6, 6], [7, 2], [5, 0],
             [6, 3], [6, 4], [7, 5], [7, 2]]
        pl = [ch1, ch2]
        if pl in l:
            if (self.pts[6][1] > self.pts[8][1] and self.pts[10][1] > self.pts[12][1] and self.pts[14][1] > self.pts[16][1] and self.pts[18][1] > self.pts[20][
                1]):
                ch1 = 1

        # con for [f][pqz]
        l = [[6, 1], [6, 0], [0, 3], [6, 4], [2, 2], [0, 6], [6, 2], [7, 6], [4, 6], [4, 1], [4, 2], [0, 2], [7, 1],
             [7, 4], [6, 6], [7, 2], [7, 5], [7, 2]]
        pl = [ch1, ch2]
        if pl in l:
            if (self.pts[6][1] < self.pts[8][1] and self.pts[10][1] > self.pts[12][1] and self.pts[14][1] > self.pts[16][1] and
                    self.pts[18][1] > self.pts[20][1]):
                ch1 = 1

        l = [[6, 1], [6, 0], [4, 2], [4, 1], [4, 6], [4, 4]]
        pl = [ch1, ch2]
        if pl in l:
            if (self.pts[10][1] > self.pts[12][1] and self.pts[14][1] > self.pts[16][1] and
                    self.pts[18][1] > self.pts[20][1]):
                ch1 = 1

        # con for [d][pqz]
        fg = 19
        # print("_________________ch1=",ch1," ch2=",ch2)
        l = [[5, 0], [3, 4], [3, 0], [3, 1], [3, 5], [5, 5], [5, 4], [5, 1], [7, 6]]
        pl = [ch1, ch2]
        if pl in l:
            if ((self.pts[6][1] > self.pts[8][1] and self.pts[10][1] < self.pts[12][1] and self.pts[14][1] < self.pts[16][1] and
                 self.pts[18][1] < self.pts[20][1]) and (self.pts[2][0] < self.pts[0][0]) and self.pts[4][1] > self.pts[14][1]):
                ch1 = 1

        l = [[4, 1], [4, 2], [4, 4]]
        pl = [ch1, ch2]
        if pl in l:
            if (self.distance(self.pts[4], self.pts[11]) < 50) and (
                    self.pts[6][1] > self.pts[8][1] and self.pts[10][1] < self.pts[12][1] and self.pts[14][1] < self.pts[16][1] and self.pts[18][1] <
                    self.pts[20][1]):
                ch1 = 1

        l = [[3, 4], [3, 0], [3, 1], [3, 5], [3, 6]]
        pl = [ch1, ch2]
        if pl in l:
            if ((self.pts[6][1] > self.pts[8][1] and self.pts[10][1] < self.pts[12][1] and self.pts[14][1] < self.pts[16][1] and
                 self.pts[18][1] < self.pts[20][1]) and (self.pts[2][0] < self.pts[0][0]) and self.pts[14][1] < self.pts[4][1]):
                ch1 = 1

        l = [[6, 6], [6, 4], [6, 1], [6, 2]]
        pl = [ch1, ch2]
        if pl in l:
            if self.pts[5][0] - self.pts[4][0] - 15 < 0:
                ch1 = 1

        # con for [i][pqz]
        l = [[5, 4], [5, 5], [5, 1], [0, 3], [0, 7], [5, 0], [0, 2], [6, 2], [7, 5], [7, 1], [7, 6], [7, 7]]
        pl = [ch1, ch2]
        if pl in l:
            if ((self.pts[6][1] < self.pts[8][1] and self.pts[10][1] < self.pts[12][1] and self.pts[14][1] < self.pts[16][1] and
                 self.pts[18][1] > self.pts[20][1])):
                ch1 = 1

        # con for [yj][bfdi]
        l = [[1, 5], [1, 7], [1, 1], [1, 6], [1, 3], [1, 0]]
        pl = [ch1, ch2]
        if pl in l:
            if (self.pts[4][0] < self.pts[5][0] + 15) and (
            (self.pts[6][1] < self.pts[8][1] and self.pts[10][1] < self.pts[12][1] and self.pts[14][1] < self.pts[16][1] and
             self.pts[18][1] > self.pts[20][1])):
                ch1 = 7

        # con for [uvr]
        l = [[5, 5], [5, 0], [5, 4], [5, 1], [4, 6], [4, 1], [7, 6], [3, 0], [3, 5]]
        pl = [ch1, ch2]
        if pl in l:
            if ((self.pts[6][1] > self.pts[8][1] and self.pts[10][1] > self.pts[12][1] and self.pts[14][1] < self.pts[16][1] and
                 self.pts[18][1] < self.pts[20][1])) and self.pts[4][1] > self.pts[14][1]:
                ch1 = 1

        # con for [w]
        fg = 13
        l = [[3, 5], [3, 0], [3, 6], [5, 1], [4, 1], [2, 0], [5, 0], [5, 5]]
        pl = [ch1, ch2]
        if pl in l:
            if not (self.pts[0][0] + fg < self.pts[8][0] and self.pts[0][0] + fg < self.pts[12][0] and self.pts[0][0] + fg < self.pts[16][0] and
                    self.pts[0][0] + fg < self.pts[20][0]) and not (
                    self.pts[0][0] > self.pts[8][0] and self.pts[0][0] > self.pts[12][0] and self.pts[0][0] > self.pts[16][0] and self.pts[0][0] > self.pts[20][
                0]) and self.distance(self.pts[4], self.pts[11]) < 50:
                ch1 = 1

        # con for [w]

        l = [[5, 0], [5, 5], [0, 1]]
        pl = [ch1, ch2]
        if pl in l:
            if self.pts[6][1] > self.pts[8][1] and self.pts[10][1] > self.pts[12][1] and self.pts[14][1] > self.pts[16][1]:
                ch1 = 1

        # -------------------------condn for 8 groups  ends

        # -------------------------condn for subgroups  starts
        #
        if ch1 == 0:
            ch1 = 'S'
            if self.pts[4][0] < self.pts[6][0] and self.pts[4][0] < self.pts[10][0] and self.pts[4][0] < self.pts[14][0] and self.pts[4][0] < self.pts[18][0]:
                ch1 = 'A'
            if self.pts[4][0] > self.pts[6][0] and self.pts[4][0] < self.pts[10][0] and self.pts[4][0] < self.pts[14][0] and self.pts[4][0] < self.pts[18][
                0] and self.pts[4][1] < self.pts[14][1] and self.pts[4][1] < self.pts[18][1]:
                ch1 = 'T'
            if self.pts[4][1] > self.pts[8][1] and self.pts[4][1] > self.pts[12][1] and self.pts[4][1] > self.pts[16][1] and self.pts[4][1] > self.pts[20][1]:
                ch1 = 'E'
            if self.pts[4][0] > self.pts[6][0] and self.pts[4][0] > self.pts[10][0] and self.pts[4][0] > self.pts[14][0] and self.pts[4][1] < self.pts[18][1]:
                ch1 = 'M'
            if self.pts[4][0] > self.pts[6][0] and self.pts[4][0] > self.pts[10][0] and self.pts[4][1] < self.pts[18][1] and self.pts[4][1] < self.pts[14][1]:
                ch1 = 'N'

        if ch1 == 2:
            if self.distance(self.pts[12], self.pts[4]) > 42:
                ch1 = 'C'
            else:
                ch1 = 'O'

        if ch1 == 3:
            if (self.distance(self.pts[8], self.pts[12])) > 72:
                ch1 = 'G'
            else:
                ch1 = 'H'

        if ch1 == 7:
            if self.distance(self.pts[8], self.pts[4]) > 42:
                ch1 = 'Y'
            else:
                ch1 = 'J'

        if ch1 == 4:
            ch1 = 'L'

        if ch1 == 6:
            ch1 = 'X'

        if ch1 == 5:
            if self.pts[4][0] > self.pts[12][0] and self.pts[4][0] > self.pts[16][0] and self.pts[4][0] > self.pts[20][0]:
                if self.pts[8][1] < self.pts[5][1]:
                    ch1 = 'Z'
                else:
                    ch1 = 'Q'
            else:
                ch1 = 'P'

        if ch1 == 1:
            if (self.pts[6][1] > self.pts[8][1] and self.pts[10][1] > self.pts[12][1] and self.pts[14][1] > self.pts[16][1] and self.pts[18][1] > self.pts[20][
                1]):
                ch1 = 'B'
            if (self.pts[6][1] > self.pts[8][1] and self.pts[10][1] < self.pts[12][1] and self.pts[14][1] < self.pts[16][1] and self.pts[18][1] < self.pts[20][
                1]):
                ch1 = 'D'
            if (self.pts[6][1] < self.pts[8][1] and self.pts[10][1] > self.pts[12][1] and self.pts[14][1] > self.pts[16][1] and self.pts[18][1] > self.pts[20][
                1]):
                ch1 = 'F'
            if (self.pts[6][1] < self.pts[8][1] and self.pts[10][1] < self.pts[12][1] and self.pts[14][1] < self.pts[16][1] and self.pts[18][1] > self.pts[20][
                1]):
                ch1 = 'I'
            if (self.pts[6][1] > self.pts[8][1] and self.pts[10][1] > self.pts[12][1] and self.pts[14][1] > self.pts[16][1] and self.pts[18][1] < self.pts[20][
                1]):
                ch1 = 'W'
            if (self.pts[6][1] > self.pts[8][1] and self.pts[10][1] > self.pts[12][1] and self.pts[14][1] < self.pts[16][1] and self.pts[18][1] < self.pts[20][
                1]) and self.pts[4][1] < self.pts[9][1]:
                ch1 = 'K'
            if ((self.distance(self.pts[8], self.pts[12]) - self.distance(self.pts[6], self.pts[10])) < 8) and (
                    self.pts[6][1] > self.pts[8][1] and self.pts[10][1] > self.pts[12][1] and self.pts[14][1] < self.pts[16][1] and self.pts[18][1] <
                    self.pts[20][1]):
                ch1 = 'U'
            if ((self.distance(self.pts[8], self.pts[12]) - self.distance(self.pts[6], self.pts[10])) >= 8) and (
                    self.pts[6][1] > self.pts[8][1] and self.pts[10][1] > self.pts[12][1] and self.pts[14][1] < self.pts[16][1] and self.pts[18][1] <
                    self.pts[20][1]) and (self.pts[4][1] > self.pts[9][1]):
                ch1 = 'V'

            if (self.pts[8][0] > self.pts[12][0]) and (
                    self.pts[6][1] > self.pts[8][1] and self.pts[10][1] > self.pts[12][1] and self.pts[14][1] < self.pts[16][1] and self.pts[18][1] <
                    self.pts[20][1]):
                ch1 = 'R'

        if ch1 == 1 or ch1 =='E' or ch1 =='S' or ch1 =='X' or ch1 =='Y' or ch1 =='B':
            if (self.pts[6][1] > self.pts[8][1] and self.pts[10][1] < self.pts[12][1] and self.pts[14][1] < self.pts[16][1] and self.pts[18][1] > self.pts[20][1]):
                ch1=" "



        print(self.pts[4][0] < self.pts[5][0])
        if ch1 == 'E' or ch1=='Y' or ch1=='B':
            if (self.pts[4][0] < self.pts[5][0]) and (self.pts[6][1] > self.pts[8][1] and self.pts[10][1] > self.pts[12][1] and self.pts[14][1] > self.pts[16][1] and self.pts[18][1] > self.pts[20][1]):
                ch1="next"


        if ch1 in ['Next', 'next', 'B', 'C', 'H', 'F', 'X']:
            if (self.pts[0][0] > self.pts[8][0] and self.pts[0][0] > self.pts[12][0] and self.pts[0][0] > self.pts[16][0] and self.pts[0][0] > self.pts[20][0]) and (self.pts[4][1] < self.pts[8][1] and self.pts[4][1] < self.pts[12][1] and self.pts[4][1] < self.pts[16][1] and self.pts[4][1] < self.pts[20][1]) and (self.pts[4][1] < self.pts[6][1] and self.pts[4][1] < self.pts[10][1] and self.pts[4][1] < self.pts[14][1] and self.pts[4][1] < self.pts[18][1]):
                ch1 = 'Backspace'


        if str(ch1)=="next" and str(self.prev_char)!="next":
            if str(self.ten_prev_char[(self.count-2)%10])!="next":
                if str(self.ten_prev_char[(self.count-2)%10])=="Backspace":
                    self.str=self.str[0:-1]
                else:
                    if str(self.ten_prev_char[(self.count - 2) % 10]) != "Backspace":
                        self.str = self.str + str(self.ten_prev_char[(self.count-2)%10])
            else:
                if str(self.ten_prev_char[(self.count - 0) % 10]) != "Backspace":
                    self.str = self.str + str(self.ten_prev_char[(self.count - 0) % 10])


        if str(ch1)==" " and str(self.prev_char)!=" ":
            self.str = self.str + " "

        self.prev_char = str(ch1)
        self.current_symbol = str(ch1)
        self.count += 1
        self.ten_prev_char[self.count%10] = str(ch1)


        if len(self.str.strip())!=0:
            st=self.str.rfind(" ")
            ed=len(self.str)
            word=self.str[st+1:ed]
            self.word=word
            if len(word.strip())!=0 and ddd is not None:
                try:
                    ddd.check(word)
                    suggestions = ddd.suggest(word)
                    lenn = len(suggestions)
                    if lenn >= 4:
                        self.word4 = suggestions[3]

                    if lenn >= 3:
                        self.word3 = suggestions[2]

                    if lenn >= 2:
                        self.word2 = suggestions[1]

                    if lenn >= 1:
                        self.word1 = suggestions[0]
                except Exception as e:
                    pass
            else:
                self.word1 = " "
                self.word2 = " "
                self.word3 = " "
                self.word4 = " "


@app.websocket("/ws/sign-language")
async def sign_language_endpoint(websocket: WebSocket):
    await websocket.accept()
    predictor = SignLanguagePredictor()
    
    try:
        while True:
            # Receive frame data from the browser (base64 PNG/JPEG) or a command string
            frame_data = await websocket.receive_text()

            # Handle special commands
            if frame_data == "CLEAR":
                predictor.__init__()  # Reset all predictor state
                await websocket.send_json({
                    "current_symbol": "-",
                    "sentence": " ",
                    "suggestions": [" ", " ", " ", " "],
                    "image": None
                })
                continue
            
            # Process frame and get prediction
            result = predictor.process_frame(frame_data)
            
            if result:
                # Send result back to the browser
                await websocket.send_json(result)
    
    except WebSocketDisconnect:
        print("Client disconnected from WebSocket")
    except Exception as e:
        print(f"Error in websocket connection: {e}")

@app.get("/")
def read_root():
    return {"message": "AccessAI Backend API is Running!"}

# ── Text-to-Sign App Integration ───────────────────────────────────────────────

BASE_DIR = Path(__file__).parent / "WLASL" / "text_to_sign"
GLOSS_INDEX_PATH = BASE_DIR / "gloss_index.json"
VIDEOS_DIR = BASE_DIR / "videos"

# ── Load gloss index ───────────────────────────────────────────────────────────
if not GLOSS_INDEX_PATH.exists():
    print("Warning: gloss_index.json not found! Text-to-sign might not work properly.")
    GLOSS_INDEX = {}
else:
    with open(GLOSS_INDEX_PATH) as f:
        GLOSS_INDEX = json.load(f)

# Pre-build a set of available (downloaded) video IDs for fast lookup
def get_available_ids():
    if not VIDEOS_DIR.exists():
        return set()
    return {p.stem for p in VIDEOS_DIR.glob("*.mp4")}

def is_valid_mp4(video_id: str) -> bool:
    """Check if a downloaded .mp4 file is a real video (not an HTML error page)."""
    path = VIDEOS_DIR / f"{video_id}.mp4"
    if not path.exists():
        return False
    try:
        with open(path, "rb") as f:
            header = f.read(12)
        return len(header) >= 8 and header[4:8] in (b"ftyp", b"moov", b"mdat", b"free", b"wide", b"skip")
    except Exception:
        return False

# Serve static files (videos folder)
VIDEOS_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/video-files", StaticFiles(directory=str(VIDEOS_DIR)), name="videos")

# ── Models ─────────────────────────────────────────────────────────────────────
class TranslateRequest(BaseModel):
    text: str

class SignResult(BaseModel):
    word: str
    gloss: Optional[str]
    video_id: Optional[str]
    local_url: Optional[str]
    remote_url: Optional[str]
    found: bool
    fingerspell: Optional[List[str]]
    source: Optional[str]

# ── Text processing ────────────────────────────────────────────────────────────
def tokenize(text: str) -> List[str]:
    text = text.lower().strip()
    text = re.sub(r"[^\w\s'-]", " ", text)
    words = text.split()
    return [w.strip("'-") for w in words if w.strip("'-")]

def lookup_gloss(word: str, available_ids: set):
    candidates = [word]
    if word.endswith("'s"):
        candidates.append(word[:-2])
    if word.endswith("ing") and len(word) > 5:
        candidates.append(word[:-3])
        candidates.append(word[:-3] + "e")
    if word.endswith("ed") and len(word) > 4:
        candidates.append(word[:-2])
        candidates.append(word[:-1])
    if word.endswith("s") and len(word) > 3:
        candidates.append(word[:-1])

    for candidate in candidates:
        if candidate in GLOSS_INDEX:
            return candidate, GLOSS_INDEX[candidate]
    return None, []

def pick_best_instance(instances: list, available_ids: set):
    for inst in instances:
        if inst["video_id"] in available_ids:
            return inst
    for inst in instances:
        if not inst["is_youtube"]:
            return inst
    return instances[0] if instances else None

# ── API Endpoints ──────────────────────────────────────────────────────────────

@app.post("/translate", response_model=List[SignResult])
def translate(req: TranslateRequest):
    available_ids = get_available_ids()
    words = tokenize(req.text)
    if not words:
        return []

    results = []
    for word in words:
        gloss, instances = lookup_gloss(word, available_ids)

        if gloss and instances:
            best = pick_best_instance(instances, available_ids)
            video_id = best["video_id"]
            is_local = video_id in available_ids and is_valid_mp4(video_id)
            
            if is_local:
                results.append(SignResult(
                    word=word,
                    gloss=gloss,
                    video_id=video_id,
                    local_url=f"/video/{video_id}",
                    remote_url=None,
                    found=True,
                    fingerspell=None,
                    source=best.get("source"),
                ))
                continue

        for char in word:
            if not char.isalpha():
                continue
            char = char.lower()
            l_gloss, l_instances = lookup_gloss(char, available_ids)
            
            gif_name = f"letter_{char}.gif"
            gif_path = VIDEOS_DIR / gif_name
            
            if l_gloss and l_instances:
                best = pick_best_instance(l_instances, available_ids)
                video_id = best["video_id"]
                is_local = video_id in available_ids and is_valid_mp4(video_id)
                
                if is_local:
                    results.append(SignResult(
                        word=char.upper(),
                        gloss=l_gloss,
                        video_id=video_id,
                        local_url=f"/video/{video_id}",
                        remote_url=None,
                        found=True,
                        fingerspell=None,
                        source=best.get("source"),
                    ))
                    continue
            
            if gif_path.exists():
                results.append(SignResult(
                    word=char.upper(),
                    gloss=f"Letter {char.upper()}",
                    video_id=f"letter_{char}",
                    local_url=f"/video/{gif_name}",
                    remote_url=None,
                    found=True,
                    fingerspell=None,
                    source="Lifeprint",
                ))
            else:
                results.append(SignResult(
                    word=char.upper(),
                    gloss=None,
                    video_id=None,
                    local_url=None,
                    remote_url=None,
                    found=False,
                    fingerspell=[char.upper()],
                    source=None,
                ))
            results.append(SignResult(
                word="_SPACE_",
                gloss=None,
                video_id=None,
                local_url=None,
                remote_url=None,
                found=False,
                fingerspell=None,
                source="spacer",
            ))

    return results

@app.get("/video/{video_id}")
def serve_video(video_id: str):
    video_id = re.sub(r"[^a-zA-Z0-9._-]", "", video_id)
    
    mp4_path = VIDEOS_DIR / f"{video_id}"
    if not mp4_path.suffix:
        mp4_path = VIDEOS_DIR / f"{video_id}.mp4"
    if mp4_path.exists():
        return FileResponse(str(mp4_path), media_type="video/mp4")
    
    gif_path = VIDEOS_DIR / f"{video_id}"
    if not gif_path.suffix:
        gif_path = VIDEOS_DIR / f"{video_id}.gif"
    if gif_path.exists():
        return FileResponse(str(gif_path), media_type="image/gif")
        
    raise HTTPException(status_code=404, detail=f"Video {video_id} not found locally.")

@app.get("/proxy-video")
def proxy_video(url: str):
    if not url.startswith("http"):
        raise HTTPException(status_code=400, detail="Invalid URL")
    try:
        req_headers = {"User-Agent": "Mozilla/5.0", "Referer": url}
        req = _urllib_req.Request(url, headers=req_headers)
        resp = _urllib_req.urlopen(req, timeout=15)
        content_type = resp.headers.get("Content-Type", "video/mp4")
        
        def iter_content():
            while True:
                chunk = resp.read(8192)
                if not chunk:
                    break
                yield chunk
        
        return StreamingResponse(iter_content(), media_type=content_type)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Proxy failed: {e}")

@app.get("/glosses")
def list_glosses():
    available_ids = get_available_ids()
    result = []
    for gloss, instances in GLOSS_INDEX.items():
        has_local = any(inst["video_id"] in available_ids for inst in instances)
        has_direct = any(not inst["is_youtube"] for inst in instances)
        result.append({
            "gloss": gloss,
            "local": has_local,
            "direct_available": has_direct,
            "instance_count": len(instances),
        })
    return result

@app.get("/stats")
def stats():
    available_ids = get_available_ids()
    total_glosses = len(GLOSS_INDEX)
    local_glosses = sum(
        1 for instances in GLOSS_INDEX.values()
        if any(inst["video_id"] in available_ids for inst in instances)
    )
    direct_glosses = sum(
        1 for instances in GLOSS_INDEX.values()
        if any(not inst["is_youtube"] for inst in instances)
    )
    return {
        "total_glosses": total_glosses,
        "local_glosses": local_glosses,
        "direct_link_glosses": direct_glosses,
        "downloaded_videos": len(available_ids),
    }
