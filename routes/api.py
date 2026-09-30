import base64
from datetime import datetime, timezone
import cv2
import numpy as np
from flask import Blueprint, request, jsonify, Response, current_app
from flask_login import login_required, current_user
from database import db
from database.models import ExamAttempt, Question, Answer, ProctoringEvent, Warning, Result, User, Exam, utc_now
from camera import VideoCamera, gen_frames
from ai.proctoring_engine import ProctoringEngine

api_bp = Blueprint('api', __name__)

# Global instances (lazily initialized or created once)
camera_instance = None
proctoring_engine = None


def get_camera():
    global camera_instance
    if camera_instance is None:
        camera_instance = VideoCamera()
    return camera_instance


def get_engine():
    global proctoring_engine
    if proctoring_engine is None:
        proctoring_engine = ProctoringEngine()
    return proctoring_engine


@api_bp.route('/video_feed')
def video_feed():
    """Live MJPEG stream for exam proctoring feed."""
    camera = get_camera()
    return Response(
        gen_frames(camera),
        mimetype='multipart/x-mixed-replace; boundary=frame'
    )


@api_bp.route('/api/proctoring/system_check', methods=['POST'])
@login_required
def api_system_check():
    """Validates camera frame and face visibility during pre-exam system check."""
    data = request.get_json() or {}
    image_b64 = data.get('image', '')

    if not image_b64:
        return jsonify({'camera_ok': False, 'face_detected': False, 'message': 'No image data provided'}), 400

    try:
        # Decode base64 frame
        if ',' in image_b64:
            image_b64 = image_b64.split(',', 1)[1]
        image_bytes = base64.b64decode(image_b64)
        np_arr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

        if img is None:
            return jsonify({'camera_ok': False, 'face_detected': False, 'message': 'Invalid image format'}), 400

        engine = get_engine()
        face_res = engine.face_detector.detect(img)
        face_count = face_res['face_count']

        return jsonify({
            'camera_ok': True,
            'face_detected': face_count >= 1,
            'face_count': face_count,
            'status': face_res['status'],
            'message': 'Face detected successfully' if face_count == 1 else (
                'Multiple faces detected' if face_count > 1 else 'No face detected'
            )
        })
    except Exception as e:
        return jsonify({'camera_ok': False, 'face_detected': False, 'message': str(e)}), 500


@api_bp.route('/api/proctoring/verify_face', methods=['POST'])
@login_required
def api_verify_face():
    """Performs biometric confirmation ensuring exactly one face is clearly positioned."""
    data = request.get_json() or {}
    image_b64 = data.get('image', '')

    if not image_b64:
        return jsonify({'verified': False, 'message': 'No frame received'}), 400

    try:
        if ',' in image_b64:
            image_b64 = image_b64.split(',', 1)[1]
        image_bytes = base64.b64decode(image_b64)
        np_arr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

        if img is None:
            return jsonify({'verified': False, 'message': 'Frame decoding error'}), 400

        engine = get_engine()
        face_res = engine.face_detector.detect(img)
        count = face_res['face_count']

        if count == 0:
            return jsonify({
                'verified': False,
                'message': 'No face detected. Please ensure your face is well-lit and directly facing the camera.'
            })
        elif count > 1:
            return jsonify({
                'verified': False,
                'message': f'Multiple faces detected ({count}). You must be completely alone.'
            })

        return jsonify({
            'verified': True,
            'face_count': 1,
            'message': 'Biometric verification successful! Ready to proceed.'
        })
    except Exception as e:
        return jsonify({'verified': False, 'message': str(e)}), 500


@api_bp.route('/api/proctoring/analyze_frame', methods=['POST'])
@login_required
def api_analyze_frame():
    """
    Main real-time AI Proctoring endpoint:
    Analyzes student video frame, evaluates face, gaze, head pose, phone, audio,
    updates attempt risk metrics, logs events and returns live HUD data.
    """
    data = request.get_json() or {}
    image_b64 = data.get('image')
    attempt_id = data.get('attempt_id')
    volume_db = float(data.get('volume_db', 0.0))
    browser_event = data.get('browser_event')
    browser_event_details = data.get('browser_event_details')

    if not image_b64:
        return jsonify({'error': 'No image provided'}), 400

    try:
        if ',' in image_b64:
            image_b64 = image_b64.split(',', 1)[1]
        image_bytes = base64.b64decode(image_b64)
        np_arr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

        if img is None:
            return jsonify({'error': 'Image decode failed'}), 400

        engine = get_engine()
        results = engine.process_frame(
            img,
            attempt_id=attempt_id,
            volume_db=volume_db,
            browser_event=browser_event,
            browser_event_details=browser_event_details
        )

        # Update database if attempt_id is provided
        attempt = None
        if attempt_id:
            attempt = db.session.get(ExamAttempt, attempt_id)
            if attempt and attempt.status == 'in_progress':
                # Update attempt risk attributes
                attempt.risk_score = results['current_risk']
                if results['max_risk'] > attempt.max_risk_score:
                    attempt.max_risk_score = results['max_risk']
                attempt.proctoring_status = results['risk_status']

                # Save new events
                for ev in results.get('new_events', []):
                    pe = ProctoringEvent(
                        attempt_id=attempt.id,
                        event_type=ev['event_type'],
                        severity=ev['severity'],
                        confidence=ev['confidence'],
                        risk_increment=ev['risk_increment'],
                        details=ev['details'],
                        timestamp=utc_now()
                    )
                    db.session.add(pe)

                # Save new warning if generated
                warn = results.get('new_warning')
                if warn:
                    w = Warning(
                        attempt_id=attempt.id,
                        event_type=warn['event_type'],
                        confidence=warn['confidence'],
                        risk_score=warn['risk_score'],
                        description=warn['description'],
                        timestamp=utc_now()
                    )
                    db.session.add(w)

                db.session.commit()

        # Build clean JSON response for HUD
        response_data = {
            'face_count': results['face_count'],
            'face_status': results['face_status'],
            'gaze_direction': results['gaze_direction'],
            'is_looking_away': results['is_looking_away'],
            'head_pose': results['head_pose'],
            'head_angles': results['head_angles'],
            'person_count': results['person_count'],
            'phone_detected': results['phone_detected'],
            'phone_confidence': results['phone_confidence'],
            'audio_status': results['audio_status'],
            'current_risk': results['current_risk'],
            'max_risk': results['max_risk'],
            'risk_status': results['risk_status'],
            'warning': results['new_warning']
        }

        return jsonify(response_data)
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@api_bp.route('/api/exam/<int:attempt_id>/answer', methods=['POST'])
@login_required
def api_save_answer(attempt_id):
    """Saves candidate choice for a specific question."""
    attempt = db.get_or_404(ExamAttempt, attempt_id)
    if attempt.user_id != current_user.id and not current_user.is_admin:
        return jsonify({'error': 'Unauthorized'}), 403

    if attempt.status != 'in_progress':
        return jsonify({'error': 'Exam is already closed'}), 400

    data = request.get_json() or {}
    question_id = data.get('question_id')
    selected_option = data.get('selected_option', '').strip().upper()

    if not question_id or selected_option not in ['A', 'B', 'C', 'D']:
        return jsonify({'error': 'Invalid question or option'}), 400

    answer = Answer.query.filter_by(
        attempt_id=attempt.id,
        question_id=question_id
    ).first()

    if answer is None:
        answer = Answer(
            attempt_id=attempt.id,
            question_id=question_id,
            selected_option=selected_option,
            answered_at=utc_now()
        )
        db.session.add(answer)
    else:
        answer.selected_option = selected_option
        answer.answered_at = utc_now()

    db.session.commit()

    return jsonify({
        'success': True,
        'question_id': question_id,
        'selected_option': selected_option
    })


@api_bp.route('/api/exam/<int:attempt_id>/event', methods=['POST'])
@login_required
def api_log_event(attempt_id):
    """Logs browser events: tab switch, blur, fullscreen exit, copy/paste."""
    attempt = db.get_or_404(ExamAttempt, attempt_id)
    if attempt.user_id != current_user.id and not current_user.is_admin:
        return jsonify({'error': 'Unauthorized'}), 403

    if attempt.status != 'in_progress':
        return jsonify({'error': 'Exam closed'}), 400

    data = request.get_json() or {}
    event_type = data.get('event_type', 'BROWSER_SECURITY_EVENT').strip().upper()
    details = data.get('details', 'Client security event triggered.')

    engine = get_engine()
    risk_engine = engine.get_risk_engine(attempt.id)
    eval_res = risk_engine.update({
        'face_count': 1,
        'browser_event': event_type,
        'browser_event_details': details
    })

    # Save to database
    pe = ProctoringEvent(
        attempt_id=attempt.id,
        event_type=event_type,
        severity='HIGH',
        confidence=1.0,
        risk_increment=15.0,
        details=details,
        timestamp=utc_now()
    )
    db.session.add(pe)

    attempt.risk_score = eval_res['current_risk']
    if eval_res['max_risk'] > attempt.max_risk_score:
        attempt.max_risk_score = eval_res['max_risk']
    attempt.proctoring_status = eval_res['status']

    # Warning if generated
    if eval_res.get('new_warning'):
        w = Warning(
            attempt_id=attempt.id,
            event_type=event_type,
            confidence=1.0,
            risk_score=attempt.risk_score,
            description=eval_res['new_warning']['description'],
            timestamp=utc_now()
        )
        db.session.add(w)

    db.session.commit()

    return jsonify({
        'success': True,
        'event_type': event_type,
        'current_risk': attempt.risk_score,
        'proctoring_status': attempt.proctoring_status,
        'warning': eval_res.get('new_warning')
    })


@api_bp.route('/api/exam/<int:attempt_id>/status', methods=['GET'])
@login_required
def api_exam_status(attempt_id):
    """Returns real-time remaining seconds and proctoring status."""
    attempt = db.get_or_404(ExamAttempt, attempt_id)
    if attempt.user_id != current_user.id and not current_user.is_admin:
        return jsonify({'error': 'Unauthorized'}), 403

    elapsed = attempt.duration_seconds
    total = attempt.exam.duration_minutes * 60
    remaining = max(0, total - elapsed)

    return jsonify({
        'attempt_id': attempt.id,
        'status': attempt.status,
        'elapsed_seconds': elapsed,
        'remaining_seconds': remaining,
        'current_risk': round(attempt.risk_score, 1),
        'max_risk': round(attempt.max_risk_score, 1),
        'proctoring_status': attempt.proctoring_status,
        'answered_count': attempt.answers.count(),
        'total_questions': attempt.exam.total_questions
    })


@api_bp.route('/api/exam/<int:attempt_id>/submit', methods=['POST'])
@login_required
def api_submit_exam(attempt_id):
    """Submits exam, calculates final score, and evaluates pass/fail status."""
    attempt = db.get_or_404(ExamAttempt, attempt_id)
    if attempt.user_id != current_user.id and not current_user.is_admin:
        return jsonify({'error': 'Unauthorized'}), 403

    if attempt.status == 'completed':
        return jsonify({
            'success': True,
            'redirect_url': f'/exam/{attempt.id}/result'
        })

    # Evaluate answers
    exam = attempt.exam
    total_score = 0.0
    for ans in attempt.answers.all():
        q = ans.question
        if q and ans.selected_option == q.correct_option:
            ans.is_correct = True
            total_score += q.points
        else:
            ans.is_correct = False

    max_possible = float(sum(q.points for q in exam.questions.all()))
    attempt.score = total_score
    attempt.max_score = max_possible
    attempt.percentage = (total_score / max_possible * 100.0) if max_possible > 0 else 0.0
    attempt.passed = attempt.percentage >= exam.passing_score
    attempt.status = 'completed'
    attempt.completed_at = utc_now()

    # Create / Update Result
    existing_result = Result.query.filter_by(attempt_id=attempt.id).first()
    if not existing_result:
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
    else:
        existing_result.score = attempt.score
        existing_result.percentage = attempt.percentage
        existing_result.passed = attempt.passed
        existing_result.proctoring_status = attempt.proctoring_status
        existing_result.max_risk_score = attempt.max_risk_score

    db.session.commit()

    # Free memory in proctoring engine
    engine = get_engine()
    engine.remove_attempt(attempt.id)

    return jsonify({
        'success': True,
        'redirect_url': f'/exam/{attempt.id}/result'
    })


@api_bp.route('/api/admin/stats', methods=['GET'])
@login_required
def api_admin_stats():
    """Provides dynamic metrics for admin charts."""
    if not current_user.is_admin:
        return jsonify({'error': 'Unauthorized'}), 403

    status_counts = {
        'NORMAL': ExamAttempt.query.filter_by(proctoring_status='NORMAL').count(),
        'LOW_RISK': ExamAttempt.query.filter_by(proctoring_status='LOW_RISK').count(),
        'WARNING': ExamAttempt.query.filter_by(proctoring_status='WARNING').count(),
        'HIGH_RISK': ExamAttempt.query.filter_by(proctoring_status='HIGH_RISK').count(),
        'CRITICAL': ExamAttempt.query.filter_by(proctoring_status='CRITICAL').count()
    }

    # Infractions by category
    categories = ['FACE_MISSING', 'MULTIPLE_FACES', 'PHONE_DETECTED', 'LOOKING_AWAY', 'HEAD_POSE_ABNORMAL', 'TAB_SWITCH']
    infraction_counts = {
        cat: ProctoringEvent.query.filter_by(event_type=cat).count() for cat in categories
    }

    return jsonify({
        'risk_distribution': status_counts,
        'infraction_counts': infraction_counts
    })
