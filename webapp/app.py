"""
Raspberry Pi 5 + Flask : 웹캠 스트림(YOLO 객체 인식) + CPU 온도 그래프

실행:  python3 app.py
접속:  http://<라즈베리파이 IP>:5000   (IP는 `hostname -I` 로 확인)

폴더 구조:
  pi_monitor/
  ├── app.py
  └── templates/
      └── index.html
"""
import time
import threading
from collections import deque

from flask import Flask, Response, jsonify, render_template
from ultralytics import YOLO

# ── 설정 ─────────────────────────────────────────────────────────
USE_PICAMERA2 = False   # 라즈베리파이 카메라 모듈(CSI 리본 케이블)이면 True, USB 웹캠이면 False
CAMERA_INDEX  = 0       # USB 웹캠 번호 (/dev/video0 → 0). 여러 개면 `ls /dev/video*` 로 확인
FRAME_WIDTH   = 640
FRAME_HEIGHT  = 480
JPEG_QUALITY  = 80      # 1~100, 높을수록 선명하지만 대역폭 증가
TEMP_INTERVAL = 1.0     # CPU 온도 측정 주기(초)
TEMP_HISTORY  = 300     # 그래프에 유지할 데이터 개수 (300개 × 1초 = 최근 5분)
YOLO_MODEL_PATH = "../scripts/yolov8n_ncnn_model"  # 실제 모델 폴더 경로로 수정

app = Flask(__name__)
camera = None


# ── 카메라 ────────────────────────────────────────────────────────
class Camera:
    """백그라운드 스레드에서 프레임을 계속 읽어 YOLO로 인식한 최신 JPEG 한 장을 보관한다.
    브라우저가 여러 개 접속해도 카메라와 모델은 한 번만 연다."""

    def __init__(self):
        import cv2
        self.cv2 = cv2
        self.model = YOLO(YOLO_MODEL_PATH)
        self.frame = None
        self.seq = 0                       # 새 프레임마다 1씩 증가 (중복 전송 방지용)
        self.lock = threading.Lock()

        if USE_PICAMERA2:
            from picamera2 import Picamera2
            self.cam = Picamera2()
            # picamera2의 "RGB888"은 실제 메모리 순서가 BGR이라 OpenCV에 그대로 넣어도 색이 맞다.
            cfg = self.cam.create_video_configuration(
                main={"size": (FRAME_WIDTH, FRAME_HEIGHT), "format": "RGB888"}
            )
            self.cam.configure(cfg)
            self.cam.start()
        else:
            self.cam = cv2.VideoCapture(CAMERA_INDEX)
            self.cam.set(cv2.CAP_PROP_FRAME_WIDTH, FRAME_WIDTH)
            self.cam.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_HEIGHT)
            if not self.cam.isOpened():
                raise RuntimeError(
                    f"웹캠을 열 수 없습니다 (index={CAMERA_INDEX}). "
                    "`ls /dev/video*` 로 장치 번호를 확인하세요."
                )

        threading.Thread(target=self._loop, daemon=True).start()

    def _loop(self):
        cv2 = self.cv2
        while True:
            if USE_PICAMERA2:
                frame = self.cam.capture_array()
            else:
                ok, frame = self.cam.read()
                if not ok:
                    time.sleep(0.05)
                    continue

            results = self.model(frame, verbose=False)
            frame = results[0].plot()

            ok, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, JPEG_QUALITY])
            if ok:
                with self.lock:
                    self.frame = buf.tobytes()
                    self.seq += 1

    def get_frame(self):
        with self.lock:
            return self.frame, self.seq


# ── CPU 온도 ──────────────────────────────────────────────────────
temp_history = deque(maxlen=TEMP_HISTORY)   # {"t": unix time, "temp": °C}
temp_lock = threading.Lock()


def read_cpu_temp():
    """/sys 에서 밀리도(m°C) 값을 읽어 °C로 변환. vcgencmd 없이도 동작한다."""
    try:
        with open("/sys/class/thermal/thermal_zone0/temp") as f:
            return round(int(f.read().strip()) / 1000, 1)
    except (OSError, ValueError):
        return None


def temp_loop():
    while True:
        t = read_cpu_temp()
        if t is not None:
            with temp_lock:
                temp_history.append({"t": time.time(), "temp": t})
        time.sleep(TEMP_INTERVAL)


# ── 라우트 ────────────────────────────────────────────────────────
@app.route("/")
def index():
    return render_template(
        "index.html",
        history_len=TEMP_HISTORY,
        poll_ms=int(TEMP_INTERVAL * 1000),
    )


@app.route("/video_feed")
def video_feed():
    """MJPEG 스트림: <img src="/video_feed"> 로 바로 표시 가능."""
    def gen():
        last_seq = -1
        while True:
            frame, seq = camera.get_frame()
            if frame is None or seq == last_seq:
                time.sleep(0.01)
                continue
            last_seq = seq
            yield (b"--frame\r\n"
                   b"Content-Type: image/jpeg\r\n\r\n" + frame + b"\r\n")

    return Response(gen(), mimetype="multipart/x-mixed-replace; boundary=frame")


@app.route("/api/temp")
def api_temp():
    with temp_lock:
        latest = temp_history[-1] if temp_history else None
    return jsonify(latest or {"t": time.time(), "temp": None})


@app.route("/api/temp/history")
def api_temp_history():
    with temp_lock:
        return jsonify(list(temp_history))


# ── 시작 ──────────────────────────────────────────────────────────
if __name__ == "__main__":
    camera = Camera()
    threading.Thread(target=temp_loop, daemon=True).start()
    # debug=True 는 리로더가 프로세스를 두 번 띄워 카메라를 두 번 열려고 하므로 끔
    app.run(host="0.0.0.0", port=5000, threaded=True, debug=False)