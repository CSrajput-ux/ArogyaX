"""
ArogyaX Healthcare Platform — Health Articles & Public Informational Routes
Blueprint: blog
Handles: Health Literacy Articles, Clinical Research Insights, and Privacy / Security Policies
"""

from flask import Blueprint, render_template, session
from backend.middleware import get_current_user

blog_bp = Blueprint('blog', __name__)

@blog_bp.route('/policy')
def policy():
    return render_template('privacy-policy.html')

@blog_bp.route('/Transforming_Healthcare')
def Transforming_Healthcare():
    u = get_current_user() if 'user_id' in session else None
    username = u['username'] if u else None
    return render_template('blog_Transforming Healthcare.html', username=username)

@blog_bp.route('/Holistic_Health')
def Holistic_Health():
    u = get_current_user() if 'user_id' in session else None
    username = u['username'] if u else None
    return render_template('blog_Holistic Health.html', username=username)

@blog_bp.route('/Nourishing_Body')
def Nourishing_Body():
    u = get_current_user() if 'user_id' in session else None
    username = u['username'] if u else None
    return render_template('blog_Nourishing_Body.html', username=username)

@blog_bp.route('/Importance_of_Games')
def Importance_of_Games():
    u = get_current_user() if 'user_id' in session else None
    username = u['username'] if u else None
    return render_template('blog_Importance_of_Games.html', username=username)
