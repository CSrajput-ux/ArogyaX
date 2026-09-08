"""
ArogyaX Healthcare Platform — Authentication Routes
Blueprint: auth
Handles: Patient / Doctor Login, Patient Registration, Doctor Registration, Logout
"""

from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from flask_bcrypt import Bcrypt
from pymongo.errors import DuplicateKeyError
import backend.database as db_module
from backend.security import sanitize_text

auth_bp = Blueprint('auth', __name__)
bcrypt = Bcrypt()

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = sanitize_text(request.form.get('username', ''))
        password = request.form.get('password', '')

        if not username or not password:
            flash('Please enter both username and password.', 'error')
            return render_template('login.html')

        if db_module.users_col is None:
            flash('MongoDB not connected. Fill MONGO_URI in .env', 'error')
            return render_template('login.html')

        user = db_module.users_col.find_one({'username': username})
        if user:
            if user.get('role') == 'admin':
                flash('Please use the Admin Login portal.', 'error')
                return redirect(url_for('admin.admin_login'))

            if not user.get('is_active', True):
                flash('This account is currently deactivated. Please contact support.', 'error')
                return render_template('login.html')

            # Support both hashed and legacy plain-text passwords
            try:
                pwd_ok = bcrypt.check_password_hash(user['password'], password)
            except Exception:
                pwd_ok = (user['password'] == password)  # legacy fallback

            if pwd_ok:
                session.clear()
                session['user_id'] = str(user['_id'])
                session['role'] = user.get('role', 'patient')
                return redirect(url_for('patient.index'))

        flash('Invalid username or password. Please try again.', 'error')
    return render_template('login.html')

@auth_bp.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('patient.index'))

@auth_bp.route('/patient-register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = sanitize_text(request.form.get('username', ''))
        email = sanitize_text(request.form.get('email', ''))
        password = request.form.get('password', '')

        if not username or not email or not password:
            flash('All fields are required.', 'error')
            return render_template('patient-register.html')

        if len(password) < 6:
            flash('Password must be at least 6 characters long.', 'error')
            return render_template('patient-register.html')

        if db_module.users_col is None:
            flash('Database currently unavailable. Please try again later.', 'error')
            return render_template('patient-register.html')

        try:
            hashed = bcrypt.generate_password_hash(password).decode('utf-8')
            result = db_module.users_col.insert_one({
                'username': username,
                'email': email,
                'password': hashed,
                'role': 'patient',
                'is_active': True,
                'created_at': datetime.utcnow()
            })
            session.clear()
            session['user_id'] = str(result.inserted_id)
            session['role'] = 'patient'
            flash('Account created successfully! Welcome to ArogyaX.', 'success')
            return redirect(url_for('patient.index'))
        except DuplicateKeyError:
            flash('Username already taken. Please choose another.', 'error')
    return render_template('patient-register.html')

@auth_bp.route('/doctor-register', methods=['GET', 'POST'])
def doctor_register():
    if request.method == 'POST':
        username = sanitize_text(request.form.get('username', ''))
        email = sanitize_text(request.form.get('email', ''))
        password = request.form.get('password', '')
        type_of_doctor = sanitize_text(request.form.get('type_of_doctor', 'General Physician'))

        if not username or not email or not password:
            flash('All fields are required.', 'error')
            return render_template('doctor-register.html')

        if len(password) < 6:
            flash('Password must be at least 6 characters long.', 'error')
            return render_template('doctor-register.html')

        if db_module.users_col is None:
            flash('Database currently unavailable. Please try again later.', 'error')
            return render_template('doctor-register.html')

        try:
            hashed = bcrypt.generate_password_hash(password).decode('utf-8')
            result = db_module.users_col.insert_one({
                'username': username,
                'email': email,
                'password': hashed,
                'role': 'doctor',
                'type_of_doctor': type_of_doctor,
                'is_active': True,
                'created_at': datetime.utcnow()
            })
            session.clear()
            session['user_id'] = str(result.inserted_id)
            session['role'] = 'doctor'
            flash('Doctor account registered successfully!', 'success')
            return redirect(url_for('patient.index'))
        except DuplicateKeyError:
            flash('Username already taken. Please choose another.', 'error')
    return render_template('doctor-register.html')
