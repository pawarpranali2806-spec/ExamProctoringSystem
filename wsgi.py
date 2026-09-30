import os
from app import create_app
from database import db
from database.models import User

config_name = os.environ.get('FLASK_CONFIG', 'production')
app = create_app(config_name)

# Auto-generate database tables in PostgreSQL upon startup
with app.app_context():
    try:
        db.create_all()
        # If database is fresh and empty, auto-seed default admin and exams
        if not User.query.first():
            print("[Startup] Empty database detected. Auto-seeding initial admin and demo exams...")
            from seed_data import seed
            seed(config_name=config_name, drop_existing=False)
            print("[Startup] Database tables and demo data created successfully.")
    except Exception as e:
        print(f"[Startup] Database setup note: {e}")

if __name__ == '__main__':
    app.run()
