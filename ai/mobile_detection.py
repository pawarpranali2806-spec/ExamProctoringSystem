import numpy as np

try:
    from ultralytics import YOLO
    YOLO_AVAILABLE = True
except ImportError:
    YOLO_AVAILABLE = False


class MobileDetector:
    """Detects mobile phones / cell phones using YOLOv8 (COCO class 67: cell phone)."""

    def __init__(self, confidence_threshold=0.45, model_instance=None):
        self.confidence_threshold = confidence_threshold
        self.model = model_instance

        if self.model is None and YOLO_AVAILABLE:
            try:
                self.model = YOLO('yolov8n.pt')
            except Exception as e:
                print(f"[MobileDetector] Warning: YOLOv8 model loading failed: {e}")
                self.model = None

    def detect(self, image_bgr: np.ndarray) -> dict:
        """
        Detects cell phones in image.
        Returns:
            dict with:
                - phone_detected (bool)
                - boxes (list of [x1, y1, x2, y2])
                - max_confidence (float)
                - status ('NONE' or 'PHONE_DETECTED')
        """
        if image_bgr is None or image_bgr.size == 0 or self.model is None:
            return {
                'phone_detected': False,
                'boxes': [],
                'max_confidence': 0.0,
                'status': 'NONE'
            }

        try:
            # Class 67 in COCO is 'cell phone'
            results = self.model.predict(
                source=image_bgr,
                classes=[67],
                conf=self.confidence_threshold,
                verbose=False
            )

            boxes = []
            confidences = []

            for r in results:
                if r.boxes is not None:
                    for box in r.boxes:
                        coords = box.xyxy[0].cpu().numpy().tolist()
                        conf = float(box.conf[0].cpu().numpy())
                        boxes.append([int(c) for c in coords])
                        confidences.append(round(conf, 2))

            phone_detected = len(boxes) > 0
            max_conf = max(confidences) if confidences else 0.0

            return {
                'phone_detected': phone_detected,
                'boxes': boxes,
                'max_confidence': max_conf,
                'status': 'PHONE_DETECTED' if phone_detected else 'NONE'
            }
        except Exception:
            return {
                'phone_detected': False,
                'boxes': [],
                'max_confidence': 0.0,
                'status': 'NONE'
            }
