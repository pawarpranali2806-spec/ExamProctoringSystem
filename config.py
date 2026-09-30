import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / '.env')


class Config:
    """Base configuration."""
    SECRET_KEY = os.environ.get('SECRET_KEY', 'panopticon-default-dev-secret-key-2026')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Uploads & Storage
    UPLOAD_FOLDER = BASE_DIR / 'uploads'
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 MB max upload
    
    # AI Engine Thresholds
    HEAD_POSE_YAW_THRESHOLD = float(os.environ.get('HEAD_POSE_YAW_THRESHOLD', 28.0))
    HEAD_POSE_PITCH_THRESHOLD = float(os.environ.get('HEAD_POSE_PITCH_THRESHOLD', 22.0))
    EYE_GAZE_EAR_THRESHOLD = float(os.environ.get('EYE_GAZE_EAR_THRESHOLD', 0.18))
    EYE_GAZE_LOOKAWAY_FRAMES = int(os.environ.get('EYE_GAZE_LOOKAWAY_FRAMES', 6))
    MOBILE_DETECTION_CONFIDENCE = float(os.environ.get('MOBILE_DETECTION_CONFIDENCE', 0.45))
    PERSON_DETECTION_CONFIDENCE = float(os.environ.get('PERSON_DETECTION_CONFIDENCE', 0.50))
    
    # Cheating Risk Engine
    RISK_DECAY_RATE = float(os.environ.get('RISK_DECAY_RATE', 0.92))
    RISK_WARNING_THRESHOLD = int(os.environ.get('RISK_WARNING_THRESHOLD', 45))
    RISK_HIGH_THRESHOLD = int(os.environ.get('RISK_HIGH_THRESHOLD', 70))
    RISK_CRITICAL_THRESHOLD = int(os.environ.get('RISK_CRITICAL_THRESHOLD', 88))


class DevelopmentConfig(Config):
    """Development environment configuration."""
    DEBUG = True
    db_url = os.environ.get('DATABASE_URL') or f"sqlite:///{BASE_DIR / 'panopticon.db'}"
    if db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql://", 1)
    SQLALCHEMY_DATABASE_URI = db_url


class ProductionConfig(Config):
    """Production environment configuration."""
    DEBUG = False
    db_url = os.environ.get('DATABASE_URL')
    if not db_url:
        db_url = f"sqlite:///{BASE_DIR / 'panopticon.db'}"
    elif db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql://", 1)
    SQLALCHEMY_DATABASE_URI = db_url


class TestingConfig(Config):
    """Testing environment configuration."""
    TESTING = True
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    WTF_CSRF_ENABLED = False


config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}
