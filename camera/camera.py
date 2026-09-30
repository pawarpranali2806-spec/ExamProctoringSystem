import cv2
import time
import math
import threading
import numpy as np


class VideoCamera:
    """
    Thread-safe camera manager supporting physical webcam capture
    with seamless simulated fallback frames when hardware camera is not available.
    """

    def __init__(self, camera_index=0, width=640, height=480):
        self.camera_index = camera_index
        self.width = width
        self.height = height
        self.lock = threading.Lock()
        self.simulated = False
        self.cap = None
        self.frame_count = 0
        self.start_time = time.time()

        self._init_camera()

    def _init_camera(self):
        try:
            self.cap = cv2.VideoCapture(self.camera_index)
            if self.cap is None or not self.cap.isOpened():
                print(f"[VideoCamera] Hardware camera {self.camera_index} not accessible. Using simulated camera.")
                self.simulated = True
                self.cap = None
            else:
                # Try reading one test frame
                ret, test_frame = self.cap.read()
                if not ret or test_frame is None:
                    print("[VideoCamera] Failed to read frame from hardware webcam. Falling back to simulated.")
                    self.simulated = True
                    self.cap.release()
                    self.cap = None
                else:
                    self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
                    self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
                    print(f"[VideoCamera] Physical camera initialized at index {self.camera_index}.")
        except Exception as e:
            print(f"[VideoCamera] Error initializing camera: {e}. Using simulated.")
            self.simulated = True
            self.cap = None

    def get_frame_raw(self) -> np.ndarray:
        """Returns BGR numpy array frame."""
        with self.lock:
            if not self.simulated and self.cap is not None and self.cap.isOpened():
                ret, frame = self.cap.read()
                if ret and frame is not None:
                    return frame

            # Generate synthetic frame if hardware camera is inactive/simulated
            return self._generate_simulated_frame()

    def get_frame_jpeg(self) -> bytes:
        """Returns encoded JPEG bytes for HTTP video streaming."""
        frame = self.get_frame_raw()
        ret, jpeg = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
        if ret:
            return jpeg.tobytes()
        # Fallback 1x1 black pixel
        return b''

    def _generate_simulated_frame(self) -> np.ndarray:
        """
        Creates a synthetic 640x480 video frame depicting an exam candidate face silhouette
        with dynamic eye movement and a live timestamp ticker.
        """
        self.frame_count += 1
        t = time.time() - self.start_time
        frame = np.zeros((self.height, self.width, 3), dtype=np.uint8)

        # Background gradient (dark navy #080d1a)
        frame[:, :] = (26, 13, 8)

        # Draw subtle grid lines
        for y in range(0, self.height, 40):
            cv2.line(frame, (0, y), (self.width, y), (40, 25, 18), 1)
        for x in range(0, self.width, 40):
            cv2.line(frame, (x, 0), (x, self.height), (40, 25, 18), 1)

        # Center coordinates
        cx = self.width // 2
        cy = self.height // 2 + 10

        # Draw Head / Face oval
        head_color = (180, 160, 140)
        cv2.ellipse(frame, (cx, cy), (105, 140), 0, 0, 360, head_color, -1)
        cv2.ellipse(frame, (cx, cy), (105, 140), 0, 0, 360, (254, 242, 0), 2)  # Cyan outline

        # Moving eyes: gaze moves left/center/right periodically
        eye_offset_x = int(math.sin(t * 1.2) * 5)
        # Left Eye
        cv2.circle(frame, (cx - 42, cy - 30), 16, (255, 255, 255), -1)
        cv2.circle(frame, (cx - 42 + eye_offset_x, cy - 30), 8, (60, 40, 20), -1)
        cv2.circle(frame, (cx - 42 + eye_offset_x, cy - 30), 4, (0, 0, 0), -1)

        # Right Eye
        cv2.circle(frame, (cx + 42, cy - 30), 16, (255, 255, 255), -1)
        cv2.circle(frame, (cx + 42 + eye_offset_x, cy - 30), 8, (60, 40, 20), -1)
        cv2.circle(frame, (cx + 42 + eye_offset_x, cy - 30), 4, (0, 0, 0), -1)

        # Nose
        cv2.line(frame, (cx, cy - 10), (cx - 5, cy + 15), (140, 120, 100), 2)
        cv2.line(frame, (cx - 5, cy + 15), (cx + 5, cy + 15), (140, 120, 100), 2)

        # Mouth
        cv2.ellipse(frame, (cx, cy + 55), (28, 8), 0, 0, 180, (110, 80, 90), 2)

        # Watermark & Status Text
        cv2.putText(
            frame,
            "PANOPTICON PROCTORING FEED [SIMULATED STREAM]",
            (16, 28),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            (0, 242, 254),
            1
        )
        timestamp_str = time.strftime('%Y-%m-%d %H:%M:%S')
        cv2.putText(
            frame,
            f"TIME: {timestamp_str} | FPS: ~30",
            (16, self.height - 18),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.45,
            (180, 180, 180),
            1
        )

        return frame

    def release(self):
        with self.lock:
            if self.cap is not None and self.cap.isOpened():
                self.cap.release()
                self.cap = None


def gen_frames(camera: VideoCamera):
    """Generator function yielding multipart JPEG stream chunks."""
    while True:
        frame_bytes = camera.get_frame_jpeg()
        if not frame_bytes:
            time.sleep(0.05)
            continue
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
        time.sleep(0.033)  # ~30 FPS
