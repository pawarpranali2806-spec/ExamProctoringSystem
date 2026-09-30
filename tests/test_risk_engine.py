import pytest
from ai.cheating_score import CheatingRiskEngine


def test_risk_engine_initial_state():
    engine = CheatingRiskEngine()
    assert engine.current_risk == 0.0
    assert engine.max_risk == 0.0
    assert engine.classify_risk(0.0) == CheatingRiskEngine.STATUS_NORMAL


def test_risk_brackets():
    engine = CheatingRiskEngine()
    assert engine.classify_risk(10) == 'NORMAL'
    assert engine.classify_risk(30) == 'LOW_RISK'
    assert engine.classify_risk(50) == 'WARNING'
    assert engine.classify_risk(75) == 'HIGH_RISK'
    assert engine.classify_risk(95) == 'CRITICAL'


def test_face_missing_persistence():
    engine = CheatingRiskEngine()
    
    # 1st cycle missing face: no warning yet (persistence threshold = 3)
    res1 = engine.update({'face_count': 0})
    assert res1['new_warning'] is None

    # 2nd cycle missing face
    res2 = engine.update({'face_count': 0})
    assert res2['new_warning'] is None

    # 3rd cycle missing face: should trigger risk increment and warning
    res3 = engine.update({'face_count': 0})
    assert res3['current_risk'] > 0
    assert res3['new_warning'] is not None
    assert res3['new_warning']['event_type'] == 'FACE_MISSING'


def test_phone_detection_risk():
    engine = CheatingRiskEngine()
    res = engine.update({
        'face_count': 1,
        'phone_detected': True,
        'phone_confidence': 0.85
    })
    assert res['current_risk'] > 15.0
    assert res['new_warning'] is not None
    assert res['new_warning']['event_type'] == 'PHONE_DETECTED'


def test_multiple_faces_risk():
    engine = CheatingRiskEngine()
    # 1st cycle multiple faces
    engine.update({'face_count': 2})
    # 2nd cycle multiple faces (persistence >= 2)
    res = engine.update({'face_count': 2})
    assert res['current_risk'] > 15.0
    assert res['new_warning'] is not None
    assert res['new_warning']['event_type'] == 'MULTIPLE_FACES'


def test_risk_decay():
    engine = CheatingRiskEngine(decay_rate=0.8)
    # Spike risk with phone
    engine.update({'face_count': 1, 'phone_detected': True, 'phone_confidence': 0.8})
    high_risk = engine.current_risk
    assert high_risk > 0

    # Normal frame: risk should decay
    decayed_res = engine.update({'face_count': 1, 'phone_detected': False})
    assert decayed_res['current_risk'] < high_risk
