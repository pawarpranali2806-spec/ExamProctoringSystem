import numpy as np

try:
    from ultralytics import YOLO
    YOLO_AVAILABLE = True
except ImportError:
    YOLO_AVAILABLE = False


class PersonDetector:
    """Detects persons in video frames using YOLOv8 (class 0)."""

    def __init__(self, confidence_threshold=0.50, model_instance=None):
        self.confidence_threshold = confidence_threshold
        self.model = model_instance

        if self.model is None and YOLO_AVAILABLE:
            try:
                # Load YOLOv8 nano model
                self.model = YOLO('yolov8n.pt')
            except Exception as e:
                print(f"[PersonDetector] Warning: YOLOv8 model loading failed: {e}")
                self.model = None

    def detect(self, image_bgr: np.ndarray) -> dict:
        """
        Detects persons in image.
        Returns:
            dict with:
                - person_count (int)
                - boxes (list of [x1, y1, x2, y2])
                - confidences (list of float)
                - status ('NO_PERSON', 'SINGLE_PERSON', 'MULTIPLE_PERSONS')
        """
        if image_bgr is None or image_bgr.size == 0 or self.model is None:
            # Fallback: assume 1 person if detector unavailable
            return {
                'person_count': 1,
                'boxes': [],
                'confidences': [],
                'status': 'SINGLE_PERSON'
            }

        try:
            # Run inference on class 0 (person)
            results = self.model.predict(
                source=image_bgr,
                classes=[0],
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

            count = len(boxes)
            if count == 0:
                status = 'NO_PERSON'
            elif count == 1:
                status = 'SINGLE_PERSON'
            else:
                status = 'MULTIPLE_PERSONS'

            return {
                'person_count': count,
                'boxes': boxes,
                'confidences': confidences,
                'status': status
            }
        except Exception as e:
            return {
                'person_count': 1,
                'boxes': [],
                'confidences': [],
                'status': 'SINGLE_PERSON'
            }
