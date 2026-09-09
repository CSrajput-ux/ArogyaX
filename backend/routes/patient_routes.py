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
            appt = db_module.appointments_col.find_one({'user_id': user['_id'], 'status': 'Approved'})
        else:
            appt = db_module.appointments_col.find_one({'doctor_id': user['_id'], 'status': 'Approved'})

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
        if str(appt.get('doctor_id', '')) != str(user['_id']) and appt.get('type_of_doctor') != user.get('type_of_doctor'):
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


# ── Live Telehealth Call Signaling (Patient to Doctor Priya Sharma / Specialists) ──

# Global in-memory call signaling registry (with auto-expiry)
ACTIVE_CALLS = {}

@patient_bp.route('/api/call/initiate', methods=['POST'])
def api_call_initiate():
    """Patient initiates a live consultation call to a doctor (e.g., Dr. Priya Sharma)."""
    data = request.get_json() or {}
    user = get_current_user()
    
    caller_name = data.get('caller_name') or (user.get('username') if user else 'Patient')
    caller_id = str(user['_id']) if user else 'guest_patient'
    doctor_target = (data.get('doctor_name') or data.get('doctor_id') or 'Dr. Priya Sharma').strip()
    reason = data.get('reason', 'Telehealth Video Consultation')
    
    import time
    call_id = f"CALL-{int(time.time()*1000)}"
    room_url = url_for('patient.videocall_direct')
    
    # Store call session
    ACTIVE_CALLS[call_id] = {
        'call_id': call_id,
        'caller_name': caller_name,
        'caller_id': caller_id,
        'doctor_target': doctor_target,
        'reason': reason,
        'status': 'ringing',
        'created_at': time.time(),
        'room_url': room_url
    }
    
    # Clean expired calls older than 5 minutes
    now = time.time()
    for cid in list(ACTIVE_CALLS.keys()):
        if now - ACTIVE_CALLS[cid].get('created_at', 0) > 300:
            ACTIVE_CALLS.pop(cid, None)
            
    return jsonify({
        'success': True,
        'call_id': call_id,
        'status': 'ringing',
        'doctor_target': doctor_target,
        'room_url': room_url
    })


@patient_bp.route('/api/call/check-incoming', methods=['GET'])
def api_call_check_incoming():
    """Doctor side polls to check if there is an active incoming call for them."""
    user = get_current_user()
    if not user:
        return jsonify({'has_incoming': False})
        
    doc_username = (user.get('username') or '').strip().lower()
    doc_fullname = f"dr. {doc_username}".lower()
    
    import time
    now = time.time()
    
    for call_id, call_data in list(ACTIVE_CALLS.items()):
        # Expire stale calls after 90 seconds of ringing
        if now - call_data.get('created_at', 0) > 90:
            if call_data.get('status') == 'ringing':
                call_data['status'] = 'missed'
            continue
            
        if call_data.get('status') == 'ringing':
            target = call_data.get('doctor_target', '').strip().lower()
            # Match if target is Priya Sharma or current doctor's username
            matches = False
            if 'priya' in target and ('priya' in doc_username or 'priya' in doc_fullname):
                matches = True
            elif target in doc_username or doc_username in target or target in doc_fullname:
                matches = True
            elif 'priya' in target:
                # If target is Priya Sharma, and logged in user is a doctor
                if user.get('role') == 'doctor':
                    matches = True
            
            if matches:
                return jsonify({
                    'has_incoming': True,
                    'call_id': call_id,
                    'caller_name': call_data.get('caller_name', 'Patient'),
                    'reason': call_data.get('reason', 'Immediate Consultation'),
                    'room_url': call_data.get('room_url', '/videocall')
                })
                
    return jsonify({'has_incoming': False})


@patient_bp.route('/api/call/respond', methods=['POST'])
def api_call_respond():
    """Doctor responds to an incoming call: accept or decline."""
    data = request.get_json() or {}
    call_id = data.get('call_id')
    action = data.get('action')  # 'accept' or 'decline'
    
    if call_id and call_id in ACTIVE_CALLS:
        if action == 'accept':
            ACTIVE_CALLS[call_id]['status'] = 'accepted'
            return jsonify({'success': True, 'status': 'accepted', 'room_url': ACTIVE_CALLS[call_id]['room_url']})
        else:
            ACTIVE_CALLS[call_id]['status'] = 'declined'
            return jsonify({'success': True, 'status': 'declined'})
            
    return jsonify({'success': False, 'message': 'Call session not found'}), 404


@patient_bp.route('/api/call/status/<call_id>', methods=['GET'])
def api_call_status(call_id):
    """Patient polls to check whether the doctor accepted or declined the call."""
    if call_id in ACTIVE_CALLS:
        return jsonify({
            'success': True,
            'call_id': call_id,
            'status': ACTIVE_CALLS[call_id].get('status'),
            'room_url': ACTIVE_CALLS[call_id].get('room_url')
        })
    return jsonify({'success': False, 'status': 'not_found'}), 404

