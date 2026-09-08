"""
ArogyaX Healthcare Platform — AI & Medical Intelligence Routes
Blueprint: ai
Handles: Disease Prediction (ML + Gemini AI), Vision Scans (MRI Brain Tumor, Chest X-Ray, Cataract Detection),
Health APIs, and Assessment Tracking
"""

import os
from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, session, jsonify, flash
import backend.database as db_module
from backend.middleware import login_required, get_current_user
from backend.config import Config
from backend.security import allowed_file, sanitize_safe_filename
from backend.services.ml_service import predict_disease_ml, symptoms_list, ML_MODEL_AVAILABLE
from backend.services.gemini_service import get_gemini_disease_explanation, analyze_scan_with_gemini, gemini_client

ai_bp = Blueprint('ai', __name__)

@ai_bp.route('/disease_predict', methods=['GET', 'POST'])
@login_required
def disease_predict():
    user = get_current_user()
    username = user['username'] if user else 'Patient'
    role = user.get('role', 'patient') if user else 'patient'
    user_str = dict(user) if user else {}
    if user_str and '_id' in user_str:
        user_str['_id'] = str(user_str['_id'])
        
    chart_data = {}
    gemini_explanation = None
    disease = None
    confidence_score = None
    selected_symptoms = []

    if request.method == 'POST' and ML_MODEL_AVAILABLE:
        for s in ['Symptom1', 'Symptom2', 'Symptom3', 'Symptom4', 'Symptom5']:
            val = request.form.get(s, '')
            if val and val not in selected_symptoms:
                selected_symptoms.append(val)
        if selected_symptoms:
            disease, confidence_score = predict_disease_ml(selected_symptoms)
            chart_data = {'disease': disease, 'confidence_score': confidence_score}
            # Gemini AI Clinical Explanation
            gemini_explanation = get_gemini_disease_explanation(disease, selected_symptoms)

    return render_template('disease_predict.html',
        symptoms=symptoms_list, disease=disease, chart_data=chart_data,
        confidence_score=confidence_score, username=username,
        gemini_explanation=gemini_explanation,
        gemini_enabled=gemini_client is not None,
        selected_symptoms=selected_symptoms,
        role=role, user=user_str)

@ai_bp.route('/medical-imaging')
@login_required
def medical_imaging():
    user = get_current_user()
    username = user['username'] if user else 'Patient'
    role = user.get('role', 'patient') if user else 'patient'
    user_str = dict(user) if user else {}
    if user_str and '_id' in user_str:
        user_str['_id'] = str(user_str['_id'])
    return render_template('medical-imaging.html', username=username, role=role, user=user_str)

@ai_bp.route('/braintumor', methods=['GET', 'POST'])
@login_required
def braintumor():
    user = get_current_user()
    username = user['username'] if user else 'Patient'
    role = user.get('role', 'patient') if user else 'patient'
    user_str = dict(user) if user else {}
    if user_str and '_id' in user_str:
        user_str['_id'] = str(user_str['_id'])
        
    gemini_result = None
    if request.method == 'POST' and 'scan_image' in request.files:
        file = request.files['scan_image']
        if file and allowed_file(file.filename):
            scan_dir = os.path.join(Config.UPLOAD_FOLDER, 'scans')
            os.makedirs(scan_dir, exist_ok=True)
            filename = sanitize_safe_filename(f"mri_{user['_id']}", file.filename)
            filepath = os.path.join(scan_dir, filename)
            file.save(filepath)
            gemini_result = analyze_scan_with_gemini(filepath, 'brain')
        else:
            flash('Please upload a valid medical image (PNG, JPG, JPEG, WEBP).', 'error')
            
    return render_template('brain-tumor.html', username=username, role=role, user=user_str,
                           gemini_result=gemini_result, gemini_enabled=gemini_client is not None)

@ai_bp.route('/lung', methods=['GET', 'POST'])
@login_required
def lung():
    user = get_current_user()
    username = user['username'] if user else 'Patient'
    role = user.get('role', 'patient') if user else 'patient'
    user_str = dict(user) if user else {}
    if user_str and '_id' in user_str:
        user_str['_id'] = str(user_str['_id'])
        
    gemini_result = None
    if request.method == 'POST' and 'scan_image' in request.files:
        file = request.files['scan_image']
        if file and allowed_file(file.filename):
            scan_dir = os.path.join(Config.UPLOAD_FOLDER, 'scans')
            os.makedirs(scan_dir, exist_ok=True)
            filename = sanitize_safe_filename(f"xray_{user['_id']}", file.filename)
            filepath = os.path.join(scan_dir, filename)
            file.save(filepath)
            gemini_result = analyze_scan_with_gemini(filepath, 'lung')
        else:
            flash('Please upload a valid chest X-ray image (PNG, JPG, JPEG, WEBP).', 'error')
            
    return render_template('lung.html', username=username, role=role, user=user_str,
                           gemini_result=gemini_result, gemini_enabled=gemini_client is not None)

@ai_bp.route('/cataract', methods=['GET', 'POST'])
@login_required
def cataract():
    user = get_current_user()
    username = user['username'] if user else 'Patient'
    role = user.get('role', 'patient') if user else 'patient'
    user_str = dict(user) if user else {}
    if user_str and '_id' in user_str:
        user_str['_id'] = str(user_str['_id'])
        
    gemini_result = None
    if request.method == 'POST' and 'scan_image' in request.files:
        file = request.files['scan_image']
        if file and allowed_file(file.filename):
            scan_dir = os.path.join(Config.UPLOAD_FOLDER, 'scans')
            os.makedirs(scan_dir, exist_ok=True)
            filename = sanitize_safe_filename(f"cataract_{user['_id']}", file.filename)
            filepath = os.path.join(scan_dir, filename)
            file.save(filepath)
            gemini_result = analyze_scan_with_gemini(filepath, 'cataract')
        else:
            flash('Please upload a valid ocular scan image (PNG, JPG, JPEG, WEBP).', 'error')
            
    return render_template('cataract.html', username=username, role=role, user=user_str,
                           gemini_result=gemini_result, gemini_enabled=gemini_client is not None)

@ai_bp.route('/api/health')
def health_check():
    return jsonify({
        'status': 'ok',
        'mongodb': 'connected' if db_module.db is not None else 'disconnected',
        'gemini_ai': 'connected' if gemini_client is not None else 'not configured',
        'ml_model': 'loaded' if ML_MODEL_AVAILABLE else 'unavailable',
    })

@ai_bp.route('/api/save_assessment', methods=['POST'])
@login_required
def save_assessment():
    user = get_current_user()
    if not user:
        return jsonify({'error': 'Unauthorized'}), 401
    
    if db_module.assessments_col is None:
        return jsonify({'error': 'Database service currently unavailable'}), 500

    data = request.json or {}
    assessment = {
        'patientId': str(user['_id']),
        'assessmentType': data.get('assessmentType', 'Unknown'),
        'date': datetime.now().strftime("%Y-%m-%d"),
        'symptoms': data.get('symptoms', []),
        'inputData': data.get('inputData', ''),
        'result': data.get('result', ''),
        'confidence': data.get('confidence', 0),
        'riskLevel': data.get('riskLevel', 'Unknown'),
        'recommendations': data.get('recommendations', ''),
        'createdAt': datetime.now()
    }
    
    try:
        db_module.assessments_col.insert_one(assessment)
        return jsonify({'success': True, 'message': 'Health assessment securely archived in vault'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
