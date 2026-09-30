import numpy as np
from ai.face_detection import FaceDetector
from ai.eye_tracking import EyeTracker
from ai.head_pose import HeadPoseEstimator
from ai.audio_monitor import AudioMonitor


def test_face_detector_blank_frame():
    detector = FaceDetector()
    blank = np.zeros((240, 320, 3), dtype=np.uint8)
    res = detector.detect(blank)
    assert 'face_count' in res
    assert 'status' in res
    assert res['face_count'] == 0
    assert res['status'] == 'NO_FACE'


def test_eye_tracker_empty_landmarks():
    tracker = EyeTracker()
    res = tracker.compute_gaze([])
    assert res['gaze_direction'] == 'CENTER'
    assert res['is_looking_away'] is False


def test_head_pose_empty_landmarks():
    estimator = HeadPoseEstimator()
    res = estimator.estimate([], 640, 480)
    assert res['pose_label'] == 'FORWARD'
    assert res['is_abnormal'] is False


def test_audio_monitor():
    monitor = AudioMonitor(spike_threshold=60.0)
    # Normal volume
    r1 = monitor.process_volume(30.0)
    assert r1['status'] == 'NORMAL'
    assert r1['is_anomaly'] is False

    # Loud sustained noise
    for _ in range(5):
        r2 = monitor.process_volume(85.0)
    assert r2['status'] in ['NOISE_SPIKE', 'TALKING_DETECTED']
