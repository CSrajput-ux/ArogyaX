"""
ArogyaX Healthcare Platform — Patient Portal & Primary Workflow Routes
Blueprint: patient
Handles: Home / Dashboard, Specialists Directory, Doctor Profile, Booking, Telehealth, Pharmacy, Vault, Profile
"""

import os
from datetime import datetime
from bson.objectid import ObjectId
from flask import Blueprint, render_template, request, redirect, url_for, session, flash, send_file
import backend.database as db_module
from backend.middleware import login_required, get_current_user
from backend.config import Config
from backend.security import allowed_file, sanitize_safe_filename, sanitize_text
from backend.services.mail_service import send_mail_safe

patient_bp = Blueprint('patient', __name__)

@patient_bp.route('/', methods=['GET', 'POST'])
def index():
    username = None
    if 'user_id' in session:
        user = get_current_user()
        if user:
            username = user['username']
            if user['role'] == 'admin':
                return redirect(url_for('admin.admin_dashboard'))
            if user['role'] == 'doctor':
                appts = list(db_module.appointments_col.find({'type_of_doctor': user.get('type_of_doctor')})) if db_module.appointments_col is not None else []
                for a in appts:
                    a['_id'] = str(a['_id'])
                user_str = dict(user)
                user_str['_id'] = str(user['_id'])
                return render_template('doctor-dashboard.html', username=username, appointments=appts, doctor=user_str)
            else:
                user_appts = list(db_module.appointments_col.find({'user_id': user['_id']})) if db_module.appointments_col is not None else []
                for a in user_appts:
                    a['_id'] = str(a['_id'])
                assessments = list(db_module.assessments_col.find({'patientId': str(user['_id'])}).sort('createdAt', -1)) if db_module.assessments_col is not None else []
                for a in assessments:
                    a['_id'] = str(a['_id'])
                user_str = dict(user)
                user_str['_id'] = str(user['_id'])
                return render_template('patient-dashboard.html', username=username, user=user_str, user_appointments=user_appts, assessments=assessments)
    return render_template('index.html')

@patient_bp.route('/doctors')
def doctors_directory():
    username = None
    role = 'patient'
    if 'user_id' in session:
        u = get_current_user()
        if u:
            username = u['username']
            role = u.get('role', 'patient')
            
    specialization = request.args.get('specialization', '')
    query = {'role': 'doctor', 'is_active': True}
    if specialization and specialization != 'All':
        query['type_of_doctor'] = specialization
        
    doctors = list(db_module.users_col.find(query)) if db_module.users_col is not None else []
    for d in doctors:
        d['_id'] = str(d['_id'])
        
    specs_raw = db_module.users_col.distinct('type_of_doctor', {'role': 'doctor'}) if db_module.users_col is not None else []
    specializations = [s for s in specs_raw if s]
    if not specializations:
        specializations = ['General Physician', 'Cardiologist', 'Neurologist', 'Dermatologist', 'Orthopedic', 'Pediatrician', 'Ophthalmologist']
        
    return render_template('doctors.html', doctors=doctors, username=username, role=role,
                           specializations=specializations, current_specialization=specialization)

@patient_bp.route('/doctor-profile/<doctor_id>')
def doctor_profile(doctor_id):
    username = None
    role = 'patient'
    if 'user_id' in session:
        u = get_current_user()
        if u:
            username = u['username']
            role = u.get('role', 'patient')
            
    doctor = db_module.get_user_by_id(doctor_id) if db_module.users_col is not None else None
    if not doctor:
        # Fallback dummy doctor for demo if ID not found
        doctor = {
            '_id': doctor_id,
            'username': 'dr_priya',
            'type_of_doctor': 'Cardiologist',
            'bio': 'Senior Cardiologist with 10+ years of clinical excellence in non-invasive cardiology and preventive heart care.',
            'years_of_experience': 10,
            'consultation_fee': 800,
            'availability': 'Mon - Fri, 10:00 AM - 5:00 PM',
            'email': 'priya.sharma@arogyax.com',
            'phone': '+91 98765 43210'
        }
    else:
        doctor['_id'] = str(doctor['_id'])
    return render_template('doctor-profile.html', doctor=doctor, username=username, role=role)

@patient_bp.route('/order-medicines')
@login_required
def order_medicines():
    user = get_current_user()
    username = user['username'] if user else 'Patient'
    role = user.get('role', 'patient') if user else 'patient'
    user_str = dict(user) if user else {}
    if user_str and '_id' in user_str:
        user_str['_id'] = str(user_str['_id'])
    return render_template('order-medicines.html', username=username, role=role, user=user_str)

@patient_bp.route('/book-appointment', methods=['GET', 'POST'])
@login_required
def book_appointment():
    user = get_current_user()
    username = user['username']
    doctors = list(db_module.users_col.find({'role': 'doctor', 'is_active': True})) if db_module.users_col is not None else []
    for d in doctors:
        d['_id'] = str(d['_id'])

    if request.method == 'POST':
        name = sanitize_text(request.form.get('name', ''))
        age_str = request.form.get('age', '0')
        blood_group = sanitize_text(request.form.get('blood_group', ''))
        time_slot = sanitize_text(request.form.get('time_slot', ''))
        phone_number = sanitize_text(request.form.get('phone_number', ''))
        email = sanitize_text(request.form.get('email', ''))
        type_of_doctor = sanitize_text(request.form.get('type_of_doctor', ''))

        try:
            age = max(1, min(120, int(age_str)))
        except ValueError:
            age = 30

        appt_data = {
            'name': name,
            'age': age,
            'blood_group': blood_group,
            'time_slot': time_slot,
            'phone_number': phone_number,
            'email': email,
            'type_of_doctor': type_of_doctor,
            'status': 'Pending',
            'user_id': user['_id'],
            'created_at': datetime.utcnow()
        }
        if db_module.appointments_col is not None:
            db_module.appointments_col.insert_one(appt_data)

            doctor_obj = db_module.users_col.find_one({'type_of_doctor': type_of_doctor, 'role': 'doctor'})
            if doctor_obj:
                send_mail_safe('New Appointment Request', doctor_obj.get('email'),
                    f"Hello Dr. {doctor_obj['username']},\n\nNew consultation booking from {name}. Please log in to approve.")

        flash('Appointment booked successfully! Our clinic will notify you upon confirmation.', 'success')
        return redirect(url_for('patient.index'))

    return render_template('book-appointment.html', doctors=doctors, username=username)

@patient_bp.route('/videocall')
@login_required
def videocall_direct():
    user = get_current_user()
    if not user:
        return redirect(url_for('auth.login'))
    
    appt = None
    if db_module.appointments_col is not None:
        if user.get('role') == 'patient':
            appt = db_module.appointments_col.find_one({'user_id': user['_id'], 'status': 'Approved'})
        else:
            appt = db_module.appointments_col.find_one({'type_of_doctor': user.get('type_of_doctor'), 'status': 'Approved'})
    
    appt_id = str(appt['_id']) if appt else 'telehealth-session-live'
    doctor_name = "Dr. Priya Sharma"
    specialization = appt.get('type_of_doctor', 'Senior Cardiologist') if appt else 'Senior Specialist'
    user_str = dict(user)
    user_str['_id'] = str(user['_id'])
    return render_template('videocall.html', username=user['username'], appointment_id=appt_id, role=user.get('role', 'patient'), user=user_str, doctor_name=doctor_name, specialization=specialization, appointment=appt)

@patient_bp.route('/videocall/<appointment_id>')
@login_required
def videocall(appointment_id):
    user = get_current_user()
    if not user:
        return redirect(url_for('auth.login'))
        
    try:
        appt = db_module.appointments_col.find_one({'_id': ObjectId(appointment_id)}) if db_module.appointments_col is not None else None
    except Exception:
        flash('Appointment not found.', 'error')
        return redirect(url_for('patient.index'))
        
    if not appt or appt.get('status') != 'Approved':
        flash('Video call is only available for confirmed approved appointments.', 'error')
        return redirect(url_for('patient.index'))
        
    # Security check for authorization
    if user.get('role') == 'patient':
        if str(appt['user_id']) != str(user['_id']):
            flash('Unauthorized access.', 'error')
            return redirect(url_for('patient.index'))
    elif user.get('role') == 'doctor':
        if appt.get('type_of_doctor') != user.get('type_of_doctor'):
             flash('Unauthorized access.', 'error')
             return redirect(url_for('patient.index'))
             
    user_str = dict(user)
    user_str['_id'] = str(user['_id'])
    return render_template('videocall.html', username=user['username'], appointment_id=appointment_id, role=user.get('role', 'patient'), user=user_str, doctor_name=f"Dr. {user['username']}", specialization=appt.get('type_of_doctor'), appointment=appt)

@patient_bp.route('/vault', methods=['GET', 'POST'])
@login_required
def vault():
    user = get_current_user()
    if not user or user.get('role') != 'patient':
        return redirect(url_for('patient.index'))
    
    if request.method == 'POST':
        if 'record_file' in request.files:
            file = request.files['record_file']
            record_title = sanitize_text(request.form.get('title', 'Untitled Medical Record'))
            if file and allowed_file(file.filename):
                os.makedirs(Config.VAULT_FOLDER, exist_ok=True)
                filename = sanitize_safe_filename(f"vault_{user['_id']}", file.filename)
                filepath = os.path.join(Config.VAULT_FOLDER, filename)
                file.save(filepath)
                
                record_entry = {
                    'title': record_title,
                    'filename': filename,
                    'filepath': f"uploads/profile_photos/vault/{filename}",
                    'uploaded_at': datetime.utcnow()
                }
                db_module.users_col.update_one({'_id': user['_id']}, {'$push': {'records': record_entry}})
                flash('Medical record successfully secured in your Health Vault!', 'success')
                return redirect(url_for('patient.vault'))
                
    user = get_current_user() # re-fetch
    user_str = dict(user)
    user_str['_id'] = str(user['_id'])
    
    assessments = list(db_module.assessments_col.find({'patientId': str(user['_id'])}).sort('createdAt', -1)) if db_module.assessments_col is not None else []
    for a in assessments:
        a['_id'] = str(a['_id'])
    
    return render_template('vault.html', user=user_str, username=user['username'], role='patient', assessments=assessments)

@patient_bp.route('/profile')
@login_required
def profile():
    user = get_current_user()
    username = user['username']
    email = user['email']
    user_appts = list(db_module.appointments_col.find({'user_id': user['_id']})) if db_module.appointments_col is not None else []
    for a in user_appts:
        a['_id'] = str(a['_id'])
    return render_template('patient-profile.html', username=username, Email=email, user_appointments=user_appts)

@patient_bp.route('/view-prescription-patient/<appointment_id>')
@login_required
def view_prescription_patient(appointment_id):
    user = get_current_user()
    appt = db_module.appointments_col.find_one({'_id': ObjectId(appointment_id)}) if db_module.appointments_col is not None else None
    
    # Strict Authorization Check: Only the appointment's patient can download
    if appt and str(appt.get('user_id')) == str(user['_id']) and appt.get('status') == 'Prescribed':
        filepath = appt.get('prescription_file')
        # Check both full and relative paths
        if filepath and not os.path.isabs(filepath):
            filepath = os.path.join(Config.STATIC_FOLDER, filepath)
        if filepath and os.path.exists(filepath):
            return send_file(filepath, as_attachment=True)
        else:
            flash('Prescription file not found on server.', 'error')
    else:
        flash('Unauthorized access to medical record.', 'error')
    return redirect(url_for('patient.index'))
