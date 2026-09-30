import cv2
import numpy as np

try:
    import mediapipe as mp
    MP_AVAILABLE = True
except ImportError:
    MP_AVAILABLE = False


class FaceDetector:
    """Detects faces in video frames using MediaPipe with OpenCV Haar Cascade fallback."""

    def __init__(self, min_detection_confidence=0.5):
        self.min_detection_confidence = min_detection_confidence
        self.mp_face_detection = None
        self.detector = None
        self.cascade_detector = None

        if MP_AVAILABLE:
            try:
                self.mp_face_detection = mp.solutions.face_detection
                self.detector = self.mp_face_detection.FaceDetection(
                    model_selection=0,
                    min_detection_confidence=self.min_detection_confidence
                )
            except Exception as e:
                print(f"[FaceDetector] Warning: MediaPipe init failed: {e}. Falling back to OpenCV Cascade.")
                self.detector = None

        if self.detector is None:
            # Haar Cascade fallback
            cascade_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
            self.cascade_detector = cv2.CascadeClassifier(cascade_path)

    def detect(self, image_bgr: np.ndarray) -> dict:
        """
        Detects faces in a BGR image.
        Returns:
            dict with:
                - face_count (int)
                - status ('NO_FACE', 'SINGLE_FACE', 'MULTIPLE_FACES')
                - bounding_boxes (list of [x, y, w, h])
                - confidences (list of float)
        """
        if image_bgr is None or image_bgr.size == 0:
            return {
                'face_count': 0,
                'status': 'NO_FACE',
                'bounding_boxes': [],
                'confidences': []
            }

        h, w = image_bgr.shape[:2]
        boxes = []
        confidences = []

        if self.detector is not None:
            image_rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)
            results = self.detector.process(image_rgb)

            if results.detections:
                for detection in results.detections:
                    score = float(detection.score[0]) if detection.score else 0.8
                    bbox = detection.location_data.relative_bounding_box
                    x = max(0, int(bbox.xmin * w))
                    y = max(0, int(bbox.ymin * h))
                    box_w = min(w - x, int(bbox.width * w))
                    box_h = min(h - y, int(bbox.height * h))
                    boxes.append([x, y, box_w, box_h])
                    confidences.append(score)
        elif self.cascade_detector is not None:
            gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)
            detected = self.cascade_detector.detectMultiScale(
                gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30)
            )
            for (x, y, bw, bh) in detected:
                boxes.append([int(x), int(y), int(bw), int(bh)])
                confidences.append(0.85)

        count = len(boxes)
        if count == 0:
            status = 'NO_FACE'
        elif count == 1:
            status = 'SINGLE_FACE'
        else:
            status = 'MULTIPLE_FACES'

        return {
            'face_count': count,
            'status': status,
            'bounding_boxes': boxes,
            'confidences': confidences
        }

    def close(self):
        if self.detector is not None:
            try:
                self.detector.close()
            except Exception:
                pass
