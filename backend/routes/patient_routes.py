"""
ArogyaX Healthcare Platform — Patient Portal & Primary Workflow Routes
Blueprint: patient
Handles: Home / Dashboard, Specialists Directory, Doctor Profile, Booking, Telehealth, Pharmacy, Vault, Profile
"""

import os
import random
import string
from datetime import datetime
from bson.objectid import ObjectId
from flask import Blueprint, render_template, request, redirect, url_for, session, flash, send_file, jsonify
import backend.database as db_module
from backend.middleware import login_required, get_current_user
from backend.config import Config
from backend.security import allowed_file, sanitize_safe_filename, sanitize_text
from backend.services.mail_service import send_mail_safe

patient_bp = Blueprint('patient', __name__)

# ── Specialty Code Map for Case ID generation ────────────────────────────────
SPECIALTY_CODES = {
    'Cardiologist': 'CARD',
    'Neurologist': 'NEUR',
    'Dermatologist': 'DERM',
    'Orthopedic': 'ORTH',
    'Pediatrician': 'PEDI',
    'Ophthalmologist': 'OPTH',
    'General Physician': 'GENP',
    'Gynecologist': 'GYNO',
    'Oncologist': 'ONCO',
    'Psychiatrist': 'PSYC',
    'Pulmonologist': 'PULM',
    'Endocrinologist': 'ENDO',
    'Gastroenterologist': 'GAST',
    'Rheumatologist': 'RHEU',
    'Nephrologist': 'NEPH',
    'Urologist': 'UROL',
    'ENT Specialist': 'ENTS',
    'Radiologist': 'RADI',
}

def generate_case_id(specialty):
    """Generate unique Case ID like AX-CARD-10245."""
    code = SPECIALTY_CODES.get(specialty, 'GENP')
    number = ''.join(random.choices(string.digits, k=5))
    return f"AX-{code}-{number}"


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
                # Redirect doctor to upgraded clinical dashboard
                return redirect(url_for('clinical.doctor_dashboard'))
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

@patient_bp.route('/api/doctors/search')
def api_search_doctors():
    lat = request.args.get('lat', type=float)
    lng = request.args.get('lng', type=float)
    specialty = request.args.get('specialty', '')
    radius = request.args.get('radius', type=int, default=5000) # Initial radius 5km

    query = {'role': 'doctor', 'is_active': True}
    if specialty and specialty != 'All':
        query['type_of_doctor'] = specialty

    # Progressive radius search
    radii = [radius, 15000, 30000, 75000]
    found_doctors = []
    current_radius = 0

    if lat is not None and lng is not None:
        for r in radii:
            geo_query = query.copy()
            geo_query['location'] = {
                '$near': {
                    '$geometry': {
                        'type': 'Point',
                        'coordinates': [lng, lat]
                    },
                    '$maxDistance': r
                }
            }
            try:
                found_doctors = list(db_module.users_col.find(geo_query))
                if found_doctors:
                    current_radius = r
                    break
            except Exception as e:
                print(f"Geo search error: {e}")
                found_doctors = list(db_module.users_col.find(query))
                break
    else:
        # Fallback if no location provided
        found_doctors = list(db_module.users_col.find(query))

    # Ranking logic
    ranked_doctors = []
    for d in found_doctors:
        d['_id'] = str(d['_id'])
        score = 0
        
        # 1. Experience (1 point per year, max 30)
        exp = int(d.get('years_of_experience', 0))
        score += min(exp, 30) * 1.5
        
        # 2. Rating (Multiply by 5)
        rating = float(d.get('rating', 4.0)) # Default 4.0 if not set
        score += rating * 5
        
        d['score'] = score
        ranked_doctors.append(d)
        
    # Sort by score descending
    ranked_doctors.sort(key=lambda x: x['score'], reverse=True)
    
    return jsonify({
        'doctors': ranked_doctors,
        'search_radius_meters': current_radius,
        'out_of_city': current_radius > 30000 if current_radius else False
    })


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
        doctor_id_str = sanitize_text(request.form.get('doctor_id', ''))
        reason = sanitize_text(request.form.get('reason', ''))
        chief_complaint = sanitize_text(request.form.get('chief_complaint', ''))

        try:
            age = max(1, min(120, int(age_str)))
        except ValueError:
            age = 30

        # Find the matching doctor
        doctor_obj = None
        if doctor_id_str and db_module.users_col is not None:
            try:
                doctor_obj = db_module.users_col.find_one({'_id': ObjectId(doctor_id_str), 'role': 'doctor'})
            except Exception:
                pass
        if not doctor_obj and db_module.users_col is not None:
            doctor_obj = db_module.users_col.find_one({'type_of_doctor': type_of_doctor, 'role': 'doctor'})

        doctor_id = doctor_obj['_id'] if doctor_obj else None
        hospital_name = doctor_obj.get('hospital_name', 'ArogyaX Health Centre') if doctor_obj else 'ArogyaX Health Centre'
        hospital_city = doctor_obj.get('hospital_city', '') if doctor_obj else ''

        # Generate unique Case ID
        case_id = generate_case_id(type_of_doctor)
        # Ensure uniqueness
        if db_module.consultation_cases_col is not None:
            while db_module.consultation_cases_col.find_one({'case_id': case_id}):
                case_id = generate_case_id(type_of_doctor)

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
            'doctor_id': doctor_id,
            'hospital_name': hospital_name,
            'hospital_city': hospital_city,
            'reason': reason,
            'chief_complaint': chief_complaint,
            'case_id': case_id,
            'created_at': datetime.utcnow()
        }

        if db_module.appointments_col is not None:
            appt_result = db_module.appointments_col.insert_one(appt_data)
            appt_id = appt_result.inserted_id

            # ── Create ConsultationCase ──────────────────────────────────────
            if db_module.consultation_cases_col is not None:
                case_doc = {
                    'case_id': case_id,
                    'appointment_id': appt_id,
                    'patient_id': user['_id'],
                    'patient_name': name,
                    'doctor_id': doctor_id,
                    'doctor_name': doctor_obj['username'] if doctor_obj else None,
                    'specialty': type_of_doctor,
                    'hospital_name': hospital_name,
                    'hospital_city': hospital_city,
                    'status': 'Pending',           # Pending | Active | Completed
                    'chief_complaint': chief_complaint,
                    'reason': reason,
                    # Case form fields (filled by doctor later)
                    'symptoms': [],
                    'duration': '',
                    'severity': '',
                    'medical_history': '',
                    'family_history': '',
                    'allergies': '',
                    'current_medications': '',
                    'previous_treatment': '',
                    'lifestyle_factors': '',
                    'vitals': {},
                    'examination_notes': '',
                    'investigation_notes': '',
                    'doctor_assessment': '',
                    'diagnosis': '',
                    'treatment_plan': '',
                    'follow_up_date': None,
                    'follow_up_reason': '',
                    'prescription_id': None,
                    'ai_insights': [],
                    'created_at': datetime.utcnow(),
                    'updated_at': datetime.utcnow()
                }
                db_module.consultation_cases_col.insert_one(case_doc)

            # Email doctor
            if doctor_obj:
                send_mail_safe('New Appointment Request — ArogyaX', doctor_obj.get('email'),
                    f"Hello Dr. {doctor_obj['username']},\n\nNew consultation booking from {name}.\nCase ID: {case_id}\nSpecialty: {type_of_doctor}\nTime Slot: {time_slot}\n\nPlease log in to review and approve.")

        flash(f'Appointment booked successfully! Your Case ID is {case_id}. Our clinic will notify you upon confirmation.', 'success')
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
            appt = db_module.appointments_col.find_one({'user_id': user['_id'], 'status': {'$in': ['Approved', 'Active']}})
        else:
            appt = db_module.appointments_col.find_one({'doctor_id': user['_id'], 'status': {'$in': ['Approved', 'Active']}})

    if not appt:
        flash('A video consultation requires an approved appointment assigned to your account.', 'warning')
        return redirect(url_for('patient.index'))

    appt_id = str(appt['_id'])
    doctor_obj = db_module.get_user_by_id(appt.get('doctor_id')) if appt.get('doctor_id') else None
    if user.get('role') == 'doctor':
        remote_name = appt.get('name') or 'Patient'
    else:
        remote_name = f"Dr. {doctor_obj.get('username')}" if doctor_obj else f"Dr. {appt.get('doctor_name') or 'Assigned Doctor'}"
    specialization = appt.get('type_of_doctor', 'Specialist')
    user_str = dict(user)
    user_str['_id'] = str(user['_id'])
    return render_template('videocall.html', username=user['username'], appointment_id=appt_id, role=user.get('role', 'patient'), user=user_str, doctor_name=remote_name, specialization=specialization, appointment=appt)


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

    if not appt or appt.get('status') not in ('Approved', 'Active'):
        flash('Video call is only available for confirmed approved appointments.', 'error')
        return redirect(url_for('patient.index'))

    # Security check for authorization
    if user.get('role') == 'patient':
        if str(appt.get('user_id', '')) != str(user['_id']):
            flash('Unauthorized access.', 'error')
            return redirect(url_for('patient.index'))
    elif user.get('role') == 'doctor':
        assigned_doctor_id = str(appt.get('doctor_id') or '')
        if (assigned_doctor_id and assigned_doctor_id != str(user['_id'])) or (not assigned_doctor_id and appt.get('type_of_doctor') != user.get('type_of_doctor')):
            flash('Unauthorized access.', 'error')
            return redirect(url_for('patient.index'))
    else:
        flash('Only the patient and assigned doctor can join this consultation.', 'error')
        return redirect(url_for('patient.index'))

    doctor_obj = db_module.get_user_by_id(appt.get('doctor_id')) if appt.get('doctor_id') else None
    if user.get('role') == 'doctor':
        remote_name = appt.get('name') or 'Patient'
    else:
        remote_name = f"Dr. {doctor_obj.get('username')}" if doctor_obj else f"Dr. {appt.get('doctor_name') or 'Assigned Doctor'}"
    user_str = dict(user)
    user_str['_id'] = str(user['_id'])
    return render_template('videocall.html', username=user['username'], appointment_id=appointment_id, role=user.get('role', 'patient'), user=user_str, doctor_name=remote_name, specialization=appt.get('type_of_doctor'), appointment=appt)


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

    user = get_current_user()  # re-fetch
    user_str = dict(user)
    user_str['_id'] = str(user['_id'])

    assessments = list(db_module.assessments_col.find({'patientId': str(user['_id'])}).sort('createdAt', -1)) if db_module.assessments_col is not None else []
    for a in assessments:
        a['_id'] = str(a['_id'])

    # Fetch prescriptions issued by doctors (linked to patient)
    doctor_prescriptions = []
    if db_module.prescriptions_col is not None:
        rxs = list(db_module.prescriptions_col.find({'patient_id': str(user['_id'])}).sort('created_at', -1))
        for rx in rxs:
            rx['_id'] = str(rx['_id'])
            doctor_prescriptions.append(rx)

    return render_template('vault.html', user=user_str, username=user['username'], role='patient',
                           assessments=assessments, doctor_prescriptions=doctor_prescriptions)


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
        if filepath and not os.path.isabs(filepath):
            filepath = os.path.join(Config.STATIC_FOLDER, filepath)
        if filepath and os.path.exists(filepath):
            return send_file(filepath, as_attachment=True)
        else:
            flash('Prescription file not found on server.', 'error')
    else:
        flash('Unauthorized access to medical record.', 'error')
    return redirect(url_for('patient.index'))


@patient_bp.route('/download-prescription/<prescription_id>')
@login_required
def download_prescription(prescription_id):
    """Download a structured prescription issued by a doctor."""
    user = get_current_user()
    if db_module.prescriptions_col is None:
        flash('Service unavailable.', 'error')
        return redirect(url_for('patient.vault'))

    try:
        rx = db_module.prescriptions_col.find_one({'_id': ObjectId(prescription_id)})
    except Exception:
        flash('Prescription not found.', 'error')
        return redirect(url_for('patient.vault'))

    if not rx or str(rx.get('patient_id')) != str(user['_id']):
        flash('Unauthorized access to this prescription.', 'error')
        return redirect(url_for('patient.vault'))

    filepath = rx.get('pdf_path')
    if filepath and not os.path.isabs(filepath):
        filepath = os.path.join(Config.STATIC_FOLDER, filepath)
    if filepath and os.path.exists(filepath):
        return send_file(filepath, as_attachment=True)
    else:
        flash('Prescription PDF not found on server.', 'error')
    return redirect(url_for('patient.vault'))


# ── Appointment-scoped call invitations ───────────────────────────────────
# This registry is process-local; use shared storage (e.g. Redis) for multi-worker deployments.
ACTIVE_CALLS = {}

@patient_bp.route('/api/call/initiate', methods=['POST'])
@login_required
def api_call_initiate():
    data = request.get_json(silent=True) or {}
    user = get_current_user()
    if not user or user.get('role') != 'patient':
        return jsonify({'success': False, 'message': 'Only the appointment patient can start a call'}), 403

    appointment_id = str(data.get('appointment_id') or '')
    authorized_user, error_response = _authorized_call_user(appointment_id)
    if error_response:
        return error_response
    try:
        appt = db_module.appointments_col.find_one({'_id': ObjectId(appointment_id)}) if db_module.appointments_col is not None else None
    except Exception:
        appt = None
    if not appt or str(appt.get('user_id') or '') != str(user['_id']):
        return jsonify({'success': False, 'message': 'Appointment not found for this patient'}), 404

    doctor_id = str(appt.get('doctor_id') or '')
    doctor = db_module.get_user_by_id(appt.get('doctor_id')) if appt.get('doctor_id') else None
    doctor_target = f"Dr. {doctor.get('username')}" if doctor else str(appt.get('type_of_doctor') or 'Assigned Doctor')
    import time
    now = time.time()
    for cid in list(ACTIVE_CALLS):
        if now - ACTIVE_CALLS[cid].get('created_at', 0) > 300:
            ACTIVE_CALLS.pop(cid, None)

    call_id = f"CALL-{int(now * 1000)}-{str(user['_id'])[-6:]}"
    room_url = url_for('patient.videocall', appointment_id=appointment_id)
    ACTIVE_CALLS[call_id] = {
        'call_id': call_id,
        'appointment_id': appointment_id,
        'caller_name': user.get('username') or 'Patient',
        'caller_id': str(user['_id']),
        'doctor_id': doctor_id,
        'doctor_target': doctor_target,
        'specialization': appt.get('type_of_doctor'),
        'reason': str(data.get('reason') or 'Telehealth Video Consultation')[:200],
        'status': 'ringing',
        'created_at': now,
        'room_url': room_url
    }
    return jsonify({'success': True, 'call_id': call_id, 'status': 'ringing', 'doctor_target': doctor_target, 'room_url': room_url})


@patient_bp.route('/api/call/check-incoming', methods=['GET'])
@login_required
def api_call_check_incoming():
    user = get_current_user()
    if not user or user.get('role') != 'doctor':
        return jsonify({'has_incoming': False}), 403
    import time
    now = time.time()
    for call_data in list(ACTIVE_CALLS.values()):
        if call_data.get('status') != 'ringing':
            continue
        if now - call_data.get('created_at', 0) > 90:
            call_data['status'] = 'missed'
            continue
        target_doctor_id = call_data.get('doctor_id')
        matches = (target_doctor_id == str(user['_id'])) if target_doctor_id else (
            call_data.get('specialization') and call_data.get('specialization') == user.get('type_of_doctor')
        )
        if matches:
            return jsonify({
                'has_incoming': True,
                'call_id': call_data['call_id'],
                'caller_name': call_data.get('caller_name', 'Patient'),
                'reason': call_data.get('reason', 'Video consultation'),
                'room_url': call_data.get('room_url')
            })
    return jsonify({'has_incoming': False})


@patient_bp.route('/api/call/respond', methods=['POST'])
@login_required
def api_call_respond():
    data = request.get_json(silent=True) or {}
    call_id = data.get('call_id')
    action = data.get('action')
    user = get_current_user()
    if not call_id or call_id not in ACTIVE_CALLS:
        return jsonify({'success': False, 'message': 'Call session not found'}), 404
    call_data = ACTIVE_CALLS[call_id]

    if action == 'cancel':
        if user.get('role') != 'patient' or call_data.get('caller_id') != str(user['_id']):
            return jsonify({'success': False, 'message': 'Only the caller can cancel this invitation'}), 403
        call_data['status'] = 'ended'
        return jsonify({'success': True, 'status': 'ended'})

    if user.get('role') != 'doctor' or action not in ('accept', 'decline'):
        return jsonify({'success': False, 'message': 'Invalid call response or role'}), 403
    target_doctor_id = call_data.get('doctor_id')
    authorized = (target_doctor_id == str(user['_id'])) if target_doctor_id else (
        call_data.get('specialization') and call_data.get('specialization') == user.get('type_of_doctor')
    )
    if not authorized:
        return jsonify({'success': False, 'message': 'This call is assigned to another doctor'}), 403
    if call_data.get('status') != 'ringing':
        return jsonify({'success': False, 'message': 'This call is no longer ringing'}), 409
    import time
    if time.time() - call_data.get('created_at', 0) > 90:
        call_data['status'] = 'missed'
        return jsonify({'success': False, 'message': 'This call has expired'}), 410
    call_data['status'] = 'accepted' if action == 'accept' else 'declined'
    result = {'success': True, 'status': call_data['status']}
    if action == 'accept':
        result['room_url'] = call_data['room_url']
    return jsonify(result)


@patient_bp.route('/api/call/status/<call_id>', methods=['GET'])
@login_required
def api_call_status(call_id):
    user = get_current_user()
    call_data = ACTIVE_CALLS.get(call_id)
    if not call_data:
        return jsonify({'success': False, 'status': 'not_found'}), 404
    if call_data.get('caller_id') != str(user['_id']):
        return jsonify({'success': False, 'message': 'Only the caller can view this call status'}), 403
    return jsonify({
        'success': True,
        'call_id': call_id,
        'status': call_data.get('status'),
        'room_url': call_data.get('room_url')
    })


# ── WebRTC telehealth signaling (authenticated participants only) ───────────
# In-memory storage is suitable only for a single worker/process. Use Redis or
# a database-backed signaling store when deploying multiple workers/instances.
import time as _call_time
from threading import RLock as _RLock
_WEBRTC_ROOMS = {}
_WEBRTC_LOCK = _RLock()
_WEBRTC_TTL_SECONDS = 4 * 60 * 60

def _prune_webrtc_rooms(now=None):
    now = now or _call_time.time()
    for room_key in list(_WEBRTC_ROOMS):
        if now - _WEBRTC_ROOMS[room_key].get('updated_at', now) > _WEBRTC_TTL_SECONDS:
            _WEBRTC_ROOMS.pop(room_key, None)

def _authorized_call_user(appointment_id):
    user = get_current_user()
    if not user:
        return None, (jsonify({'success': False, 'message': 'Authentication required'}), 401)
    try:
        appt = db_module.appointments_col.find_one({'_id': ObjectId(str(appointment_id))}) if db_module.appointments_col is not None else None
    except Exception:
        appt = None
    if not appt or appt.get('status') not in ('Approved', 'Active'):
        return None, (jsonify({'success': False, 'message': 'Approved appointment not found'}), 404)
    patient_id = str(appt.get('user_id') or '')
    doctor_id = str(appt.get('doctor_id') or '')
    user_id = str(user.get('_id'))
    authorized = (user.get('role') == 'patient' and patient_id == user_id) or (user.get('role') == 'doctor' and (doctor_id == user_id or (not doctor_id and appt.get('type_of_doctor') == user.get('type_of_doctor'))))
    if not authorized:
        return None, (jsonify({'success': False, 'message': 'You are not authorized for this appointment'}), 403)
    return user, None

@patient_bp.route('/api/call/session', methods=['POST'])
@login_required
def api_webrtc_session():
    data = request.get_json(silent=True) or {}
    appointment_id = str(data.get('appointment_id') or '')
    user, error_response = _authorized_call_user(appointment_id)
    if error_response:
        return error_response
    room_id = appointment_id or ('user-room-' + str(user['_id']))
    participant_id = str(user['_id'])
    with _WEBRTC_LOCK:
        _prune_webrtc_rooms()
        room = _WEBRTC_ROOMS.setdefault(room_id, {'participants': [], 'signals': [], 'created_at': _call_time.time(), 'updated_at': _call_time.time()})
        if participant_id not in room['participants']:
            if len(room['participants']) >= 2:
                return jsonify({'success': False, 'message': 'This consultation already has two participants'}), 409
            room['participants'].append(participant_id)
        is_first = room['participants'][0] == participant_id
        room['updated_at'] = _call_time.time()
        existing_offer = next((s for s in room['signals'] if s.get('type') == 'offer' and s.get('from') != participant_id), None)
        return jsonify({'success': True, 'call_id': room_id, 'should_offer': is_first and len(room['participants']) == 1, 'offer': existing_offer.get('description') if existing_offer else None, 'participants': len(room['participants'])})

@patient_bp.route('/api/call/signal/<path:call_id>', methods=['POST'])
@login_required
def api_webrtc_signal(call_id):
    data = request.get_json(silent=True) or {}
    signal_type = data.get('type')
    if signal_type not in ('offer', 'answer'):
        return jsonify({'success': False, 'message': 'Unsupported signal type'}), 400
    description = data.get('description') or {}
    if description.get('type') != signal_type or not description.get('sdp'):
        return jsonify({'success': False, 'message': 'Invalid SDP description'}), 400
    user = get_current_user()
    with _WEBRTC_LOCK:
        _prune_webrtc_rooms()
        room = _WEBRTC_ROOMS.get(call_id)
        if not room or str(user['_id']) not in room['participants']:
            return jsonify({'success': False, 'message': 'Call room not found or user is not a participant'}), 404
        room['signals'].append({'type': signal_type, 'description': description, 'from': str(user['_id']), 'at': _call_time.time()})
        room['updated_at'] = _call_time.time()
    return jsonify({'success': True})

@patient_bp.route('/api/call/ice/<path:call_id>', methods=['POST'])
@login_required
def api_webrtc_ice(call_id):
    data = request.get_json(silent=True) or {}
    candidate = data.get('candidate')
    if not isinstance(candidate, dict) or not candidate.get('candidate'):
        return jsonify({'success': False, 'message': 'Invalid ICE candidate'}), 400
    user = get_current_user()
    with _WEBRTC_LOCK:
        _prune_webrtc_rooms()
        room = _WEBRTC_ROOMS.get(call_id)
        if not room or str(user['_id']) not in room['participants']:
            return jsonify({'success': False, 'message': 'Call room not found or user is not a participant'}), 404
        room['signals'].append({'type': 'ice', 'candidate': candidate, 'from': str(user['_id']), 'at': _call_time.time()})
        room['updated_at'] = _call_time.time()
    return jsonify({'success': True})

@patient_bp.route('/api/call/signals/<path:call_id>', methods=['GET'])
@login_required
def api_webrtc_get_signals(call_id):
    user = get_current_user()
    participant_id = str(user['_id'])
    with _WEBRTC_LOCK:
        _prune_webrtc_rooms()
        room = _WEBRTC_ROOMS.get(call_id)
        if not room or participant_id not in room['participants']:
            return jsonify({'success': False, 'message': 'Call room not found or user is not a participant'}), 404
        after_seq = request.args.get('after', default=0, type=int)
        # Assign stable sequence IDs before filtering so each poll only returns new signals.
        for index, signal in enumerate(room['signals'], start=1):
            signal.setdefault('seq', index)
        received = [dict(s) for s in room['signals']
                    if s.get('from') != participant_id and s.get('seq', 0) > after_seq]
        room['updated_at'] = _call_time.time()
    return jsonify({'success': True, 'signals': [{'type': s['type'], 'description': s.get('description'), 'candidate': s.get('candidate'), 'seq': s['seq']} for s in received]})

@patient_bp.route('/api/call/end/<path:call_id>', methods=['POST'])
@login_required
def api_webrtc_end(call_id):
    user = get_current_user()
    participant_id = str(user['_id'])
    with _WEBRTC_LOCK:
        room = _WEBRTC_ROOMS.get(call_id)
        if room and participant_id in room['participants']:
            room['signals'].append({'type': 'ended', 'from': participant_id, 'at': _call_time.time()})
            room['updated_at'] = _call_time.time()
            # Keep the room around briefly so the peer can receive the end signal.
            room['participants'] = [pid for pid in room['participants'] if pid != participant_id]
            if not room['participants']:
                _WEBRTC_ROOMS.pop(call_id, None)
    return jsonify({'success': True})


@patient_bp.route('/api/call/leave/<path:call_id>', methods=['POST'])
@login_required
def api_webrtc_leave(call_id):
    """Remove the current authenticated participant from a call room without sending another end event."""
    user = get_current_user()
    participant_id = str(user['_id'])
    with _WEBRTC_LOCK:
        room = _WEBRTC_ROOMS.get(call_id)
        if room and participant_id in room['participants']:
            room['participants'] = [pid for pid in room['participants'] if pid != participant_id]
            room['updated_at'] = _call_time.time()
            if not room['participants']:
                _WEBRTC_ROOMS.pop(call_id, None)
    return jsonify({'success': True})
