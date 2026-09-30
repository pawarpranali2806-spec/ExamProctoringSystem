# PROJECT PANOPTICON: AI-POWERED ONLINE EXAM PROCTORING SYSTEM

[![Python 3.12](https://img.shields.io/badge/Python-3.12-blue.svg)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Framework-Flask_3.x-green.svg)](https://flask.palletsprojects.com/)
[![Computer Vision](https://img.shields.io/badge/Vision-MediaPipe_%7C_OpenCV_%7C_YOLOv8-cyan.svg)](https://mediapipe.dev/)
[![Security](https://img.shields.io/badge/Integrity-Zero_Trust_Audit-violet.svg)](#)

Project Panopticon is a high-performance, autonomous online examination proctoring platform engineered to protect academic integrity during remote assessments. Built with Flask, SQLAlchemy, MediaPipe, OpenCV, and YOLOv8, Panopticon continuously monitors exam environments through a cyberpunk glassmorphism interface and a persistent, fair, multi-factor cheating risk engine.

---

## Key Features

1. **Biometric Face Verification**
   - Pre-flight facial presence verification using MediaPipe 468-point face mesh.
   - Enforces strict single-candidate occupancy before unlocking the exam room.
   - Real-time continuous detection of missing face (`NO_FACE`) or unauthorized secondary individuals (`MULTIPLE_FACES`).

2. **3D Head Pose & Gaze Vectoring**
   - Solves Perspective-n-Point (PnP) using 3D generic facial models to track Pitch, Yaw, and Roll Euler angles.
   - Measures Iris-to-Eye-Corner ratios (EAR) to detect suspicious looking away (left, right, desk downward) without triggering on harmless natural blinks.

3. **YOLOv8 Multi-Class Threat Detection**
   - Real-time object detection detecting unauthorized mobile devices (COCO class 67) and extra persons (COCO class 0).
   - Fast GPU/CPU inference (<40ms per frame) without bottlenecking user interaction.

4. **Acoustic Anomaly Monitoring**
   - Measures background decibel levels and ambient noise spikes through client Web Audio APIs.
   - Flags suspicious whispering, speech assistance, or sustained talking.

5. **Browser Security & Lockdown Events**
   - Real-time telemetry tracking tab switches (`visibilitychange`), window loss of focus (`blur`), clipboard violations (`copy`, `cut`, `paste`), and fullscreen exits.

6. **Adaptive Cheating Risk Engine**
   - Multi-factor confidence-weighted scoring:
     - `NORMAL` (0 - 20%)
     - `LOW_RISK` (21 - 40%)
     - `WARNING` (41 - 65%)
     - `HIGH_RISK` (66 - 85%)
     - `CRITICAL` (86 - 100%)
   - Incorporates persistence time windows (brief harmless glances are ignored; sustained infractions escalate risk).
   - Smooth risk decay rewards candidates when normal posture resumes.

7. **Audit Reporting & Analytics**
   - Chronological telemetry timeline documenting every detected anomaly with timestamps, confidence scores, and risk increments.
   - Question-by-question candidate answer verification.
   - One-click print / export to PDF formatting for formal academic disciplinary dossiers.

---

## Project Structure

```text
Project-Panopticon/
├── app.py                     # Application factory & entrypoint
├── config.py                  # Dev, Prod, and Test configurations
├── wsgi.py                    # Production WSGI entrypoint
├── requirements.txt           # Python dependencies
├── .env.example               # Environment variables template
├── .env                       # Local environment variables
├── seed_data.py               # Seed database with demo exams, users & telemetry
├── README.md                  # Complete documentation
│
├── ai/                        # AI & Computer Vision Subsystems
│   ├── __init__.py
│   ├── face_detection.py      # MediaPipe / Haar cascade face detector
│   ├── face_mesh.py           # 468/478-point facial mesh extractor
│   ├── eye_tracking.py        # Iris gaze direction & Eye Aspect Ratio (EAR)
│   ├── head_pose.py           # 3D PnP Euler angles (Yaw, Pitch, Roll)
│   ├── person_detection.py    # YOLOv8 Person detector (class 0)
│   ├── mobile_detection.py    # YOLOv8 Cell Phone detector (class 67)
│   ├── audio_monitor.py       # Decibel anomaly & speech monitor
│   ├── cheating_score.py      # Centralized risk engine with persistence & decay
│   └── proctoring_engine.py   # Master AI coordinator & HUD frame annotator
│
├── camera/                    # Camera Management & Streaming
│   ├── __init__.py
│   └── camera.py              # Thread-safe OpenCV capture with simulated fallback
│
├── database/                  # Database Layer
│   ├── __init__.py            # SQLAlchemy db instance
│   └── models.py              # User, Exam, Question, Attempt, Answer, Events, Result
│
├── routes/                    # Web & REST Endpoints
│   ├── __init__.py
│   ├── auth.py                # Login, registration, role checks
│   ├── student.py             # Student portal, system check, live exam, result
│   ├── admin.py               # Admin control center, exam builder, audit reports
│   └── api.py                 # Real-time frame analysis, answer saving, stats
│
├── templates/                 # Jinja2 Templates (Dark Cyberpunk Glassmorphism)
│   ├── base.html              # Base navigation, flash alerts & layout
│   ├── landing.html           # Landing showcase & architecture overview
│   ├── auth/                  # Login & registration templates
│   ├── student/               # Dashboard, system check, biometric verification, exam room
│   ├── admin/                 # Admin dashboard, exam lists, question builder, audit reports
│   └── errors/                # 403, 404, and 500 error pages
│
├── static/                    # Static Assets
│   ├── css/
│   │   ├── main.css           # Design system, glass cards, glowing badges
│   │   └── exam.css           # Live examination HUD, video scanlines, timers
│   └── js/
│       ├── main.js            # Common utility scripts & toasts
│       ├── system_check.js    # Pre-flight hardware diagnostics
│       └── proctoring_client.js # Real-time exam client & AI telemetry loop
│
├── tests/                     # Automated Pytest Suite
│   ├── __init__.py
│   ├── test_auth.py           # Authentication & role restrictions
│   ├── test_exam.py           # Exam creation & grading logic
│   ├── test_risk_engine.py    # Cheating score engine & persistence
│   ├── test_ai_modules.py     # Face, eye, head pose, and audio unit tests
│   └── test_api.py            # Real-time proctoring APIs
│
├── uploads/                   # Uploaded media assets
└── instance/                  # Local SQLite database files
```

---

## Quick Start (Local Setup)

### 1. Prerequisites
- Python 3.12 (Recommended for OpenCV, MediaPipe, NumPy, and PyTorch binary wheel compatibility)
- Git & modern web browser (Chrome, Edge, Firefox, or Safari) with camera/mic permissions

### 2. Installation
```powershell
# Navigate to project directory
cd Project-Panopticon

# Create and activate Python 3.12 virtual environment
py -3.12 -m venv venv
.\venv\Scripts\Activate.ps1

# Upgrade pip and install dependencies
pip install --upgrade pip
pip install -r requirements.txt
```

### 3. Initialize & Seed Database
```powershell
python seed_data.py
```

### 4. Run Development Server
```powershell
python app.py
```
Open your browser and navigate to: **`http://127.0.0.1:5000`**

---

## Demo Accounts

| Role | Email | Password | Access Capabilities |
| :--- | :--- | :--- | :--- |
| **Administrator** | `admin@panopticon.ai` | `Admin@12345` | Exam Creation, Question Bank, Audit Reports, Telemetry Charts |
| **Candidate** | `student@panopticon.ai` | `Student@12345` | System Check, Biometric Face Verification, Live Proctored Exam |
| **Candidate 2** | `sarah@panopticon.ai` | `Student@12345` | Sample clean candidate session with 87.5% passing score |

---

## Running Automated Tests

Run the full pytest suite:
```powershell
pytest tests/ -v
```

---

## Production Deployment Guide

### Environment Variables
Configure your `.env` file for production:
```env
FLASK_APP=app.py
FLASK_ENV=production
SECRET_KEY=generate-a-strong-random-64-char-secret-key
DATABASE_URL=postgresql://panopticon_user:strong_password@localhost:5432/panopticon_db
```

### Running with Gunicorn (Linux / Container)
```bash
gunicorn -w 4 -b 0.0.0.0:8000 wsgi:app
```

### Running with Waitress (Windows Production)
```powershell
pip install waitress
waitress-serve --port=5000 wsgi:app
```

---

## License
MIT License &copy; 2026 Project Panopticon. Developed for high-integrity academic assessment.
