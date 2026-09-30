import time
from collections import deque


class CheatingRiskEngine:
    """
    Centralized Multi-Factor Proctoring Risk Engine.
    Uses confidence-weighted scoring, rolling time windows, persistence filtering,
    and adaptive risk decay.
    """

    # Risk score brackets
    STATUS_NORMAL = 'NORMAL'          # 0 - 20
    STATUS_LOW_RISK = 'LOW_RISK'      # 21 - 40
    STATUS_WARNING = 'WARNING'        # 41 - 65
    STATUS_HIGH_RISK = 'HIGH_RISK'    # 66 - 85
    STATUS_CRITICAL = 'CRITICAL'      # 86 - 100

    def __init__(self, decay_rate=0.94, warning_cooldown=8.0):
        self.decay_rate = decay_rate
        self.warning_cooldown = warning_cooldown

        self.current_risk = 0.0
        self.max_risk = 0.0

        # Persistence counters (consecutive frames)
        self.consecutive_face_missing = 0
        self.consecutive_multiple_faces = 0
        self.consecutive_looking_away = 0
        self.consecutive_phone_detected = 0
        self.consecutive_head_abnormal = 0

        # Timestamps of last warnings issued by type
        self.last_warning_times = {}

        # History buffer: (timestamp, event_type, risk_delta, confidence)
        self.history = deque(maxlen=60)

    def update(self, detection_results: dict) -> dict:
        """
        Evaluates current frame detections and computes new risk metrics.

        Args:
            detection_results: dict with:
                - face_count (int)
                - is_looking_away (bool)
                - gaze_direction (str)
                - head_abnormal (bool)
                - phone_detected (bool)
                - phone_confidence (float)
                - person_count (int)
                - audio_anomaly (bool)
                - audio_confidence (float)
                - browser_event (str or None)

        Returns:
            dict with:
                - current_risk (float)
                - max_risk (float)
                - status (str: NORMAL, LOW_RISK, WARNING, HIGH_RISK, CRITICAL)
                - new_events (list of dicts to log)
                - new_warning (dict or None to show to user)
        """
        now = time.time()
        new_events = []
        new_warning = None
        frame_risk_addition = 0.0

        # 1. Face Missing Analysis
        face_count = detection_results.get('face_count', 1)
        if face_count == 0:
            self.consecutive_face_missing += 1
            if self.consecutive_face_missing >= 3:  # Sustained missing face
                conf = min(1.0, 0.6 + self.consecutive_face_missing * 0.1)
                delta = 14.0
                frame_risk_addition += delta
                event = {
                    'event_type': 'FACE_MISSING',
                    'severity': 'HIGH' if self.consecutive_face_missing >= 5 else 'MEDIUM',
                    'confidence': conf,
                    'risk_increment': delta,
                    'details': f"No face detected in video stream for {self.consecutive_face_missing} consecutive cycles."
                }
                new_events.append(event)
                new_warning = self._check_generate_warning(
                    'FACE_MISSING', conf, "Face not detected. Please remain centered in front of the camera.", now
                )
        else:
            self.consecutive_face_missing = 0

        # 2. Multiple Persons / Multiple Faces Analysis
        person_count = detection_results.get('person_count', face_count)
        if face_count > 1 or person_count > 1:
            self.consecutive_multiple_faces += 1
            if self.consecutive_multiple_faces >= 2:
                conf = 0.90
                delta = 22.0
                frame_risk_addition += delta
                event = {
                    'event_type': 'MULTIPLE_FACES',
                    'severity': 'CRITICAL',
                    'confidence': conf,
                    'risk_increment': delta,
                    'details': f"Multiple individuals detected (faces={face_count}, persons={person_count})."
                }
                new_events.append(event)
                new_warning = self._check_generate_warning(
                    'MULTIPLE_FACES', conf, "Multiple people detected in view! Examination must be taken alone.", now
                )
        else:
            self.consecutive_multiple_faces = 0

        # 3. Mobile Phone Detection
        phone_detected = detection_results.get('phone_detected', False)
        phone_conf = detection_results.get('phone_confidence', 0.0)
        if phone_detected and phone_conf >= 0.40:
            self.consecutive_phone_detected += 1
            if self.consecutive_phone_detected >= 1:
                delta = 25.0 * phone_conf
                frame_risk_addition += delta
                event = {
                    'event_type': 'PHONE_DETECTED',
                    'severity': 'CRITICAL',
                    'confidence': phone_conf,
                    'risk_increment': delta,
                    'details': f"Mobile device detected in frame with {round(phone_conf * 100, 1)}% confidence."
                }
                new_events.append(event)
                new_warning = self._check_generate_warning(
                    'PHONE_DETECTED', phone_conf, "Unauthorized mobile device detected in frame! Remove immediately.", now
                )
        else:
            self.consecutive_phone_detected = 0

        # 4. Gaze Direction & Looking Away
        is_looking_away = detection_results.get('is_looking_away', False)
        gaze_dir = detection_results.get('gaze_direction', 'CENTER')
        if is_looking_away and face_count > 0:
            self.consecutive_looking_away += 1
            if self.consecutive_looking_away >= 3:  # Persistence filter: brief glance ignored
                conf = min(0.95, 0.55 + self.consecutive_looking_away * 0.08)
                delta = 8.0
                frame_risk_addition += delta
                event = {
                    'event_type': 'LOOKING_AWAY',
                    'severity': 'MEDIUM',
                    'confidence': conf,
                    'risk_increment': delta,
                    'details': f"Eyes directed away from screen ({gaze_dir}) for {self.consecutive_looking_away} cycles."
                }
                new_events.append(event)
                new_warning = self._check_generate_warning(
                    'LOOKING_AWAY', conf, f"Suspicious eye gaze detected ({gaze_dir}). Please keep eyes on screen.", now
                )
        else:
            self.consecutive_looking_away = 0

        # 5. Head Pose Abnormal
        head_abnormal = detection_results.get('head_abnormal', False)
        head_pose_label = detection_results.get('head_pose_label', 'FORWARD')
        if head_abnormal and face_count > 0:
            self.consecutive_head_abnormal += 1
            if self.consecutive_head_abnormal >= 3:
                conf = 0.75
                delta = 7.0
                frame_risk_addition += delta
                event = {
                    'event_type': 'HEAD_POSE_ABNORMAL',
                    'severity': 'LOW' if self.consecutive_head_abnormal < 5 else 'MEDIUM',
                    'confidence': conf,
                    'risk_increment': delta,
                    'details': f"Abnormal head orientation: {head_pose_label}."
                }
                new_events.append(event)
                new_warning = self._check_generate_warning(
                    'HEAD_POSE_ABNORMAL', conf, f"Head turned away ({head_pose_label}). Face the screen directly.", now
                )
        else:
            self.consecutive_head_abnormal = 0

        # 6. Audio Anomaly
        audio_anomaly = detection_results.get('audio_anomaly', False)
        audio_conf = detection_results.get('audio_confidence', 0.0)
        if audio_anomaly:
            delta = 10.0 * audio_conf
            frame_risk_addition += delta
            event = {
                'event_type': 'AUDIO_ANOMALY',
                'severity': 'MEDIUM',
                'confidence': audio_conf,
                'risk_increment': delta,
                'details': f"Unusual background sound/speech activity detected."
            }
            new_events.append(event)
            new_warning = self._check_generate_warning(
                'AUDIO_ANOMALY', audio_conf, "Abnormal audio/voice detected. Maintain strict silence.", now
            )

        # 7. Browser Security Event (if passed)
        browser_event = detection_results.get('browser_event')
        if browser_event:
            b_delta = 15.0
            if browser_event in ['TAB_SWITCH', 'WINDOW_BLUR']:
                b_delta = 18.0
            elif browser_event in ['FULLSCREEN_EXIT']:
                b_delta = 16.0
            elif browser_event in ['COPY_ACTION', 'PASTE_ACTION']:
                b_delta = 12.0

            frame_risk_addition += b_delta
            event = {
                'event_type': browser_event,
                'severity': 'HIGH',
                'confidence': 1.0,
                'risk_increment': b_delta,
                'details': detection_results.get('browser_event_details', f"Browser security infraction: {browser_event}")
            }
            new_events.append(event)
            new_warning = self._check_generate_warning(
                browser_event, 1.0, f"Browser violation recorded ({browser_event}). Leaving exam view is prohibited.", now
            )

        # Apply Risk Dynamics
        if frame_risk_addition > 0:
            # Add risk with ceiling at 100
            self.current_risk = min(100.0, self.current_risk + frame_risk_addition)
        else:
            # Smooth exponential decay towards 0 when student acts normally
            self.current_risk = max(0.0, self.current_risk * self.decay_rate)

        # Track historical peak
        if self.current_risk > self.max_risk:
            self.max_risk = self.current_risk

        # Determine status
        status = self.classify_risk(self.current_risk)

        # Append to sliding history
        self.history.append((now, status, frame_risk_addition))

        return {
            'current_risk': round(self.current_risk, 1),
            'max_risk': round(self.max_risk, 1),
            'status': status,
            'new_events': new_events,
            'new_warning': new_warning
        }

    def _check_generate_warning(self, event_type: str, confidence: float, description: str, now: float):
        """Ensures warning is not spammed by respecting a cooldown window."""
        last_time = self.last_warning_times.get(event_type, 0.0)
        if now - last_time >= self.warning_cooldown:
            self.last_warning_times[event_type] = now
            return {
                'event_type': event_type,
                'confidence': round(confidence, 2),
                'risk_score': round(self.current_risk, 1),
                'description': description
            }
        return None

    @classmethod
    def classify_risk(cls, score: float) -> str:
        if score <= 20:
            return cls.STATUS_NORMAL
        elif score <= 40:
            return cls.STATUS_LOW_RISK
        elif score <= 65:
            return cls.STATUS_WARNING
        elif score <= 85:
            return cls.STATUS_HIGH_RISK
        else:
            return cls.STATUS_CRITICAL

    def reset(self):
        self.current_risk = 0.0
        self.max_risk = 0.0
        self.consecutive_face_missing = 0
        self.consecutive_multiple_faces = 0
        self.consecutive_looking_away = 0
        self.consecutive_phone_detected = 0
        self.consecutive_head_abnormal = 0
        self.last_warning_times.clear()
        self.history.clear()
