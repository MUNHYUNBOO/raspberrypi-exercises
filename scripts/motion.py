import cv2
import time
from datetime import datetime

cap = cv2.VideoCapture(0)
prev_gray = None
THRESHOLD = 100
MIN_AREA = 500

while True:
    ok, frame = cap.read()
    if not ok:
        break
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    gray = cv2.GaussianBlur(gray, (21, 21), 0)

    if prev_gray is None:
        prev_gray = gray
        continue

    diff = cv2.absdiff(prev_gray, gray)
    thresh = cv2.threshold(diff, THRESHOLD, 255, cv2.THRESH_BINARY)[1]
    thresh = cv2.dilate(thresh, None, iterations=2)
    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    if any(cv2.contourArea(c) > MIN_AREA for c in contours):
        fname = f"motion_{datetime.now():%Y%m%d_%H%M%S}.jpg"
        cv2.imwrite(fname, frame)
        print(f"움직임 감지 → {fname}")
        time.sleep(2)

    prev_gray = gray