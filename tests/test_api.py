import base64
import pytest
import numpy as np
import cv2
from app import create_app
from database import db
from database.models import User, Exam, Question, ExamAttempt, Answer


@pytest.fixture
def auth_client():
    app = create_app('testing')
    with app.test_client() as client:
        with app.app_context():
            db.create_all()

            # Create test admin & student
            admin = User(username='api_admin', email='api_admin@panopticon.ai', full_name='API Admin', role='admin')
            admin.set_password('Admin@123')

            student = User(username='api_student', email='api_student@panopticon.ai', full_name='API Student', role='student')
            student.set_password('Student@123')

            db.session.add_all([admin, student])
            db.session.commit()

            # Create test exam
            exam = Exam(title='API Test Exam', duration_minutes=15, passing_score=50, is_published=True, created_by=admin.id)
            db.session.add(exam)
            db.session.commit()

            q1 = Question(exam_id=exam.id, question_text="API Q1", option_a="A", option_b="B", option_c="C", option_d="D", correct_option="A", points=2)
            db.session.add(q1)
            db.session.commit()

            yield client, student, admin, exam, q1

            db.session.remove()
            db.drop_all()


def test_api_system_check_endpoint(auth_client):
    client, student, admin, exam, q1 = auth_client
    # Log in as student
    client.post('/login', data={'identifier': 'api_student@panopticon.ai', 'password': 'Student@123'})

    # Blank 100x100 JPEG base64
    blank = np.zeros((100, 100, 3), dtype=np.uint8)
    _, buf = cv2.imencode('.jpg', blank)
    b64_str = 'data:image/jpeg;base64,' + base64.b64encode(buf).decode('utf-8')

    res = client.post('/api/proctoring/system_check', json={'image': b64_str})
    assert res.status_code == 200
    data = res.get_json()
    assert data['camera_ok'] is True
    assert 'face_detected' in data


def test_api_answer_and_submit(auth_client):
    client, student, admin, exam, q1 = auth_client
    client.post('/login', data={'identifier': 'api_student@panopticon.ai', 'password': 'Student@123'})

    # Start attempt
    client.post(f'/exam/{exam.id}/start')
    attempt = ExamAttempt.query.filter_by(user_id=student.id, exam_id=exam.id).first()
    assert attempt is not None

    # Save answer via API
    ans_res = client.post(f'/api/exam/{attempt.id}/answer', json={
        'question_id': q1.id,
        'selected_option': 'A'
    })
    assert ans_res.status_code == 200
    assert ans_res.get_json()['success'] is True

    # Check status endpoint
    stat_res = client.get(f'/api/exam/{attempt.id}/status')
    assert stat_res.status_code == 200
    assert stat_res.get_json()['answered_count'] == 1

    # Submit attempt via API
    sub_res = client.post(f'/api/exam/{attempt.id}/submit')
    assert sub_res.status_code == 200
    sub_data = sub_res.get_json()
    assert sub_data['success'] is True

    # Validate database state
    updated_attempt = db.session.get(ExamAttempt, attempt.id)
    assert updated_attempt.status == 'completed'
    assert updated_attempt.score == 2.0
    assert updated_attempt.passed is True
