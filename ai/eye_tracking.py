import numpy as np


class EyeTracker:
    """Tracks eye gaze direction, eye closure (EAR), and suspicious looking away."""

    # Landmark indices for MediaPipe Face Mesh
    LEFT_EYE_OUTER = 33
    LEFT_EYE_INNER = 133
    LEFT_EYE_TOP = 159
    LEFT_EYE_BOTTOM = 145
    LEFT_IRIS = 468

    RIGHT_EYE_INNER = 362
    RIGHT_EYE_OUTER = 263
    RIGHT_EYE_TOP = 386
    RIGHT_EYE_BOTTOM = 374
    RIGHT_IRIS = 473

    def __init__(self, ear_threshold=0.18):
        self.ear_threshold = ear_threshold

    @staticmethod
    def _euclidean_dist(p1, p2):
        return np.linalg.norm(np.array(p1) - np.array(p2))

    def compute_ear(self, landmarks_2d):
        """Computes average Eye Aspect Ratio (EAR) across both eyes."""
        if len(landmarks_2d) < 400:
            return 0.3  # Neutral default

        try:
            # Left Eye
            top_left = landmarks_2d[self.LEFT_EYE_TOP]
            bottom_left = landmarks_2d[self.LEFT_EYE_BOTTOM]
            outer_left = landmarks_2d[self.LEFT_EYE_OUTER]
            inner_left = landmarks_2d[self.LEFT_EYE_INNER]

            left_ear = self._euclidean_dist(top_left, bottom_left) / (
                self._euclidean_dist(outer_left, inner_left) + 1e-6
            )

            # Right Eye
            top_right = landmarks_2d[self.RIGHT_EYE_TOP]
            bottom_right = landmarks_2d[self.RIGHT_EYE_BOTTOM]
            outer_right = landmarks_2d[self.RIGHT_EYE_OUTER]
            inner_right = landmarks_2d[self.RIGHT_EYE_INNER]

            right_ear = self._euclidean_dist(top_right, bottom_right) / (
                self._euclidean_dist(outer_right, inner_right) + 1e-6
            )

            return float((left_ear + right_ear) / 2.0)
        except (IndexError, TypeError):
            return 0.3

    def compute_gaze(self, landmarks_2d):
        """
        Determines gaze direction (CENTER, LEFT, RIGHT, UP, DOWN, EYES_CLOSED).
        Returns:
            dict with:
                - gaze_direction (str)
                - is_looking_away (bool)
                - ear (float)
                - horizontal_ratio (float)
        """
        if len(landmarks_2d) < 478:
            return {
                'gaze_direction': 'CENTER',
                'is_looking_away': False,
                'ear': 0.3,
                'horizontal_ratio': 0.5
            }

        ear = self.compute_ear(landmarks_2d)

        # If eyes are closed
        if ear < self.ear_threshold:
            return {
                'gaze_direction': 'EYES_CLOSED',
                'is_looking_away': False,
                'ear': round(ear, 3),
                'horizontal_ratio': 0.5
            }

        try:
            # Left Eye Iris relative position
            l_iris = np.array(landmarks_2d[self.LEFT_IRIS])
            l_outer = np.array(landmarks_2d[self.LEFT_EYE_OUTER])
            l_inner = np.array(landmarks_2d[self.LEFT_EYE_INNER])
            l_eye_width = self._euclidean_dist(l_outer, l_inner) + 1e-6
            l_ratio = self._euclidean_dist(l_iris, l_outer) / l_eye_width

            # Right Eye Iris relative position
            r_iris = np.array(landmarks_2d[self.RIGHT_IRIS])
            r_inner = np.array(landmarks_2d[self.RIGHT_EYE_INNER])
            r_outer = np.array(landmarks_2d[self.RIGHT_EYE_OUTER])
            r_eye_width = self._euclidean_dist(r_inner, r_outer) + 1e-6
            r_ratio = self._euclidean_dist(r_iris, r_inner) / r_eye_width

            avg_ratio = float((l_ratio + r_ratio) / 2.0)

            # Iris vertical position
            l_top = np.array(landmarks_2d[self.LEFT_EYE_TOP])
            l_bottom = np.array(landmarks_2d[self.LEFT_EYE_BOTTOM])
            v_ratio = (l_iris[1] - l_top[1]) / (l_bottom[1] - l_top[1] + 1e-6)

            gaze_direction = 'CENTER'
            is_looking_away = False

            # Gaze classification thresholds
            if avg_ratio < 0.38:
                gaze_direction = 'LOOKING_RIGHT'  # mirror perspective
                is_looking_away = True
            elif avg_ratio > 0.62:
                gaze_direction = 'LOOKING_LEFT'
                is_looking_away = True
            elif v_ratio < 0.20:
                gaze_direction = 'LOOKING_UP'
                is_looking_away = True
            elif v_ratio > 0.80:
                gaze_direction = 'LOOKING_DOWN'
                is_looking_away = True

            return {
                'gaze_direction': gaze_direction,
                'is_looking_away': is_looking_away,
                'ear': round(ear, 3),
                'horizontal_ratio': round(avg_ratio, 3)
            }
        except (IndexError, TypeError, ZeroDivisionError):
            return {
                'gaze_direction': 'CENTER',
                'is_looking_away': False,
                'ear': round(ear, 3),
                'horizontal_ratio': 0.5
            }
