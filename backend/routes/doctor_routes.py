"""
ArogyaX Healthcare Platform — Doctor Clinical Portal Routes
Blueprint: doctor
Handles: Clinical Dashboard, Patient Queue, Approvals, Prescriptions, Profile Management, Patient Records Review
"""

import os
from datetime import datetime
from bson.objectid import ObjectId
from flask import Blueprint, render_template, request, redirect, url_for, session, flash, send_file
import backend.database as db_module
from backend.middleware import login_required, doctor_required, get_current_user
from backend.config import Config
from backend.security import allowed_file, sanitize_safe_filename, sanitize_text
from backend.services.pdf_service import generate_prescription_pdf
from backend.services.mail_service import send_mail_safe

doctor_bp = Blueprint('doctor', __name__)

@doctor_bp.route('/doctor-patients')
@login_required
@doctor_required
def doctor_patients():
    user = get_current_user()
    username = user['username']
    appts = list(db_module.appointments_col.find({'type_of_doctor': user.get('type_of_doctor')})) if db_module.appointments_col is not None else []
    for a in appts:
        a['_id'] = str(a['_id'])
    user_str = dict(user)
    user_str['_id'] = str(user['_id'])
    return render_template('doctor-patients.html', doctor=user_str, appointments=appts, username=username, file_list=[])

@doctor_bp.route('/approve-appointment/<appointment_id>')
@login_required
@doctor_required
def approve_appointment(appointment_id):
    doctor = get_current_user()
    appt = db_module.appointments_col.find_one({'_id': ObjectId(appointment_id)}) if db_module.appointments_col is not None else None
    if appt and appt.get('type_of_doctor') == doctor.get('type_of_doctor'):
        db_module.appointments_col.update_one({'_id': ObjectId(appointment_id)}, {'$set': {'status': 'Approved'}})
        send_mail_safe('Appointment Approved — ArogyaX', appt.get('email'),
            f"Hello {appt['name']},\n\nYour consultation with Dr. {doctor['username']} has been approved. You can now join the HD video call or attend in-clinic.")
        flash('Appointment approved successfully.', 'success')
    else:
        flash('Appointment not found or unauthorized department.', 'error')
    return redirect(url_for('patient.index'))

@doctor_bp.route('/prescribe-medicine/<appointment_id>', methods=['GET', 'POST'])
@login_required
@doctor_required
def prescribe_medicine(appointment_id):
    doctor = get_current_user()
    appt = db_module.appointments_col.find_one({'_id': ObjectId(appointment_id)}) if db_module.appointments_col is not None else None
    
    if not appt:
        flash('Appointment not found.', 'error')
        return redirect(url_for('doctor.doctor_patients'))

    available_medicines = [
        "Paracetamol 650mg", "Ibuprofen 400mg", "Amoxicillin 500mg",
        "Omeprazole 20mg", "Cetirizine 10mg", "Metformin 500mg",
        "Atorvastatin 10mg", "Amlodipine 5mg", "Azithromycin 500mg",
        "Vitamin D3 60000IU", "Vitamin C 500mg", "Pantoprazole 40mg"
    ]
    
    if request.method == 'POST':
        selected_medicines = request.form.getlist('medicines[]')
        advice_notes = sanitize_text(request.form.get('advice', ''))
        
        if not selected_medicines:
            flash('Please select at least one medicine to prescribe.', 'error')
            appt_str = dict(appt)
            appt_str['_id'] = str(appt['_id'])
            return render_template('prescribe-medicine.html', appointment=appt_str, available_medicines=available_medicines)
            
        pdf_rel_path = generate_prescription_pdf(
            appointment_id=appointment_id,
            appt=appt,
            doctor_name=doctor['username'],
            doctor_spec=doctor.get('type_of_doctor', 'Physician'),
            selected_medicines=selected_medicines,
            advice_notes=advice_notes
        )
        
        db_module.appointments_col.update_one(
            {'_id': ObjectId(appointment_id)},
            {'$set': {'status': 'Prescribed', 'prescription_file': pdf_rel_path}}
        )
        flash('Digital prescription generated and saved to patient vault successfully!', 'success')
        return redirect(url_for('doctor.doctor_patients'))

    appt_str = dict(appt)
    appt_str['_id'] = str(appt['_id'])
    return render_template('prescribe-medicine.html', appointment=appt_str, available_medicines=available_medicines)

@doctor_bp.route('/view-prescription/<appointment_id>')
@login_required
@doctor_required
def view_prescription(appointment_id):
    doctor = get_current_user()
    appt = db_module.appointments_col.find_one({'_id': ObjectId(appointment_id)}) if db_module.appointments_col is not None else None
    if appt and appt.get('type_of_doctor') == doctor.get('type_of_doctor') and appt.get('status') == 'Prescribed':
        filepath = appt.get('prescription_file')
        if filepath and not os.path.isabs(filepath):
            filepath = os.path.join(Config.STATIC_FOLDER, filepath)
        if filepath and os.path.exists(filepath):
            return send_file(filepath, as_attachment=True)
        else:
            flash('Prescription file not found on server.', 'error')
    else:
        flash('Unauthorized access to medical record.', 'error')
    return redirect(url_for('doctor.doctor_patients'))

@doctor_bp.route('/doctor-profile-edit', methods=['GET', 'POST'])
@login_required
@doctor_required
def doctor_profile_edit():
    user = get_current_user()
    if request.method == 'POST':
        try:
            years_exp = int(request.form.get('years_of_experience', 0) or 0)
        except ValueError:
            years_exp = 0
            
        try:
            consult_fee = int(request.form.get('consultation_fee', 0) or 0)
        except ValueError:
            consult_fee = 0

        updates = {
            'bio': sanitize_text(request.form.get('bio', ''), max_len=1000),
            'years_of_experience': max(0, min(60, years_exp)),
            'consultation_fee': max(0, min(50000, consult_fee)),
            'phone': sanitize_text(request.form.get('phone', '')),
            'email': sanitize_text(request.form.get('email', user['email'])),
            'city': sanitize_text(request.form.get('city', '')),
            'consultation_type': request.form.getlist('consultation_type'),
            'availability': {
                'Monday': sanitize_text(request.form.get('avail_monday', '')),
                'Tuesday': sanitize_text(request.form.get('avail_tuesday', '')),
                'Wednesday': sanitize_text(request.form.get('avail_wednesday', '')),
                'Thursday': sanitize_text(request.form.get('avail_thursday', '')),
                'Friday': sanitize_text(request.form.get('avail_friday', '')),
                'Saturday': sanitize_text(request.form.get('avail_saturday', ''))
            }
        }
        
        # Location / Geospatial Data
        lat_str = request.form.get('latitude')
        lng_str = request.form.get('longitude')
        if lat_str and lng_str:
            try:
                lat = float(lat_str)
                lng = float(lng_str)
                updates['location'] = {
                    "type": "Point",
                    "coordinates": [lng, lat]
                }
            except ValueError:
                pass
                
        if request.form.get('type_of_doctor'):
            updates['type_of_doctor'] = sanitize_text(request.form.get('type_of_doctor'))

        # Secure profile photo upload
        if 'profile_photo' in request.files:
            file = request.files['profile_photo']
            if file and file.filename and allowed_file(file.filename):
                os.makedirs(Config.UPLOAD_FOLDER, exist_ok=True)
                filename = sanitize_safe_filename(f"doctor_{user['_id']}", file.filename)
                filepath = os.path.join(Config.UPLOAD_FOLDER, filename)
                file.save(filepath)
                updates['profile_photo'] = f"uploads/profile_photos/{filename}"

        db_module.users_col.update_one({'_id': user['_id']}, {'$set': updates})
        flash('Practice profile updated successfully!', 'success')
        return redirect(url_for('doctor.doctor_profile_edit'))

    user = get_current_user()
    user_str = dict(user)
    user_str['_id'] = str(user['_id'])
    return render_template('doctor-profile-edit.html', user=user_str, doctor=user_str, username=user['username'])

@doctor_bp.route('/view-records/<patient_id>')
@login_required
@doctor_required
def view_records(patient_id):
    doctor = get_current_user()
    patient = db_module.get_user_by_id(patient_id)
    if not patient:
        flash('Patient medical record not found.', 'error')
        return redirect(url_for('doctor.doctor_patients'))
        
    patient_str = dict(patient)
    patient_str['_id'] = str(patient['_id'])
    
    doctor_str = dict(doctor)
    doctor_str['_id'] = str(doctor['_id'])
    
    return render_template('doctor-view-records.html', patient=patient_str, doctor=doctor_str, username=doctor['username'], role='doctor', user=doctor_str)
