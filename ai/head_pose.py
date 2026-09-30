import cv2
import numpy as np


class HeadPoseEstimator:
    """Estimates 3D Head Pose (Pitch, Yaw, Roll) using Perspective-n-Point (PnP)."""

    # 3D generic facial model coordinates
    MODEL_POINTS = np.array([
        (0.0, 0.0, 0.0),           # Nose tip
        (0.0, -330.0, -65.0),      # Chin
        (-225.0, 170.0, -135.0),   # Left eye left corner
        (225.0, 170.0, -135.0),    # Right eye right corner
        (-150.0, -150.0, -125.0),  # Left mouth corner
        (150.0, -150.0, -125.0)    # Right mouth corner
    ], dtype=np.float64)

    # Corresponding MediaPipe landmark indices
    LANDMARK_INDICES = [1, 152, 33, 263, 61, 291]

    def __init__(self, yaw_threshold=28.0, pitch_threshold=22.0, roll_threshold=25.0):
        self.yaw_threshold = yaw_threshold
        self.pitch_threshold = pitch_threshold
        self.roll_threshold = roll_threshold

    def estimate(self, landmarks_2d, img_w, img_h) -> dict:
        """
        Estimates head pose angles in degrees.
        Returns:
            dict with:
                - yaw (float, deg): left negative / right positive
                - pitch (float, deg): up negative / down positive
                - roll (float, deg): tilt
                - pose_label (str): 'FORWARD', 'TURNED_LEFT', 'TURNED_RIGHT', 'LOOKING_DOWN', 'LOOKING_UP', etc.
                - is_abnormal (bool)
        """
        if len(landmarks_2d) < 300:
            return {
                'yaw': 0.0,
                'pitch': 0.0,
                'roll': 0.0,
                'pose_label': 'FORWARD',
                'is_abnormal': False
            }

        try:
            image_points = np.array([
                landmarks_2d[idx] for idx in self.LANDMARK_INDICES
            ], dtype=np.float64)

            # Camera matrix estimation
            focal_length = img_w
            center = (img_w / 2.0, img_h / 2.0)
            camera_matrix = np.array([
                [focal_length, 0, center[0]],
                [0, focal_length, center[1]],
                [0, 0, 1]
            ], dtype=np.float64)
            dist_coeffs = np.zeros((4, 1))

            success, rvec, tvec = cv2.solvePnP(
                self.MODEL_POINTS,
                image_points,
                camera_matrix,
                dist_coeffs,
                flags=cv2.SOLVEPNP_ITERATIVE
            )

            if not success:
                return {
                    'yaw': 0.0,
                    'pitch': 0.0,
                    'roll': 0.0,
                    'pose_label': 'FORWARD',
                    'is_abnormal': False
                }

            # Convert rotation vector to rotation matrix
            rmat, _ = cv2.Rodrigues(rvec)

            # Decompose rotation matrix into Euler angles
            angles, _, _, _, _, _ = cv2.RQDecomp3x3(rmat)
            pitch = float(angles[0] * 360)
            yaw = float(angles[1] * 360)
            roll = float(angles[2] * 360)

            # Classify pose
            pose_label = 'FORWARD'
            is_abnormal = False

            if yaw > self.yaw_threshold:
                pose_label = 'TURNED_RIGHT'
                is_abnormal = True
            elif yaw < -self.yaw_threshold:
                pose_label = 'TURNED_LEFT'
                is_abnormal = True
            elif pitch > self.pitch_threshold:
                pose_label = 'LOOKING_DOWN'
                is_abnormal = True
            elif pitch < -self.pitch_threshold:
                pose_label = 'LOOKING_UP'
                is_abnormal = True
            elif abs(roll) > self.roll_threshold:
                pose_label = 'HEAD_TILTED'
                is_abnormal = True

            return {
                'yaw': round(yaw, 1),
                'pitch': round(pitch, 1),
                'roll': round(roll, 1),
                'pose_label': pose_label,
                'is_abnormal': is_abnormal
            }
        except Exception:
            return {
                'yaw': 0.0,
                'pitch': 0.0,
                'roll': 0.0,
                'pose_label': 'FORWARD',
                'is_abnormal': False
            }
