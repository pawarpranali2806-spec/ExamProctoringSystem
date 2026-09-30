from datetime import datetime, timezone
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from database import db


def utc_now():
    return datetime.now(timezone.utc).replace(tzinfo=None)


class User(UserMixin, db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    full_name = db.Column(db.String(120), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='student')  # 'student' or 'admin'
    avatar = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=utc_now)

    # Relationships
    attempts = db.relationship('ExamAttempt', backref='student', lazy='dynamic', cascade='all, delete-orphan')
    results = db.relationship('Result', backref='student', lazy='dynamic', cascade='all, delete-orphan')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    @property
    def is_admin(self):
        return self.role == 'admin'

    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'full_name': self.full_name,
            'role': self.role,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class Exam(db.Model):
    __tablename__ = 'exams'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    duration_minutes = db.Column(db.Integer, nullable=False, default=30)
    passing_score = db.Column(db.Integer, nullable=False, default=60)  # percentage
    is_published = db.Column(db.Boolean, default=False, nullable=False)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=utc_now)

    # Relationships
    creator = db.relationship('User', foreign_keys=[created_by], backref='created_exams')
    questions = db.relationship('Question', backref='exam', lazy='dynamic', cascade='all, delete-orphan', order_by='Question.order')
    attempts = db.relationship('ExamAttempt', backref='exam', lazy='dynamic', cascade='all, delete-orphan')

    @property
    def total_questions(self):
        return self.questions.count()

    @property
    def total_points(self):
        return sum(q.points for q in self.questions.all())

    def to_dict(self, include_questions=False):
        data = {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'duration_minutes': self.duration_minutes,
            'passing_score': self.passing_score,
            'is_published': self.is_published,
            'total_questions': self.total_questions,
            'total_points': self.total_points,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
        if include_questions:
            data['questions'] = [q.to_dict() for q in self.questions.all()]
        return data


class Question(db.Model):
    __tablename__ = 'questions'

    id = db.Column(db.Integer, primary_key=True)
    exam_id = db.Column(db.Integer, db.ForeignKey('exams.id', ondelete='CASCADE'), nullable=False)
    question_text = db.Column(db.Text, nullable=False)
    option_a = db.Column(db.String(500), nullable=False)
    option_b = db.Column(db.String(500), nullable=False)
    option_c = db.Column(db.String(500), nullable=False)
    option_d = db.Column(db.String(500), nullable=False)
    correct_option = db.Column(db.String(1), nullable=False)  # 'A', 'B', 'C', 'D'
    points = db.Column(db.Integer, nullable=False, default=1)
    order = db.Column(db.Integer, default=0)

    # Relationships
    answers = db.relationship('Answer', backref='question', lazy='dynamic', cascade='all, delete-orphan')

    def to_dict(self, include_correct=False):
        data = {
            'id': self.id,
            'exam_id': self.exam_id,
            'question_text': self.question_text,
            'option_a': self.option_a,
            'option_b': self.option_b,
            'option_c': self.option_c,
            'option_d': self.option_d,
            'points': self.points,
            'order': self.order
        }
        if include_correct:
            data['correct_option'] = self.correct_option
        return data


class ExamAttempt(db.Model):
    __tablename__ = 'exam_attempts'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    exam_id = db.Column(db.Integer, db.ForeignKey('exams.id', ondelete='CASCADE'), nullable=False)
    status = db.Column(db.String(20), default='in_progress', nullable=False)  # 'in_progress', 'completed', 'terminated'
    started_at = db.Column(db.DateTime, default=utc_now, nullable=False)
    completed_at = db.Column(db.DateTime, nullable=True)
    score = db.Column(db.Float, default=0.0)
    max_score = db.Column(db.Float, default=0.0)
    percentage = db.Column(db.Float, default=0.0)
    passed = db.Column(db.Boolean, default=False)
    risk_score = db.Column(db.Float, default=0.0)
    max_risk_score = db.Column(db.Float, default=0.0)
    proctoring_status = db.Column(db.String(20), default='NORMAL', nullable=False)  # 'NORMAL', 'LOW_RISK', 'WARNING', 'HIGH_RISK', 'CRITICAL'

    # Relationships
    answers = db.relationship('Answer', backref='attempt', lazy='dynamic', cascade='all, delete-orphan')
    proctoring_events = db.relationship('ProctoringEvent', backref='attempt', lazy='dynamic', cascade='all, delete-orphan')
    warnings = db.relationship('Warning', backref='attempt', lazy='dynamic', cascade='all, delete-orphan')
    result = db.relationship('Result', backref='attempt', uselist=False, cascade='all, delete-orphan')

    @property
    def duration_seconds(self):
        end = self.completed_at or utc_now()
        start = self.started_at or end
        if end.tzinfo is not None and start.tzinfo is None:
            start = start.replace(tzinfo=timezone.utc)
        elif end.tzinfo is None and start.tzinfo is not None:
            end = end.replace(tzinfo=timezone.utc)
        return max(0, int((end - start).total_seconds()))

    @property
    def duration_formatted(self):
        sec = self.duration_seconds
        mins = sec // 60
        secs = sec % 60
        return f"{mins}m {secs}s"

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'exam_id': self.exam_id,
            'status': self.status,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'duration_formatted': self.duration_formatted,
            'score': self.score,
            'max_score': self.max_score,
            'percentage': round(self.percentage, 1),
            'passed': self.passed,
            'risk_score': round(self.risk_score, 1),
            'max_risk_score': round(self.max_risk_score, 1),
            'proctoring_status': self.proctoring_status,
            'warnings_count': self.warnings.count(),
            'events_count': self.proctoring_events.count()
        }


class Answer(db.Model):
    __tablename__ = 'answers'

    id = db.Column(db.Integer, primary_key=True)
    attempt_id = db.Column(db.Integer, db.ForeignKey('exam_attempts.id', ondelete='CASCADE'), nullable=False)
    question_id = db.Column(db.Integer, db.ForeignKey('questions.id', ondelete='CASCADE'), nullable=False)
    selected_option = db.Column(db.String(1), nullable=True)  # 'A', 'B', 'C', 'D'
    is_correct = db.Column(db.Boolean, default=False)
    answered_at = db.Column(db.DateTime, default=utc_now)

    def to_dict(self):
        return {
            'id': self.id,
            'attempt_id': self.attempt_id,
            'question_id': self.question_id,
            'selected_option': self.selected_option,
            'is_correct': self.is_correct,
            'answered_at': self.answered_at.isoformat() if self.answered_at else None
        }


class ProctoringEvent(db.Model):
    __tablename__ = 'proctoring_events'

    id = db.Column(db.Integer, primary_key=True)
    attempt_id = db.Column(db.Integer, db.ForeignKey('exam_attempts.id', ondelete='CASCADE'), nullable=False, index=True)
    event_type = db.Column(db.String(50), nullable=False)  # 'FACE_MISSING', 'MULTIPLE_FACES', 'PHONE_DETECTED', etc.
    severity = db.Column(db.String(20), default='LOW', nullable=False)  # 'INFO', 'LOW', 'MEDIUM', 'HIGH', 'CRITICAL'
    confidence = db.Column(db.Float, default=1.0)
    risk_increment = db.Column(db.Float, default=0.0)
    details = db.Column(db.Text, nullable=True)
    timestamp = db.Column(db.DateTime, default=utc_now, nullable=False, index=True)

    def to_dict(self):
        return {
            'id': self.id,
            'attempt_id': self.attempt_id,
            'event_type': self.event_type,
            'severity': self.severity,
            'confidence': round(self.confidence, 2),
            'risk_increment': round(self.risk_increment, 1),
            'details': self.details,
            'timestamp': self.timestamp.strftime('%H:%M:%S') if self.timestamp else ''
        }


class Warning(db.Model):
    __tablename__ = 'warnings'

    id = db.Column(db.Integer, primary_key=True)
    attempt_id = db.Column(db.Integer, db.ForeignKey('exam_attempts.id', ondelete='CASCADE'), nullable=False, index=True)
    event_type = db.Column(db.String(50), nullable=False)
    confidence = db.Column(db.Float, default=1.0)
    risk_score = db.Column(db.Float, default=0.0)
    description = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=utc_now, nullable=False)

    def to_dict(self):
        return {
            'id': self.id,
            'attempt_id': self.attempt_id,
            'event_type': self.event_type,
            'confidence': round(self.confidence, 2),
            'risk_score': round(self.risk_score, 1),
            'description': self.description,
            'timestamp': self.timestamp.strftime('%H:%M:%S') if self.timestamp else ''
        }


class Result(db.Model):
    __tablename__ = 'results'

    id = db.Column(db.Integer, primary_key=True)
    attempt_id = db.Column(db.Integer, db.ForeignKey('exam_attempts.id', ondelete='CASCADE'), unique=True, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    exam_id = db.Column(db.Integer, db.ForeignKey('exams.id', ondelete='CASCADE'), nullable=False)
    score = db.Column(db.Float, default=0.0)
    max_score = db.Column(db.Float, default=0.0)
    percentage = db.Column(db.Float, default=0.0)
    passed = db.Column(db.Boolean, default=False)
    proctoring_status = db.Column(db.String(20), default='NORMAL', nullable=False)
    warnings_count = db.Column(db.Integer, default=0)
    max_risk_score = db.Column(db.Float, default=0.0)
    events_count = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=utc_now)

    # Relationships
    exam = db.relationship('Exam')

    def to_dict(self):
        return {
            'id': self.id,
            'attempt_id': self.attempt_id,
            'user_id': self.user_id,
            'exam_id': self.exam_id,
            'exam_title': self.exam.title if self.exam else '',
            'score': self.score,
            'max_score': self.max_score,
            'percentage': round(self.percentage, 1),
            'passed': self.passed,
            'proctoring_status': self.proctoring_status,
            'warnings_count': self.warnings_count,
            'max_risk_score': round(self.max_risk_score, 1),
            'events_count': self.events_count,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M') if self.created_at else ''
        }
