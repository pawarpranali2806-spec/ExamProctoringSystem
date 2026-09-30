from datetime import datetime, timezone
from flask import Blueprint, render_template, redirect, url_for, flash, request, abort
from flask_login import login_required, current_user
from database import db
from database.models import Exam, Question, ExamAttempt, Answer, Result, Warning, ProctoringEvent, utc_now

student_bp = Blueprint('student', __name__)


@student_bp.route('/dashboard')
@login_required
def dashboard():
    """Student dashboard showing available exams, ongoing attempts, and results."""
    # Available published exams
    available_exams = Exam.query.filter_by(is_published=True).order_by(Exam.created_at.desc()).all()

    # User's active / in_progress attempts
    active_attempts = ExamAttempt.query.filter_by(
        user_id=current_user.id,
        status='in_progress'
    ).order_by(ExamAttempt.started_at.desc()).all()

    # User's completed results
    completed_results = Result.query.filter_by(
        user_id=current_user.id
    ).order_by(Result.created_at.desc()).all()

    # Recent warnings across student's attempts
    attempt_ids = [a.id for a in ExamAttempt.query.filter_by(user_id=current_user.id).all()]
    recent_warnings = []
    if attempt_ids:
        recent_warnings = Warning.query.filter(
            Warning.attempt_id.in_(attempt_ids)
        ).order_by(Warning.timestamp.desc()).limit(10).all()

    return render_template(
        'student/dashboard.html',
        available_exams=available_exams,
        active_attempts=active_attempts,
        completed_results=completed_results,
        recent_warnings=recent_warnings
    )


@student_bp.route('/exam/<int:exam_id>/check')
@login_required
def system_check(exam_id):
    """Pre-exam system hardware and environment verification."""
    exam = db.get_or_404(Exam, exam_id)
    if not exam.is_published and not current_user.is_admin:
        flash("This exam is currently not available.", "warning")
        return redirect(url_for('student.dashboard'))

    return render_template('student/system_check.html', exam=exam)


@student_bp.route('/exam/<int:exam_id>/verify')
@login_required
def face_verification(exam_id):
    """Pre-exam biometric face verification."""
    exam = db.get_or_404(Exam, exam_id)
    if not exam.is_published and not current_user.is_admin:
        flash("This exam is not published.", "warning")
        return redirect(url_for('student.dashboard'))

    return render_template('student/face_verification.html', exam=exam)


@student_bp.route('/exam/<int:exam_id>/start', methods=['POST'])
@login_required
def start_exam(exam_id):
    """Initializes or resumes an ExamAttempt and redirects to the exam portal."""
    exam = db.get_or_404(Exam, exam_id)
    if not exam.is_published and not current_user.is_admin:
        flash("This exam is not active.", "warning")
        return redirect(url_for('student.dashboard'))

    # Check if there is already an active in_progress attempt
    existing_attempt = ExamAttempt.query.filter_by(
        user_id=current_user.id,
        exam_id=exam.id,
        status='in_progress'
    ).first()

    if existing_attempt:
        return redirect(url_for('student.take_exam', attempt_id=existing_attempt.id))

    # Calculate max possible score from questions
    max_score = float(sum(q.points for q in exam.questions.all()))

    # Create new attempt
    attempt = ExamAttempt(
        user_id=current_user.id,
        exam_id=exam.id,
        status='in_progress',
        started_at=utc_now(),
        max_score=max_score,
        risk_score=0.0,
        max_risk_score=0.0,
        proctoring_status='NORMAL'
    )
    db.session.add(attempt)
    db.session.commit()

    return redirect(url_for('student.take_exam', attempt_id=attempt.id))


@student_bp.route('/exam/<int:attempt_id>/take')
@login_required
def take_exam(attempt_id):
    """Full-screen exam environment with questions, timer, and AI Proctoring HUD."""
    attempt = db.get_or_404(ExamAttempt, attempt_id)

    # Authorization check
    if attempt.user_id != current_user.id and not current_user.is_admin:
        abort(403)

    if attempt.status != 'in_progress':
        flash("This examination has already been completed.", "info")
        return redirect(url_for('student.exam_result', attempt_id=attempt.id))

    exam = attempt.exam
    questions = exam.questions.order_by(Question.order.asc(), Question.id.asc()).all()

    # Preload already answered questions
    existing_answers = {a.question_id: a.selected_option for a in attempt.answers.all()}

    # Calculate remaining time in seconds
    elapsed_seconds = attempt.duration_seconds
    total_allowed_seconds = exam.duration_minutes * 60
    remaining_seconds = max(0, total_allowed_seconds - elapsed_seconds)

    if remaining_seconds <= 0:
        # Time expired: auto submit
        return redirect(url_for('student.auto_submit_expired', attempt_id=attempt.id))

    return render_template(
        'student/exam_interface.html',
        attempt=attempt,
        exam=exam,
        questions=questions,
        existing_answers=existing_answers,
        remaining_seconds=remaining_seconds
    )


@student_bp.route('/exam/<int:attempt_id>/auto_submit_expired')
@login_required
def auto_submit_expired(attempt_id):
    """Handles time expiration submission."""
    attempt = db.get_or_404(ExamAttempt, attempt_id)
    if attempt.user_id != current_user.id and not current_user.is_admin:
        abort(403)

    if attempt.status == 'in_progress':
        # Calculate score
        correct_count = 0
        total_score = 0.0
        for ans in attempt.answers.all():
            q = ans.question
            if q and ans.selected_option == q.correct_option:
                ans.is_correct = True
                total_score += q.points
                correct_count += 1
            else:
                ans.is_correct = False

        attempt.score = total_score
        attempt.percentage = (total_score / attempt.max_score * 100.0) if attempt.max_score > 0 else 0.0
        attempt.passed = attempt.percentage >= attempt.exam.passing_score
        attempt.status = 'completed'
        attempt.completed_at = utc_now()

        # Create Result record
        result = Result(
            attempt_id=attempt.id,
            user_id=attempt.user_id,
            exam_id=attempt.exam_id,
            score=attempt.score,
            max_score=attempt.max_score,
            percentage=attempt.percentage,
            passed=attempt.passed,
            proctoring_status=attempt.proctoring_status,
            warnings_count=attempt.warnings.count(),
            max_risk_score=attempt.max_risk_score,
            events_count=attempt.proctoring_events.count(),
            created_at=utc_now()
        )
        db.session.add(result)
        db.session.commit()

    flash("Examination time elapsed. Your answers have been safely submitted.", "warning")
    return redirect(url_for('student.exam_result', attempt_id=attempt.id))


@student_bp.route('/exam/<int:attempt_id>/result')
@login_required
def exam_result(attempt_id):
    """Displays student performance and proctoring clearance."""
    attempt = db.get_or_404(ExamAttempt, attempt_id)
    if attempt.user_id != current_user.id and not current_user.is_admin:
        abort(403)

    result = Result.query.filter_by(attempt_id=attempt.id).first()
    return render_template('student/exam_result.html', attempt=attempt, result=result)
