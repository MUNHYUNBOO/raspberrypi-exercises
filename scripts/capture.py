import cv2

cap = cv2.VideoCapture(0)
ok, frame = cap.read()
if ok:
    cv2.imwrite("test.jpg", frame)
cap.release()