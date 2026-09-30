from datetime import datetime, timedelta, timezone
from app import create_app
from database import db
from database.models import User, Exam, Question, ExamAttempt, Answer, ProctoringEvent, Warning, Result


def seed():
    app = create_app('development')
    with app.app_context():
        print("[Seed] Dropping and recreating tables...")
        db.drop_all()
        db.create_all()

        print("[Seed] Creating users...")
        admin = User(
            username='admin',
            email='admin@panopticon.ai',
            full_name='Dr. Evelyn Vance',
            role='admin'
        )
        admin.set_password('Admin@12345')

        student1 = User(
            username='student',
            email='student@panopticon.ai',
            full_name='Alex Mercer',
            role='student'
        )
        student1.set_password('Student@12345')

        student2 = User(
            username='sarah',
            email='sarah@panopticon.ai',
            full_name='Sarah Connor',
            role='student'
        )
        student2.set_password('Student@12345')

        db.session.add_all([admin, student1, student2])
        db.session.commit()

        print("[Seed] Creating sample examinations...")
        # Exam 1: Cybersecurity & AI Ethics
        exam1 = Exam(
            title="Advanced Cybersecurity & AI Ethics Certification",
            description="Comprehensive assessment evaluating threat modeling, zero-trust architectures, model evasion techniques, and algorithmic governance in mission-critical environments.",
            duration_minutes=20,
            passing_score=70,
            is_published=True,
            created_by=admin.id
        )

        # Exam 2: Computer Vision & Deep Learning
        exam2 = Exam(
            title="Deep Learning & Real-Time Computer Vision Engineering",
            description="Rigorous exam testing spatial feature extraction, YOLO object detection architectures, loss optimization, and edge inference deployment.",
            duration_minutes=15,
            passing_score=65,
            is_published=True,
            created_by=admin.id
        )

        db.session.add_all([exam1, exam2])
        db.session.commit()

        print("[Seed] Creating questions for Exam 1...")
        exam1_questions = [
            (
                "Which security principle mandates that users and systems are granted only the minimum access rights essential for their immediate operational function?",
                "Principle of Least Privilege",
                "Defense in Depth",
                "Separation of Duties",
                "Fail-Safe Defaults",
                "A",
                2
            ),
            (
                "What type of machine learning adversarial attack involves subtly modifying test inputs with imperceptible noise to force misclassification?",
                "Data Poisoning",
                "Evasion Attack (Adversarial Perturbation)",
                "Model Inversion",
                "Membership Inference",
                "B",
                2
            ),
            (
                "Under the Zero Trust Architecture (ZTA) framework, what is the fundamental security paradigm regarding internal network traffic?",
                "Trust all internal traffic behind the perimeter firewall",
                "Never trust, always verify every access request regardless of origin",
                "Verify only requests originating from external IP subnets",
                "Rely strictly on physical network isolation",
                "B",
                2
            ),
            (
                "Which cryptographic mechanism guarantees non-repudiation in electronic transactions?",
                "Symmetric AES-256 Encryption",
                "Digital Signature using Private Key",
                "HMAC with Pre-shared Secret",
                "Diffie-Hellman Key Exchange",
                "B",
                2
            ),
            (
                "What is the primary risk associated with Prompt Injection attacks against LLM-integrated services?",
                "Overheating server GPU clusters",
                "Overriding system instructions to execute unauthorized commands or extract private context",
                "Causing denial-of-service via memory leaks",
                "Corrupting model parameter weights on disk",
                "B",
                2
            ),
            (
                "Differential Privacy provides formal mathematical guarantees that:",
                "Data encryption keys cannot be broken within polynomial time",
                "The presence or absence of any single individual in a dataset does not significantly affect query results",
                "All personal identifiers are permanently scrubbed with zero utility loss",
                "Server memory buffers are zeroed after each inference operation",
                "B",
                2
            ),
            (
                "In web application security, what header is explicitly recommended to protect against Cross-Site Scripting (XSS)?",
                "Strict-Transport-Security (HSTS)",
                "Content-Security-Policy (CSP)",
                "X-Forwarded-For",
                "Access-Control-Allow-Origin: *",
                "B",
                2
            ),
            (
                "Which anomaly detection approach models normal behavioral baselines and flags statistically significant deviations?",
                "Signature-based Detection",
                "Heuristic Rule Matching",
                "Unsupervised Behavioral Anomaly Detection",
                "Static Whitelist Matching",
                "C",
                2
            )
        ]

        for i, (text, a, b, c, d, correct, pts) in enumerate(exam1_questions, 1):
            q = Question(
                exam_id=exam1.id,
                question_text=text,
                option_a=a,
                option_b=b,
                option_c=c,
                option_d=d,
                correct_option=correct,
                points=pts,
                order=i
            )
            db.session.add(q)

        print("[Seed] Creating questions for Exam 2...")
        exam2_questions = [
            (
                "In convolutional neural networks, what is the role of 1x1 convolutions (pointwise convolutions)?",
                "Downsample spatial resolution like max pooling",
                "Dimensionality reduction/increase across channel depth with non-linearity",
                "Compute optical flow between sequential frames",
                "Eliminate the need for activation functions",
                "B",
                2
            ),
            (
                "How does the YOLO (You Only Look Once) architecture differ from two-stage detectors like Faster R-CNN?",
                "YOLO extracts features strictly on CPU cores",
                "YOLO predicts bounding boxes and class probabilities directly in a single forward pass",
                "YOLO generates region proposals using selective search before CNN classification",
                "YOLO requires separate networks for classification and bounding box regression",
                "B",
                2
            ),
            (
                "What problem does Batch Normalization primarily mitigate during deep neural network training?",
                "Exploding dataset size",
                "Internal Covariate Shift and gradient vanishing/exploding",
                "GPU memory fragmentation",
                "Over-regularization of convolutional kernels",
                "B",
                2
            ),
            (
                "In MediaPipe Face Mesh, how many 3D landmarks are estimated in real-time on the human face?",
                "68 landmarks",
                "128 landmarks",
                "468/478 landmarks",
                "1024 landmarks",
                "C",
                2
            ),
            (
                "What is Intersection over Union (IoU) primarily used for in object detection evaluation?",
                "Measuring inference speed in milliseconds",
                "Quantifying the degree of overlap between predicted and ground-truth bounding boxes",
                "Balancing the ratio of positive and negative training samples",
                "Normalizing pixel brightness across video frames",
                "B",
                2
            )
        ]

        for i, (text, a, b, c, d, correct, pts) in enumerate(exam2_questions, 1):
            q = Question(
                exam_id=exam2.id,
                question_text=text,
                option_a=a,
                option_b=b,
                option_c=c,
                option_d=d,
                correct_option=correct,
                points=pts,
                order=i
            )
            db.session.add(q)

        db.session.commit()

        print("[Seed] Creating sample past attempts and proctoring telemetry...")
        # Attempt 1: Sarah Connor took Exam 1 - Clean session, high score, passed, NORMAL status
        start_time1 = datetime.now(timezone.utc) - timedelta(hours=3)
        end_time1 = start_time1 + timedelta(minutes=14, seconds=22)

        attempt1 = ExamAttempt(
            user_id=student2.id,
            exam_id=exam1.id,
            status='completed',
            started_at=start_time1,
            completed_at=end_time1,
            score=14.0,
            max_score=16.0,
            percentage=87.5,
            passed=True,
            risk_score=5.0,
            max_risk_score=12.0,
            proctoring_status='NORMAL'
        )
        db.session.add(attempt1)
        db.session.commit()

        # Answers for Attempt 1
        q_list1 = exam1.questions.all()
        for idx, q in enumerate(q_list1):
            # Sarah got most right
            chosen = q.correct_option if idx != 4 else 'A'
            ans = Answer(
                attempt_id=attempt1.id,
                question_id=q.id,
                selected_option=chosen,
                is_correct=(chosen == q.correct_option),
                answered_at=start_time1 + timedelta(minutes=idx + 1)
            )
            db.session.add(ans)

        # Result 1
        res1 = Result(
            attempt_id=attempt1.id,
            user_id=student2.id,
            exam_id=exam1.id,
            score=14.0,
            max_score=16.0,
            percentage=87.5,
            passed=True,
            proctoring_status='NORMAL',
            warnings_count=0,
            max_risk_score=12.0,
            events_count=1,
            created_at=end_time1
        )
        db.session.add(res1)

        # Attempt 2: Alex Mercer took Exam 2 - Suspicious session with phone detection and multiple gaze events
        start_time2 = datetime.now(timezone.utc) - timedelta(hours=1)
        end_time2 = start_time2 + timedelta(minutes=12, seconds=45)

        attempt2 = ExamAttempt(
            user_id=student1.id,
            exam_id=exam2.id,
            status='completed',
            started_at=start_time2,
            completed_at=end_time2,
            score=6.0,
            max_score=10.0,
            percentage=60.0,
            passed=False,
            risk_score=48.0,
            max_risk_score=78.5,
            proctoring_status='HIGH_RISK'
        )
        db.session.add(attempt2)
        db.session.commit()

        # Answers for Attempt 2
        q_list2 = exam2.questions.all()
        for idx, q in enumerate(q_list2):
            chosen = q.correct_option if idx < 3 else 'A'
            ans = Answer(
                attempt_id=attempt2.id,
                question_id=q.id,
                selected_option=chosen,
                is_correct=(chosen == q.correct_option),
                answered_at=start_time2 + timedelta(minutes=idx * 2 + 1)
            )
            db.session.add(ans)

        # Proctoring Events for Attempt 2
        ev1 = ProctoringEvent(
            attempt_id=attempt2.id,
            event_type='LOOKING_AWAY',
            severity='MEDIUM',
            confidence=0.88,
            risk_increment=16.0,
            details="Eyes directed downward towards desk surface for 4 consecutive cycles.",
            timestamp=start_time2 + timedelta(minutes=3, seconds=10)
        )
        ev2 = ProctoringEvent(
            attempt_id=attempt2.id,
            event_type='PHONE_DETECTED',
            severity='CRITICAL',
            confidence=0.92,
            risk_increment=25.0,
            details="Mobile smartphone identified in candidate hand with 92% confidence.",
            timestamp=start_time2 + timedelta(minutes=5, seconds=42)
        )
        ev3 = ProctoringEvent(
            attempt_id=attempt2.id,
            event_type='TAB_SWITCH',
            severity='HIGH',
            confidence=1.0,
            risk_increment=18.0,
            details="Candidate switched browser tab or minimized examination portal.",
            timestamp=start_time2 + timedelta(minutes=8, seconds=15)
        )
        db.session.add_all([ev1, ev2, ev3])

        # Warnings for Attempt 2
        w1 = Warning(
            attempt_id=attempt2.id,
            event_type='LOOKING_AWAY',
            confidence=0.88,
            risk_score=26.0,
            description="Suspicious gaze direction detected. Maintain eyes on the examination screen.",
            timestamp=start_time2 + timedelta(minutes=3, seconds=12)
        )
        w2 = Warning(
            attempt_id=attempt2.id,
            event_type='PHONE_DETECTED',
            confidence=0.92,
            risk_score=68.5,
            description="Unauthorized mobile phone detected in view! Please remove immediately.",
            timestamp=start_time2 + timedelta(minutes=5, seconds=45)
        )
        w3 = Warning(
            attempt_id=attempt2.id,
            event_type='TAB_SWITCH',
            confidence=1.0,
            risk_score=78.5,
            description="Browser window focus lost. Navigating away from exam is logged as an infraction.",
            timestamp=start_time2 + timedelta(minutes=8, seconds=16)
        )
        db.session.add_all([w1, w2, w3])

        # Result 2
        res2 = Result(
            attempt_id=attempt2.id,
            user_id=student1.id,
            exam_id=exam2.id,
            score=6.0,
            max_score=10.0,
            percentage=60.0,
            passed=False,
            proctoring_status='HIGH_RISK',
            warnings_count=3,
            max_risk_score=78.5,
            events_count=3,
            created_at=end_time2
        )
        db.session.add(res2)

        db.session.commit()
        print("[Seed] Successfully seeded database with Admin, Students, Exams, and Past Telemetry!")


if __name__ == '__main__':
    seed()
