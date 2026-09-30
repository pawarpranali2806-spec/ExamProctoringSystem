import cv2
import numpy as np
from ai.face_detection import FaceDetector
from ai.face_mesh import FaceMeshDetector
from ai.eye_tracking import EyeTracker
from ai.head_pose import HeadPoseEstimator
from ai.person_detection import PersonDetector
from ai.mobile_detection import MobileDetector
from ai.audio_monitor import AudioMonitor
from ai.cheating_score import CheatingRiskEngine


class ProctoringEngine:
    """Master Coordinator for all AI Proctoring sub-systems."""

    def __init__(self):
        print("[ProctoringEngine] Initializing AI models...")
        self.face_detector = FaceDetector()
        self.face_mesh_detector = FaceMeshDetector()
        self.eye_tracker = EyeTracker()
        self.head_pose_estimator = HeadPoseEstimator()
        
        # Share YOLO model instance between person and mobile detectors to conserve memory
        self.person_detector = PersonDetector()
        yolo_shared_model = getattr(self.person_detector, 'model', None)
        self.mobile_detector = MobileDetector(model_instance=yolo_shared_model)
        
        self.audio_monitor = AudioMonitor()
        
        # Store risk engine per attempt: {attempt_id: CheatingRiskEngine}
        self.risk_engines = {}
        print("[ProctoringEngine] Initialization complete.")

    def get_risk_engine(self, attempt_id: int) -> CheatingRiskEngine:
        """Retrieves or creates a risk engine instance for an exam attempt."""
        if attempt_id not in self.risk_engines:
            self.risk_engines[attempt_id] = CheatingRiskEngine()
        return self.risk_engines[attempt_id]

    def remove_attempt(self, attempt_id: int):
        """Cleans up memory for a completed attempt."""
        if attempt_id in self.risk_engines:
            del self.risk_engines[attempt_id]

    def process_frame(
        self,
        image_bgr: np.ndarray,
        attempt_id: int = None,
        volume_db: float = 0.0,
        browser_event: str = None,
        browser_event_details: str = None,
        annotate: bool = False
    ) -> dict:
        """
        Processes a video frame through all AI models and evaluates cheating risk.
        """
        if image_bgr is None or image_bgr.size == 0:
            return self._empty_result()

        h, w = image_bgr.shape[:2]

        # 1. Face Detection
        face_res = self.face_detector.detect(image_bgr)
        face_count = face_res['face_count']
        face_status = face_res['status']

        # 2. Face Mesh & Eye / Head analysis (if face is present)
        gaze_res = {'gaze_direction': 'UNKNOWN', 'is_looking_away': False, 'ear': 0.0}
        head_res = {'yaw': 0.0, 'pitch': 0.0, 'roll': 0.0, 'pose_label': 'UNKNOWN', 'is_abnormal': False}
        landmarks_2d = []

        if face_count > 0:
            mesh_res = self.face_mesh_detector.process(image_bgr)
            if mesh_res['detected']:
                landmarks_2d = mesh_res['landmarks_2d']
                gaze_res = self.eye_tracker.compute_gaze(landmarks_2d)
                head_res = self.head_pose_estimator.estimate(landmarks_2d, w, h)
            else:
                # Face detected by detector but mesh not resolved (e.g. extreme angle)
                gaze_res['gaze_direction'] = 'CENTER'
                head_res['pose_label'] = 'FORWARD'

        # 3. Person & Mobile Detection (YOLO)
        person_res = self.person_detector.detect(image_bgr)
        person_count = max(face_count, person_res['person_count'])

        mobile_res = self.mobile_detector.detect(image_bgr)
        phone_detected = mobile_res['phone_detected']
        phone_confidence = mobile_res['max_confidence']

        # 4. Audio Analysis
        audio_res = self.audio_monitor.process_volume(volume_db)

        # 5. Aggregate Detection Results
        detection_package = {
            'face_count': face_count,
            'is_looking_away': gaze_res['is_looking_away'],
            'gaze_direction': gaze_res['gaze_direction'],
            'head_abnormal': head_res['is_abnormal'],
            'head_pose_label': head_res['pose_label'],
            'phone_detected': phone_detected,
            'phone_confidence': phone_confidence,
            'person_count': person_count,
            'audio_anomaly': audio_res['is_anomaly'],
            'audio_confidence': audio_res['confidence'],
            'browser_event': browser_event,
            'browser_event_details': browser_event_details
        }

        # 6. Cheating Risk Engine Evaluation
        risk_engine = self.get_risk_engine(attempt_id) if attempt_id else CheatingRiskEngine()
        risk_eval = risk_engine.update(detection_package)

        # 7. Optional Frame Annotation
        annotated_bgr = None
        if annotate:
            annotated_bgr = self._annotate_frame(
                image_bgr.copy(),
                face_res,
                landmarks_2d,
                gaze_res,
                head_res,
                person_res,
                mobile_res,
                risk_eval
            )

        return {
            'face_count': face_count,
            'face_status': face_status,
            'gaze_direction': gaze_res['gaze_direction'],
            'is_looking_away': gaze_res['is_looking_away'],
            'head_pose': head_res['pose_label'],
            'head_angles': {
                'yaw': head_res['yaw'],
                'pitch': head_res['pitch'],
                'roll': head_res['roll']
            },
            'person_count': person_count,
            'phone_detected': phone_detected,
            'phone_confidence': phone_confidence,
            'audio_status': audio_res['status'],
            'audio_volume': audio_res['volume'],
            'current_risk': risk_eval['current_risk'],
            'max_risk': risk_eval['max_risk'],
            'risk_status': risk_eval['status'],
            'new_events': risk_eval['new_events'],
            'new_warning': risk_eval['new_warning'],
            'annotated_image': annotated_bgr
        }

    def _annotate_frame(
        self,
        img: np.ndarray,
        face_res: dict,
        landmarks: list,
        gaze: dict,
        head: dict,
        person: dict,
        mobile: dict,
        risk: dict
    ) -> np.ndarray:
        """Draws cyberpunk HUD overlays on the frame for live proctoring view."""
        h, w = img.shape[:2]

        # Draw Face Boxes
        for box in face_res.get('bounding_boxes', []):
            x, y, bw, bh = box
            cv2.rectangle(img, (x, y), (x + bw, y + bh), (254, 242, 0), 2)  # Cyan
            cv2.putText(img, "STUDENT VERIFIED", (x, max(20, y - 8)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (254, 242, 0), 1)

        # Draw Phone Boxes
        for box in mobile.get('boxes', []):
            x1, y1, x2, y2 = box
            cv2.rectangle(img, (x1, y1), (x2, y2), (0, 0, 255), 2)  # Red
            cv2.putText(img, f"PHONE DETECTED {int(mobile['max_confidence']*100)}%",
                        (x1, max(20, y1 - 8)), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)

        # Top HUD Status Banner
        cv2.rectangle(img, (0, 0), (w, 36), (15, 20, 30), -1)

        # Status text with color coding
        status = risk['status']
        if status == 'NORMAL':
            color = (0, 255, 0)
        elif status == 'LOW_RISK':
            color = (255, 200, 0)
        elif status == 'WARNING':
            color = (0, 165, 255)
        else:
            color = (0, 0, 255)

        hud_text = (
            f"PANOPTICON AI | Faces: {face_res['face_count']} | "
            f"Gaze: {gaze['gaze_direction']} | "
            f"Head: {head['pose_label']} | "
            f"Risk: {risk['current_risk']}% [{status}]"
        )
        cv2.putText(img, hud_text, (10, 24), cv2.FONT_HERSHEY_SIMPLEX, 0.45, color, 1)

        return img

    def _empty_result(self) -> dict:
        return {
            'face_count': 0,
            'face_status': 'NO_FACE',
            'gaze_direction': 'UNKNOWN',
            'is_looking_away': False,
            'head_pose': 'UNKNOWN',
            'head_angles': {'yaw': 0.0, 'pitch': 0.0, 'roll': 0.0},
            'person_count': 0,
            'phone_detected': False,
            'phone_confidence': 0.0,
            'audio_status': 'NORMAL',
            'audio_volume': 0.0,
            'current_risk': 0.0,
            'max_risk': 0.0,
            'risk_status': 'NORMAL',
            'new_events': [],
            'new_warning': None,
            'annotated_image': None
        }
