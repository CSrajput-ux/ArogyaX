"""
ArogyaX Healthcare Platform — Application Factory
Initializes Flask app, security middleware, database, services, error handlers, and blueprints.
"""

import os
from flask import Flask, render_template, request, jsonify, url_for, session, redirect
from flask_bcrypt import Bcrypt
from backend.config import Config
from backend.database import init_db
from backend.services.mail_service import init_mail
from backend.services.ml_service import init_ml
from backend.services.gemini_service import init_gemini

# Initialize core extensions
bcrypt = Bcrypt()

def create_app(config_class=Config):
    """
    Application Factory Pattern for ArogyaX.
    Sets up frontend templates, static folder, routes, and security filters.
    """
    app = Flask(
        __name__,
        template_folder=config_class.TEMPLATE_FOLDER,
        static_folder=config_class.STATIC_FOLDER
    )
    
    # Load configuration
    app.config.from_object(config_class)
    
    # Ensure critical runtime directories exist
    os.makedirs(config_class.UPLOAD_FOLDER, exist_ok=True)
    os.makedirs(config_class.PRESCRIPTIONS_FOLDER, exist_ok=True)
    os.makedirs(config_class.SCANS_FOLDER, exist_ok=True)
    os.makedirs(config_class.VAULT_FOLDER, exist_ok=True)
    
    # Initialize extensions and services
    bcrypt.init_app(app)
    init_mail(app)
    init_db(app)
    init_ml(app)
    init_gemini(app)
    
    # Register blueprints
    from backend.routes.auth_routes import auth_bp
    from backend.routes.patient_routes import patient_bp
    from backend.routes.doctor_routes import doctor_bp
    from backend.routes.ai_routes import ai_bp
    from backend.routes.admin_routes import admin_bp
    from backend.routes.blog_routes import blog_bp
    
    app.register_blueprint(patient_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(doctor_bp)
    app.register_blueprint(ai_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(blog_bp)
    
    # Context Processor for seamless backward-compatible url_for resolution
    @app.context_processor
    def utility_processor():
        def smart_url_for(endpoint, **values):
            try:
                return url_for(endpoint, **values)
            except Exception:
                for prefix in ['patient', 'auth', 'doctor', 'ai', 'admin', 'blog']:
                    try:
                        return url_for(f"{prefix}.{endpoint}", **values)
                    except Exception:
                        pass
                # Fallback to standard url_for to display clear error if unresolved
                return url_for(endpoint, **values)
        return dict(url_for=smart_url_for)
    
    # Security response headers middleware
    @app.after_request
    def set_security_headers(response):
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'SAMEORIGIN'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        return response
    
    # Custom Security Error Handlers
    @app.errorhandler(400)
    def bad_request_error(e):
        if request.path.startswith('/api/'):
            return jsonify({'error': 'Bad Request', 'message': str(e)}), 400
        return render_template('index.html'), 400

    @app.errorhandler(403)
    def forbidden_error(e):
        if request.path.startswith('/api/'):
            return jsonify({'error': 'Forbidden Access', 'message': str(e)}), 403
        return render_template('index.html'), 403

    @app.errorhandler(404)
    def not_found_error(e):
        if request.path.startswith('/api/'):
            return jsonify({'error': 'Resource Not Found'}), 404
        return render_template('index.html'), 404

    @app.errorhandler(413)
    def request_entity_too_large(e):
        if request.path.startswith('/api/'):
            return jsonify({'error': 'File Too Large (Maximum 10MB allowed)'}), 413
        return "Upload exceeds maximum allowed file size (10MB).", 413

    @app.errorhandler(500)
    def internal_server_error(e):
        if request.path.startswith('/api/'):
            return jsonify({'error': 'Internal Server Error'}), 500
        return render_template('index.html'), 500

    return app
