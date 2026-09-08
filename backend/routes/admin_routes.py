"""
ArogyaX Healthcare Platform — Hospital Admin Management Routes
Blueprint: admin
Handles: Administrative Authentication, Platform KPI Dashboard, Staff Management, Patient Directory, Appointment Auditing, and Demo Data Seeding
"""

from datetime import datetime
from bson.objectid import ObjectId
from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from flask_bcrypt import generate_password_hash, check_password_hash
import backend.database as db_module
from backend.middleware import admin_required, get_current_user
from backend.security import sanitize_text

admin_bp = Blueprint('admin', __name__)

@admin_bp.route('/admin')
def admin_root():
    return redirect(url_for('admin.admin_login'))

@admin_bp.route('/admin-login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = sanitize_text(request.form.get('username', ''))
        password = request.form.get('password', '')
        
        if db_module.users_col is None:
            flash('Database not connected. Please verify MONGO_URI in configuration.', 'error')
            return render_template('admin-login.html')
            
        user = db_module.users_col.find_one({'username': username, 'role': 'admin'})
        if user:
            pwd_matches = False
            try:
                pwd_matches = check_password_hash(user['password'], password)
            except Exception:
                pwd_matches = (user['password'] == password)
                
            if pwd_matches:
                session['user_id'] = str(user['_id'])
                session['role'] = 'admin'
                return redirect(url_for('admin.admin_dashboard'))
                
        flash('Invalid administrative credentials.', 'error')
    return render_template('admin-login.html')

@admin_bp.route('/admin-dashboard')
@admin_required
def admin_dashboard():
    admin_user = get_current_user()
    
    total_doctors = db_module.users_col.count_documents({'role': 'doctor'}) if db_module.users_col is not None else 0
    total_patients = db_module.users_col.count_documents({'role': 'patient'}) if db_module.users_col is not None else 0
    total_users = total_doctors + total_patients
    
    total_appointments = db_module.appointments_col.count_documents({}) if db_module.appointments_col is not None else 0
    pending = db_module.appointments_col.count_documents({'status': 'Pending'}) if db_module.appointments_col is not None else 0
    approved = db_module.appointments_col.count_documents({'status': 'Approved'}) if db_module.appointments_col is not None else 0
    prescribed = db_module.appointments_col.count_documents({'status': 'Prescribed'}) if db_module.appointments_col is not None else 0
    
    all_doctors = list(db_module.users_col.find({'role': 'doctor'})) if db_module.users_col is not None else []
    all_patients = list(db_module.users_col.find({'role': 'patient'})) if db_module.users_col is not None else []
    all_appointments = list(db_module.appointments_col.find().sort('_id', -1)) if db_module.appointments_col is not None else []
    
    # Format IDs and compute stats
    for doc in all_doctors + all_patients:
        doc_id_str = str(doc['_id'])
        doc['_id'] = doc_id_str
        doc['appointments_count'] = db_module.appointments_col.count_documents({'user_id': ObjectId(doc_id_str)}) if db_module.appointments_col is not None else 0
        
    for appt in all_appointments:
        appt['_id'] = str(appt['_id'])
        
    return render_template('admin.html',
        admin_user=admin_user, total_users=total_users,
        total_doctors=total_doctors, total_patients=total_patients,
        total_appointments=total_appointments, pending=pending,
        approved=approved, prescribed=prescribed,
        all_doctors=all_doctors, all_patients=all_patients,
        all_appointments=all_appointments
    )

@admin_bp.route('/admin/delete-user/<user_id>', methods=['POST'])
@admin_required
def admin_delete_user(user_id):
    if db_module.users_col is not None:
        user = db_module.users_col.find_one({'_id': ObjectId(user_id)})
        if db_module.appointments_col is not None:
            db_module.appointments_col.delete_many({'user_id': ObjectId(user_id)})
        db_module.users_col.delete_one({'_id': ObjectId(user_id)})
        flash(f"User account '{user.get('username','?')}' and related medical records deleted.", 'success')
    return redirect(url_for('admin.admin_dashboard'))

@admin_bp.route('/admin/toggle-user/<user_id>', methods=['POST'])
@admin_required
def admin_toggle_user(user_id):
    if db_module.users_col is not None:
        user = db_module.users_col.find_one({'_id': ObjectId(user_id)})
        if user:
            new_status = not user.get('is_active', True)
            db_module.users_col.update_one({'_id': ObjectId(user_id)}, {'$set': {'is_active': new_status}})
            action = 'activated' if new_status else 'deactivated'
            flash(f"User '{user.get('username')}' has been successfully {action}.", 'success')
    return redirect(url_for('admin.admin_dashboard'))

@admin_bp.route('/admin/logout')
def admin_logout():
    session.clear()
    return redirect(url_for('admin.admin_login'))

@admin_bp.route('/seed-demo')
def seed_demo():
    if db_module.users_col is None:
        flash('MongoDB not connected. Fill MONGO_URI in .env first.', 'error')
        return redirect(url_for('admin.admin_login'))

    # 1. Admin Account
    if not db_module.users_col.find_one({'username': 'admin'}):
        db_module.users_col.insert_one({
            'username': 'admin', 'email': 'admin@arogyax.com',
            'password': generate_password_hash('admin123').decode('utf-8'),
            'role': 'admin', 'phone': '+91 9000000001', 'is_active': True,
            'created_at': datetime.utcnow()
        })

    # 2. Demo Doctors
    doctors = [
        {'username': 'dr_anika', 'email': 'anika@arogyax.com', 'type_of_doctor': 'Cardiologist',
         'bio': 'Dr. Anika Sharma is a senior cardiologist with over 12 years of experience in diagnosing and treating complex heart conditions. She specializes in interventional cardiology and heart failure management.',
         'years_of_experience': 12, 'consultation_fee': 800,
         'availability': 'Mon, Wed, Fri — 10:00 AM to 5:00 PM', 'phone': '+91 9000000002'},
        {'username': 'dr_rahul', 'email': 'rahul@arogyax.com', 'type_of_doctor': 'Neurologist',
         'bio': 'Dr. Rahul Mehta is a leading neurologist specializing in epilepsy, stroke management, and neurodegenerative diseases. He has published 30+ research papers in leading medical journals.',
         'years_of_experience': 15, 'consultation_fee': 1000,
         'availability': 'Tue, Thu, Sat — 9:00 AM to 3:00 PM', 'phone': '+91 9000000003'},
        {'username': 'dr_priya', 'email': 'priya@arogyax.com', 'type_of_doctor': 'Ophthalmologist',
         'bio': 'Dr. Priya Nair is an expert ophthalmologist specializing in cataract surgery, retinal disorders, and LASIK procedures. She has performed over 5,000 successful eye surgeries.',
         'years_of_experience': 10, 'consultation_fee': 700,
         'availability': 'Mon to Fri — 11:00 AM to 6:00 PM', 'phone': '+91 9000000004'},
        {'username': 'dr_sandeep', 'email': 'sandeep@arogyax.com', 'type_of_doctor': 'Pulmonologist',
         'bio': 'Dr. Sandeep Kaur specializes in respiratory medicine and has extensive experience treating asthma, COPD, pneumonia, and lung cancer. He runs a dedicated pulmonary rehabilitation program.',
         'years_of_experience': 8, 'consultation_fee': 600,
         'availability': 'Mon, Tue, Thu — 12:00 PM to 7:00 PM', 'phone': '+91 9000000005'},
    ]
    for d in doctors:
        if not db_module.users_col.find_one({'username': d['username']}):
            d.update({
                'password': generate_password_hash('doctor123').decode('utf-8'),
                'role': 'doctor', 'profile_photo': None, 'is_active': True,
                'created_at': datetime.utcnow()
            })
            db_module.users_col.insert_one(d)

    # 3. Demo Patients
    patients = [
        {'username': 'john_patient', 'email': 'john@example.com', 'phone': '+91 9111111111'},
        {'username': 'priti_patient', 'email': 'priti@example.com', 'phone': '+91 9222222222'},
        {'username': 'karan_patient', 'email': 'karan@example.com', 'phone': '+91 9444444444'},
        {'username': 'sara_patient', 'email': 'sara@example.com', 'phone': '+91 9555555555'},
    ]
    patient_ids = {}
    for p in patients:
        existing = db_module.users_col.find_one({'username': p['username']})
        if not existing:
            result = db_module.users_col.insert_one({
                **p,
                'password': generate_password_hash('patient123').decode('utf-8'),
                'role': 'patient', 'is_active': True,
                'created_at': datetime.utcnow()
            })
            patient_ids[p['username']] = result.inserted_id
        else:
            patient_ids[p['username']] = existing['_id']

    # 4. Demo Appointments
    if db_module.appointments_col is not None and db_module.appointments_col.count_documents({}) == 0:
        demo_appts = [
            {'name': 'John Doe', 'age': 35, 'blood_group': 'O+', 'time_slot': '10:00 AM - 11:00 AM',
             'phone_number': '+91 9111111111', 'email': 'john@example.com',
             'type_of_doctor': 'Cardiologist', 'status': 'Approved',
             'user_id': patient_ids.get('john_patient'), 'created_at': datetime.utcnow()},
            {'name': 'Priti Sharma', 'age': 28, 'blood_group': 'B+', 'time_slot': '11:00 AM - 12:00 PM',
             'phone_number': '+91 9222222222', 'email': 'priti@example.com',
             'type_of_doctor': 'Ophthalmologist', 'status': 'Pending',
             'user_id': patient_ids.get('priti_patient'), 'created_at': datetime.utcnow()},
            {'name': 'Karan Singh', 'age': 42, 'blood_group': 'A+', 'time_slot': '02:00 PM - 03:00 PM',
             'phone_number': '+91 9444444444', 'email': 'karan@example.com',
             'type_of_doctor': 'Neurologist', 'status': 'Prescribed',
             'user_id': patient_ids.get('karan_patient'), 'prescription_file': None,
             'created_at': datetime.utcnow()},
            {'name': 'John Doe', 'age': 35, 'blood_group': 'O+', 'time_slot': '03:00 PM - 04:00 PM',
             'phone_number': '+91 9111111111', 'email': 'john@example.com',
             'type_of_doctor': 'Pulmonologist', 'status': 'Pending',
             'user_id': patient_ids.get('john_patient'), 'created_at': datetime.utcnow()},
        ]
        db_module.appointments_col.insert_many(demo_appts)

    flash('✅ Demo environment seeded successfully! Login: admin/admin123 | Doctor: dr_anika/doctor123 | Patient: john_patient/patient123', 'success')
    return redirect(url_for('admin.admin_login'))
