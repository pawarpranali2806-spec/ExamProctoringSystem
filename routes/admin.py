from datetime import datetime
from flask import Blueprint, render_template, redirect, url_for, flash, request, abort, jsonify
from flask_login import login_required, current_user
from database import db
from database.models import User, Exam, Question, ExamAttempt, Answer, Result, ProctoringEvent, Warning
from routes.auth import admin_required

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')


@admin_bp.route('/dashboard')
@login_required
@admin_required
def dashboard():
    """Main administrator dashboard with metrics, risk breakdown, and attempts."""
    total_students = User.query.filter_by(role='student').count()
    total_exams = Exam.query.count()
    total_attempts = ExamAttempt.query.count()
    completed_attempts = ExamAttempt.query.filter_by(status='completed').count()

    # Suspicious attempts: attempts that reached WARNING, HIGH_RISK or CRITICAL
    suspicious_count = ExamAttempt.query.filter(
        ExamAttempt.proctoring_status.in_(['WARNING', 'HIGH_RISK', 'CRITICAL'])
    ).count()

    # Risk status distribution
    risk_distribution = {
        'NORMAL': ExamAttempt.query.filter_by(proctoring_status='NORMAL').count(),
        'LOW_RISK': ExamAttempt.query.filter_by(proctoring_status='LOW_RISK').count(),
        'WARNING': ExamAttempt.query.filter_by(proctoring_status='WARNING').count(),
        'HIGH_RISK': ExamAttempt.query.filter_by(proctoring_status='HIGH_RISK').count(),
        'CRITICAL': ExamAttempt.query.filter_by(proctoring_status='CRITICAL').count()
    }

    # Recent attempts
    recent_attempts = ExamAttempt.query.order_by(
        ExamAttempt.started_at.desc()
    ).limit(10).all()

    # Total events and warnings
    total_events = ProctoringEvent.query.count()
    total_warnings = Warning.query.count()

    return render_template(
        'admin/dashboard.html',
        total_students=total_students,
        total_exams=total_exams,
        total_attempts=total_attempts,
        completed_attempts=completed_attempts,
        suspicious_count=suspicious_count,
        risk_distribution=risk_distribution,
        recent_attempts=recent_attempts,
        total_events=total_events,
        total_warnings=total_warnings
    )


@admin_bp.route('/exams')
@login_required
@admin_required
def list_exams():
    """List all created exams."""
    exams = Exam.query.order_by(Exam.created_at.desc()).all()
    return render_template('admin/exams_list.html', exams=exams)


@admin_bp.route('/exams/new', methods=['GET', 'POST'])
@login_required
@admin_required
def create_exam():
    """Create a new exam."""
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        description = request.form.get('description', '').strip()
        duration_minutes = int(request.form.get('duration_minutes', 30))
        passing_score = int(request.form.get('passing_score', 60))
        is_published = bool(request.form.get('is_published'))

        if not title:
            flash("Exam title is required.", "warning")
            return render_template('admin/exam_form.html', action='Create')

        new_exam = Exam(
            title=title,
            description=description,
            duration_minutes=max(5, duration_minutes),
            passing_score=max(1, min(100, passing_score)),
            is_published=is_published,
            created_by=current_user.id
        )
        db.session.add(new_exam)
        db.session.commit()

        flash(f"Exam '{new_exam.title}' created! Now add questions.", "success")
        return redirect(url_for('admin.manage_questions', exam_id=new_exam.id))

    return render_template('admin/exam_form.html', action='Create', exam=None)


@admin_bp.route('/exams/<int:exam_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_exam(exam_id):
    """Edit existing exam details."""
    exam = db.get_or_404(Exam, exam_id)

    if request.method == 'POST':
        exam.title = request.form.get('title', '').strip() or exam.title
        exam.description = request.form.get('description', '').strip()
        exam.duration_minutes = max(5, int(request.form.get('duration_minutes', exam.duration_minutes)))
        exam.passing_score = max(1, min(100, int(request.form.get('passing_score', exam.passing_score))))
        exam.is_published = bool(request.form.get('is_published'))

        db.session.commit()
        flash("Exam settings updated successfully.", "success")
        return redirect(url_for('admin.list_exams'))

    return render_template('admin/exam_form.html', action='Edit', exam=exam)


@admin_bp.route('/exams/<int:exam_id>/toggle_publish', methods=['POST'])
@login_required
@admin_required
def toggle_publish(exam_id):
    """Toggles published status of an exam."""
    exam = db.get_or_404(Exam, exam_id)
    exam.is_published = not exam.is_published
    db.session.commit()
    status_str = "Published" if exam.is_published else "Unpublished"
    flash(f"Exam '{exam.title}' is now {status_str}.", "info")
    return redirect(url_for('admin.list_exams'))


@admin_bp.route('/exams/<int:exam_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_exam(exam_id):
    """Deletes an exam and its associated questions/attempts."""
    exam = db.get_or_404(Exam, exam_id)
    title = exam.title
    db.session.delete(exam)
    db.session.commit()
    flash(f"Exam '{title}' has been deleted.", "success")
    return redirect(url_for('admin.list_exams'))


@admin_bp.route('/exams/<int:exam_id>/questions', methods=['GET', 'POST'])
@login_required
@admin_required
def manage_questions(exam_id):
    """Manage and add questions to an exam."""
    exam = db.get_or_404(Exam, exam_id)

    if request.method == 'POST':
        question_text = request.form.get('question_text', '').strip()
        opt_a = request.form.get('option_a', '').strip()
        opt_b = request.form.get('option_b', '').strip()
        opt_c = request.form.get('option_c', '').strip()
        opt_d = request.form.get('option_d', '').strip()
        correct_option = request.form.get('correct_option', 'A').strip().upper()
        points = int(request.form.get('points', 1))

        if not question_text or not opt_a or not opt_b or not opt_c or not opt_d:
            flash("All question fields and options are required.", "warning")
        elif correct_option not in ['A', 'B', 'C', 'D']:
            flash("Correct option must be A, B, C, or D.", "warning")
        else:
            q_order = exam.questions.count() + 1
            new_q = Question(
                exam_id=exam.id,
                question_text=question_text,
                option_a=opt_a,
                option_b=opt_b,
                option_c=opt_c,
                option_d=opt_d,
                correct_option=correct_option,
                points=max(1, points),
                order=q_order
            )
            db.session.add(new_q)
            db.session.commit()
            flash("Question added successfully!", "success")

        return redirect(url_for('admin.manage_questions', exam_id=exam.id))

    questions = exam.questions.order_by(Question.order.asc()).all()
    return render_template('admin/questions.html', exam=exam, questions=questions)


@admin_bp.route('/questions/<int:question_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_question(question_id):
    """Delete a specific question."""
    q = db.get_or_404(Question, question_id)
    exam_id = q.exam_id
    db.session.delete(q)
    db.session.commit()
    flash("Question removed.", "info")
    return redirect(url_for('admin.manage_questions', exam_id=exam_id))


@admin_bp.route('/attempts')
@login_required
@admin_required
def list_attempts():
    """List student attempts with search and risk-level filtering."""
    risk_filter = request.args.get('risk', '').strip().upper()
    search_query = request.args.get('q', '').strip()

    query = ExamAttempt.query.join(User).join(Exam)

    if risk_filter in ['NORMAL', 'LOW_RISK', 'WARNING', 'HIGH_RISK', 'CRITICAL']:
        query = query.filter(ExamAttempt.proctoring_status == risk_filter)

    if search_query:
        query = query.filter(
            (User.full_name.ilike(f"%{search_query}%")) |
            (User.email.ilike(f"%{search_query}%")) |
            (Exam.title.ilike(f"%{search_query}%"))
        )

    attempts = query.order_by(ExamAttempt.started_at.desc()).all()
    return render_template('admin/attempts_list.html', attempts=attempts, selected_risk=risk_filter, search_query=search_query)


@admin_bp.route('/attempt/<int:attempt_id>/report')
@login_required
@admin_required
def attempt_report(attempt_id):
    """Detailed proctoring audit report for an exam attempt."""
    attempt = db.get_or_404(ExamAttempt, attempt_id)
    exam = attempt.exam
    student = attempt.student
    result = attempt.result

    # All proctoring events sorted by time
    events = attempt.proctoring_events.order_by(ProctoringEvent.timestamp.asc()).all()

    # All warnings sorted by time
    warnings = attempt.warnings.order_by(Warning.timestamp.asc()).all()

    # Detailed questions and candidate's chosen answers
    questions = exam.questions.order_by(Question.order.asc()).all()
    user_answers = {a.question_id: a for a in attempt.answers.all()}

    # Event count by type
    event_breakdown = {}
    for ev in events:
        event_breakdown[ev.event_type] = event_breakdown.get(ev.event_type, 0) + 1

    return render_template(
        'admin/attempt_report.html',
        attempt=attempt,
        exam=exam,
        student=student,
        result=result,
        events=events,
        warnings=warnings,
        questions=questions,
        user_answers=user_answers,
        event_breakdown=event_breakdown
    )
