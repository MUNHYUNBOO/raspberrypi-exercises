import cv2
import time
from ultralytics import YOLO

model = YOLO("yolov8n_ncnn_model")
cap = cv2.VideoCapture(0)

while True:
    ok, frame = cap.read()
    if not ok:
        break

    results = model(frame, verbose=False)
    names = [model.names[int(c)] for c in results[0].boxes.cls]

    if names:
        print("감지됨:", ", ".join(names))
        cv2.imwrite("last_detect.jpg", results[0].plot())

    time.sleep(0.5)