import os
from flask import Flask, render_template
from flask_login import LoginManager
from config import config
from database import db
from database.models import User
from routes import auth_bp, student_bp, admin_bp, api_bp


def create_app(config_name=None):
    """Application factory."""
    if config_name is None:
        config_name = os.environ.get('FLASK_CONFIG', 'default')

    app = Flask(__name__)
    app.config.from_object(config[config_name])

    # Ensure uploads & instance directories exist
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    os.makedirs(app.instance_path, exist_ok=True)

    # Initialize extensions
    db.init_app(app)

    # Login Manager
    login_manager = LoginManager()
    login_manager.login_view = 'auth.login'
    login_manager.login_message = "Please sign in to access this page."
    login_manager.login_message_category = "info"
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    # Register blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(student_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(api_bp)

    # Landing page route
    @app.route('/')
    def landing():
        return render_template('landing.html')

    # Global Error handlers
    @app.errorhandler(403)
    def forbidden(e):
        return render_template('errors/403.html'), 403

    @app.errorhandler(404)
    def page_not_found(e):
        return render_template('errors/404.html'), 404

    @app.errorhandler(500)
    def internal_server_error(e):
        return render_template('errors/500.html'), 500

    # Context processors
    @app.context_processor
    def inject_global_vars():
        return {
            'app_name': 'Panopticon AI',
            'current_year': 2026
        }

    return app


if __name__ == '__main__':
    app = create_app('development')
    with app.app_context():
        db.create_all()
    app.run(host='127.0.0.1', port=5000, debug=True)
