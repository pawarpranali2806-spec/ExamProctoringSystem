import pytest
from datetime import datetime, timezone
from app import create_app
from database import db
from database.models import User, Exam, Question, ExamAttempt, Answer, Result


@pytest.fixture
def app_ctx():
    app = create_app('testing')
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


def test_exam_creation_and_questions(app_ctx):
    admin = User(username='admin_exam', email='admin_exam@panopticon.ai', full_name='Admin Exam', role='admin')
    admin.set_password('Admin@123')
    db.session.add(admin)
    db.session.commit()

    exam = Exam(
        title="Test Examination 101",
        description="Testing suite examination",
        duration_minutes=30,
        passing_score=75,
        is_published=True,
        created_by=admin.id
    )
    db.session.add(exam)
    db.session.commit()

    q1 = Question(
        exam_id=exam.id,
        question_text="What is 2+2?",
        option_a="3",
        option_b="4",
        option_c="5",
        option_d="6",
        correct_option="B",
        points=2
    )
    q2 = Question(
        exam_id=exam.id,
        question_text="What is the capital of France?",
        option_a="Rome",
        option_b="Berlin",
        option_c="Paris",
        option_d="Madrid",
        correct_option="C",
        points=3
    )
    db.session.add_all([q1, q2])
    db.session.commit()

    assert exam.total_questions == 2
    assert exam.total_points == 5


def test_attempt_and_grading(app_ctx):
    admin = User(username='admin_grade', email='admin_grade@panopticon.ai', full_name='Admin Grade', role='admin')
    admin.set_password('Admin@123')
    student = User(username='student_grade', email='student_grade@panopticon.ai', full_name='Student Grade', role='student')
    student.set_password('Student@123')
    db.session.add_all([admin, student])
    db.session.commit()

    exam = Exam(
        title="Grading Test Exam",
        duration_minutes=10,
        passing_score=60,
        is_published=True,
        created_by=admin.id
    )
    db.session.add(exam)
    db.session.commit()

    q1 = Question(exam_id=exam.id, question_text="Q1", option_a="A", option_b="B", option_c="C", option_d="D", correct_option="A", points=5)
    q2 = Question(exam_id=exam.id, question_text="Q2", option_a="A", option_b="B", option_c="C", option_d="D", correct_option="B", points=5)
    db.session.add_all([q1, q2])
    db.session.commit()

    # Start attempt
    attempt = ExamAttempt(
        user_id=student.id,
        exam_id=exam.id,
        status='in_progress',
        max_score=10.0
    )
    db.session.add(attempt)
    db.session.commit()

    # Answer Q1 correctly, Q2 incorrectly
    ans1 = Answer(attempt_id=attempt.id, question_id=q1.id, selected_option='A')
    ans2 = Answer(attempt_id=attempt.id, question_id=q2.id, selected_option='C')
    db.session.add_all([ans1, ans2])
    db.session.commit()

    # Grade attempt
    total_score = 0.0
    for ans in attempt.answers.all():
        if ans.selected_option == ans.question.correct_option:
            ans.is_correct = True
            total_score += ans.question.points
        else:
            ans.is_correct = False

    attempt.score = total_score
    attempt.percentage = (total_score / attempt.max_score) * 100.0
    attempt.passed = attempt.percentage >= exam.passing_score
    attempt.status = 'completed'
    attempt.completed_at = datetime.now(timezone.utc)
    db.session.commit()

    assert attempt.score == 5.0
    assert attempt.percentage == 50.0
    assert attempt.passed is False  # 50% < 60%
