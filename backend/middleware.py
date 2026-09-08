"""
ArogyaX Healthcare Platform — Authentication & Authorization Middleware
Role-Based Access Control (RBAC): Patient, Doctor, Admin
"""

from functools import wraps
from flask import session, redirect, url_for, flash, request
from backend.database import get_user_by_id

def get_current_user():
    """Retrieve the currently authenticated user dictionary from session."""
    if 'user_id' not in session:
        return None
    return get_user_by_id(session['user_id'])

def login_required(f):
    """Requires the user to be logged in with a valid session."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('auth.login', next=request.path))
        user = get_current_user()
        if not user:
            session.clear()
            return redirect(url_for('auth.login', next=request.path))
        return f(*args, **kwargs)
    return decorated

def doctor_required(f):
    """Requires the user to be logged in with a verified Doctor role."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session or session.get('role') != 'doctor':
            flash('Access restricted to verified medical doctors.', 'error')
            return redirect(url_for('patient.index'))
        user = get_current_user()
        if not user or user.get('role') != 'doctor':
            session.clear()
            flash('Doctor authorization required.', 'error')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated

def admin_required(f):
    """Requires the user to be logged in with Administrator role."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session or session.get('role') != 'admin':
            flash('Access denied. Administrator privileges required.', 'error')
            return redirect(url_for('admin.admin_login'))
        user = get_current_user()
        if not user or user.get('role') != 'admin':
            session.clear()
            flash('Admin access required.', 'error')
            return redirect(url_for('admin.admin_login'))
        return f(*args, **kwargs)
    return decorated
