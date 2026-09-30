import cv2
import numpy as np

try:
    import mediapipe as mp
    MP_AVAILABLE = True
except ImportError:
    MP_AVAILABLE = False


class FaceMeshDetector:
    """Extracts 468/478 facial landmarks using MediaPipe Face Mesh."""

    def __init__(self, max_num_faces=1, min_detection_confidence=0.5, min_tracking_confidence=0.5):
        self.mp_face_mesh = None
        self.face_mesh = None

        if MP_AVAILABLE:
            try:
                self.mp_face_mesh = mp.solutions.face_mesh
                self.face_mesh = self.mp_face_mesh.FaceMesh(
                    max_num_faces=max_num_faces,
                    refine_landmarks=True,
                    min_detection_confidence=min_detection_confidence,
                    min_tracking_confidence=min_tracking_confidence
                )
            except Exception as e:
                print(f"[FaceMeshDetector] Warning: MediaPipe FaceMesh init failed: {e}")
                self.face_mesh = None

    def process(self, image_bgr: np.ndarray) -> dict:
        """
        Extracts facial landmarks from a BGR image.
        Returns:
            dict with:
                - detected (bool)
                - landmarks_2d (list of (x, y)) in pixel coordinates
                - landmarks_3d (list of (x, y, z)) normalized coordinates
                - raw_landmarks (list of landmarks)
        """
        if self.face_mesh is None or image_bgr is None or image_bgr.size == 0:
            return {
                'detected': False,
                'landmarks_2d': [],
                'landmarks_3d': []
            }

        h, w = image_bgr.shape[:2]
        image_rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)
        results = self.face_mesh.process(image_rgb)

        if not results.multi_face_landmarks:
            return {
                'detected': False,
                'landmarks_2d': [],
                'landmarks_3d': []
            }

        face_landmarks = results.multi_face_landmarks[0]
        landmarks_2d = []
        landmarks_3d = []

        for lm in face_landmarks.landmark:
            px = int(lm.x * w)
            py = int(lm.y * h)
            landmarks_2d.append((px, py))
            landmarks_3d.append((lm.x, lm.y, lm.z))

        return {
            'detected': True,
            'landmarks_2d': landmarks_2d,
            'landmarks_3d': landmarks_3d
        }

    def close(self):
        if self.face_mesh is not None:
            try:
                self.face_mesh.close()
            except Exception:
                pass
