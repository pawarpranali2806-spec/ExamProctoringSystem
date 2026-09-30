import requests
import base64
import numpy as np
import cv2

BASE_URL = "http://127.0.0.1:5000"

def run_live_verification():
    print("==================================================")
    print("PROJECT PANOPTICON - FULL SYSTEM VERIFICATION")
    print("==================================================")

    session = requests.Session()

    # 1. Test Landing Page
    print("\n[1/7] Testing Landing Page...")
    r = session.get(f"{BASE_URL}/")
    assert r.status_code == 200, f"Expected 200, got {r.status_code}"
    assert "PANOPTICON" in r.text
    print("   [PASS] Landing Page rendered successfully.")

    # 2. Test Student Authentication
    print("\n[2/7] Testing Student Authentication...")
    login_data = {
        'identifier': 'student@panopticon.ai',
        'password': 'Student@12345'
    }
    r = session.post(f"{BASE_URL}/login", data=login_data, allow_redirects=True)
    assert r.status_code == 200, f"Expected 200, got {r.status_code}"
    assert "Candidate Portal" in r.text or "Alex Mercer" in r.text
    print("   [PASS] Student authentication successful.")

    # 3. Test Student Dashboard & Available Exams
    print("\n[3/7] Testing Student Dashboard & Exams...")
    r = session.get(f"{BASE_URL}/dashboard")
    assert r.status_code == 200
    assert "Advanced Cybersecurity" in r.text
    print("   [PASS] Student dashboard displays available exams.")

    # 4. Test System Check & Face Verification Pages
    print("\n[4/7] Testing System Check & Face Verification...")
    r = session.get(f"{BASE_URL}/exam/1/check")
    assert r.status_code == 200
    assert "System Readiness Diagnostics" in r.text

    r = session.get(f"{BASE_URL}/exam/1/verify")
    assert r.status_code == 200
    assert "Biometric Pre-Flight Verification" in r.text
    print("   [PASS] System check & face verification pages load properly.")

    # 5. Test Live AI Frame Analysis API
    print("\n[5/7] Testing Real-Time AI Proctoring API (/api/proctoring/analyze_frame)...")
    # Generate synthetic 480x360 image
    blank = np.zeros((360, 480, 3), dtype=np.uint8)
    _, buf = cv2.imencode('.jpg', blank)
    b64_str = "data:image/jpeg;base64," + base64.b64encode(buf).decode('utf-8')

    payload = {
        'image': b64_str,
        'attempt_id': 2,
        'volume_db': 25.0,
        'browser_event': None
    }
    r = session.post(f"{BASE_URL}/api/proctoring/analyze_frame", json=payload)
    assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
    data = r.json()
    assert 'current_risk' in data
    assert 'risk_status' in data
    assert 'face_status' in data
    print(f"   [PASS] AI Proctoring Inference: Face={data['face_status']}, Gaze={data['gaze_direction']}, Threat Index={data['current_risk']}%, Status={data['risk_status']}")

    # 6. Test Admin Login & Control Center
    print("\n[6/7] Testing Administrator Control Center...")
    admin_session = requests.Session()
    r = admin_session.post(f"{BASE_URL}/login", data={
        'identifier': 'admin@panopticon.ai',
        'password': 'Admin@12345'
    }, allow_redirects=True)
    assert r.status_code == 200
    assert "Administrator Control Center" in r.text or "Dr. Evelyn Vance" in r.text
    print("   [PASS] Admin authenticated and control center loaded.")

    # Test Admin Stats API
    r = admin_session.get(f"{BASE_URL}/api/admin/stats")
    assert r.status_code == 200
    stats = r.json()
    assert 'risk_distribution' in stats
    assert 'infraction_counts' in stats
    print(f"   [PASS] Admin Real-Time Stats API: {stats['risk_distribution']}")

    # 7. Test Audit Report Generation
    print("\n[7/7] Testing Candidate Proctoring Audit Report...")
    r = admin_session.get(f"{BASE_URL}/admin/attempt/2/report")
    assert r.status_code == 200
    assert "Candidate Proctoring Audit Dossier" in r.text
    assert "Alex Mercer" in r.text
    assert "PHONE_DETECTED" in r.text
    print("   [PASS] Proctoring Audit Dossier rendered with full timeline and telemetry.")

    print("\n==================================================")
    print("ALL LIVE VERIFICATION CHECKS PASSED PERFECTLY!")
    print("==================================================")

if __name__ == '__main__':
    run_live_verification()
