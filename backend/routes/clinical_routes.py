"""
ArogyaX Healthcare Platform — Doctor Clinical Portal Routes
Blueprint: clinical
Handles: Enhanced Doctor Dashboard, Patient Queue, Clinical Cases, Structured Case-Taking,
         Prescription Management, AI Insights, Follow-up Scheduling, Audit Trail
"""

import os
from datetime import datetime
from bson.objectid import ObjectId
from flask import Blueprint, render_template, request, redirect, url_for, session, flash, send_file, jsonify
import backend.database as db_module
from backend.middleware import login_required, doctor_required, get_current_user
from backend.config import Config
from backend.security import allowed_file, sanitize_safe_filename, sanitize_text
from backend.services.pdf_service import generate_prescription_pdf_structured
from backend.services.mail_service import send_mail_safe

clinical_bp = Blueprint('clinical', __name__, url_prefix='/doctor')


def _str_doc(doc):
    """Convert ObjectId _id to string in a MongoDB document."""
    if doc and '_id' in doc:
        doc = dict(doc)
        doc['_id'] = str(doc['_id'])
    return doc


def _str_docs(docs):
    return [_str_doc(dict(d)) for d in docs]


def _log(doctor, patient_id, case_id, action):
    """Helper to log audit trail."""
    db_module.log_audit(
        doctor_id=doctor['_id'],
        doctor_name=f"Dr. {doctor['username']}",
        patient_id=patient_id,
        case_id=case_id,
        action=action
    )


# ── Doctor Dashboard ─────────────────────────────────────────────────────────

@clinical_bp.route('/dashboard')
@login_required
@doctor_required
def doctor_dashboard():
    doctor = get_current_user()
    doctor_id = doctor['_id']

    today_str = datetime.utcnow().strftime('%Y-%m-%d')

    # Fetch appointments for THIS doctor
    if db_module.appointments_col is not None:
        all_appts = list(db_module.appointments_col.find({'doctor_id': doctor_id}))
        # Also include legacy specialty-matched appointments without doctor_id
        legacy = list(db_module.appointments_col.find({
            'type_of_doctor': doctor.get('type_of_doctor'),
            'doctor_id': {'$exists': False}
        }))
        all_appts.extend(legacy)
    else:
        all_appts = []

    # Stats
    total = len(all_appts)
    pending = sum(1 for a in all_appts if a.get('status') == 'Pending')
    approved = sum(1 for a in all_appts if a.get('status') == 'Approved')
    prescribed = sum(1 for a in all_appts if a.get('status') == 'Prescribed')

    # Today's queue — all appointments (filtering by today's date from time_slot)
    todays_appts = []
    for a in all_appts:
        a_str = _str_doc(a)
        # Attach patient info
        try:
            pat = db_module.get_user_by_id(str(a.get('user_id', '')))
            a_str['patient_info'] = _str_doc(pat) if pat else {}
        except Exception:
            a_str['patient_info'] = {}
        todays_appts.append(a_str)

    # Sort by created_at descending
    todays_appts.sort(key=lambda x: x.get('created_at', datetime.min), reverse=True)

    # Clinical cases
    my_cases = []
    if db_module.consultation_cases_col is not None:
        cases_cursor = db_module.consultation_cases_col.find({'doctor_id': doctor_id}).sort('created_at', -1).limit(10)
        for c in cases_cursor:
            c_str = _str_doc(c)
            my_cases.append(c_str)

    # Prescriptions count
    rx_count = 0
    if db_module.prescriptions_col is not None:
        rx_count = db_module.prescriptions_col.count_documents({'doctor_id': str(doctor_id)})

    doctor_str = _str_doc(doctor)
    _log(doctor, None, None, "Viewed clinical dashboard")

    return render_template('doctor-dashboard.html',
                           username=doctor['username'],
                           doctor=doctor_str,
                           appointments=todays_appts,
                           total_patients=total,
                           pending_count=pending,
                           approved_count=approved,
                           prescribed_count=prescribed,
                           rx_count=rx_count,
                           recent_cases=my_cases)


# ── My Patients ──────────────────────────────────────────────────────────────

@clinical_bp.route('/my-patients')
@login_required
@doctor_required
def my_patients():
    doctor = get_current_user()
    doctor_id = doctor['_id']

    search = request.args.get('search', '').strip()
    status_filter = request.args.get('status', 'all')

    if db_module.appointments_col is None:
        flash('Database unavailable.', 'error')
        return render_template('doctor-patients-new.html', doctor=_str_doc(doctor), patients=[], username=doctor['username'])

    # This doctor's appointments + legacy
    query = {'doctor_id': doctor_id}
    appts = list(db_module.appointments_col.find(query))
    legacy = list(db_module.appointments_col.find({
        'type_of_doctor': doctor.get('type_of_doctor'),
        'doctor_id': {'$exists': False}
    }))
    appts.extend(legacy)

    # Build unique patient list
    seen_patients = {}
    for a in appts:
        uid = str(a.get('user_id', ''))
        if uid and uid not in seen_patients:
            pat = db_module.get_user_by_id(uid)
            if pat:
                pat_str = _str_doc(pat)
                pat_str['last_appointment'] = a
                pat_str['last_appointment']['_id'] = str(a['_id'])
                pat_str['case_id'] = a.get('case_id', '')
                pat_str['appt_status'] = a.get('status', 'Pending')
                seen_patients[uid] = pat_str

    patients = list(seen_patients.values())

    # Filter by search
    if search:
        patients = [p for p in patients if search.lower() in p.get('username', '').lower()
                    or search.lower() in p.get('email', '').lower()]

    # Filter by status
    if status_filter != 'all':
        patients = [p for p in patients if p.get('appt_status', '').lower() == status_filter.lower()]

    doctor_str = _str_doc(doctor)
    return render_template('doctor-patients-new.html',
                           doctor=doctor_str, patients=patients,
                           username=doctor['username'],
                           search=search, status_filter=status_filter)


# ── Clinical Cases List ───────────────────────────────────────────────────────

@clinical_bp.route('/clinical-cases')
@login_required
@doctor_required
def clinical_cases():
    doctor = get_current_user()
    doctor_id = doctor['_id']

    status_filter = request.args.get('status', 'all')
    search = request.args.get('search', '').strip()

    cases = []
    if db_module.consultation_cases_col is not None:
        query = {'doctor_id': doctor_id}
        if status_filter != 'all':
            query['status'] = status_filter.capitalize()
        cursor = db_module.consultation_cases_col.find(query).sort('created_at', -1)
        for c in cursor:
            c_str = _str_doc(c)
            if search:
                if search.lower() not in c_str.get('patient_name', '').lower() and \
                   search.lower() not in c_str.get('case_id', '').lower():
                    continue
            cases.append(c_str)

    doctor_str = _str_doc(doctor)
    return render_template('doctor-clinical-cases.html',
                           doctor=doctor_str, cases=cases,
                           username=doctor['username'],
                           status_filter=status_filter, search=search)


# ── Open / Edit a Case ────────────────────────────────────────────────────────

@clinical_bp.route('/case/<case_id>', methods=['GET', 'POST'])
@login_required
@doctor_required
def open_case(case_id):
    doctor = get_current_user()
    doctor_id = doctor['_id']

    if db_module.consultation_cases_col is None:
        flash('Database unavailable.', 'error')
        return redirect(url_for('clinical.doctor_dashboard'))

    case = db_module.consultation_cases_col.find_one({'case_id': case_id})
    if not case:
        flash('Consultation case not found.', 'error')
        return redirect(url_for('clinical.doctor_dashboard'))

    # Access control — only the assigned doctor or same specialty
    case_doctor_id = case.get('doctor_id')
    if case_doctor_id and str(case_doctor_id) != str(doctor_id):
        if case.get('specialty') != doctor.get('type_of_doctor'):
            flash('Access restricted to the assigned clinician.', 'error')
            return redirect(url_for('clinical.doctor_dashboard'))

    if request.method == 'POST':
        action = request.form.get('action', 'save_draft')

        updates = {
            'symptoms': [s.strip() for s in request.form.get('symptoms', '').split(',') if s.strip()],
            'duration': sanitize_text(request.form.get('duration', '')),
            'severity': sanitize_text(request.form.get('severity', '')),
            'medical_history': sanitize_text(request.form.get('medical_history', ''), max_len=2000),
            'family_history': sanitize_text(request.form.get('family_history', ''), max_len=1000),
            'allergies': sanitize_text(request.form.get('allergies', '')),
            'current_medications': sanitize_text(request.form.get('current_medications', '')),
            'previous_treatment': sanitize_text(request.form.get('previous_treatment', '')),
            'lifestyle_factors': sanitize_text(request.form.get('lifestyle_factors', '')),
            'vitals': {
                'bp': sanitize_text(request.form.get('vitals_bp', '')),
                'pulse': sanitize_text(request.form.get('vitals_pulse', '')),
                'temp': sanitize_text(request.form.get('vitals_temp', '')),
                'spo2': sanitize_text(request.form.get('vitals_spo2', '')),
                'weight': sanitize_text(request.form.get('vitals_weight', '')),
                'height': sanitize_text(request.form.get('vitals_height', '')),
            },
            'examination_notes': sanitize_text(request.form.get('examination_notes', ''), max_len=2000),
            'investigation_notes': sanitize_text(request.form.get('investigation_notes', '')),
            'doctor_assessment': sanitize_text(request.form.get('doctor_assessment', ''), max_len=2000),
            'diagnosis': sanitize_text(request.form.get('diagnosis', '')),
            'treatment_plan': sanitize_text(request.form.get('treatment_plan', ''), max_len=2000),
            'doctor_id': doctor_id,
            'doctor_name': doctor['username'],
            'updated_at': datetime.utcnow()
        }

        if action == 'complete':
            updates['status'] = 'Completed'
        else:
            updates['status'] = 'Active'

        db_module.consultation_cases_col.update_one({'case_id': case_id}, {'$set': updates})
        # Update appointment status too
        if db_module.appointments_col is not None:
            db_module.appointments_col.update_one(
                {'case_id': case_id},
                {'$set': {'status': 'Approved' if action != 'complete' else 'Completed'}}
            )

        log_action = 'Completed consultation case' if action == 'complete' else 'Updated case (draft saved)'
        _log(doctor, case.get('patient_id'), case_id, log_action)

        flash('Case updated successfully!' if action != 'complete' else 'Consultation completed!', 'success')
        return redirect(url_for('clinical.open_case', case_id=case_id))

    # Fetch patient info
    patient = db_module.get_user_by_id(str(case.get('patient_id', '')))
    patient_str = _str_doc(patient) if patient else {}

    # Fetch AI assessments for this patient
    ai_assessments = []
    if db_module.assessments_col is not None and patient:
        assessments = list(db_module.assessments_col.find(
            {'patientId': str(patient['_id'])}).sort('createdAt', -1).limit(5))
        for a in assessments:
            a['_id'] = str(a['_id'])
            ai_assessments.append(a)

    # Fetch patient's health vault records
    vault_records = patient_str.get('records', []) if patient_str else []

    # Clinical timeline — all events sorted chronologically
    timeline = _build_clinical_timeline(patient, case, ai_assessments)

    case_str = _str_doc(case)
    doctor_str = _str_doc(doctor)

    _log(doctor, case.get('patient_id'), case_id, "Opened patient case")

    return render_template('doctor-case.html',
                           doctor=doctor_str,
                           case=case_str,
                           patient=patient_str,
                           ai_assessments=ai_assessments,
                           vault_records=vault_records,
                           timeline=timeline,
                           username=doctor['username'])


def _build_clinical_timeline(patient, case, ai_assessments):
    """Build a chronological clinical event timeline."""
    events = []

    # Case creation
    if case.get('created_at'):
        events.append({
            'date': case['created_at'],
            'type': 'appointment',
            'icon': '📅',
            'title': f"Appointment Booked — {case.get('specialty', '')}",
            'detail': f"Case ID: {case.get('case_id', '')}",
            'color': '#0f52ab'
        })

    # AI assessments
    for a in ai_assessments:
        dt = a.get('createdAt') or a.get('date')
        if dt and isinstance(dt, str):
            try:
                dt = datetime.strptime(dt, '%Y-%m-%d')
            except Exception:
                dt = None
        if dt:
            events.append({
                'date': dt,
                'type': 'ai',
                'icon': '🤖',
                'title': f"AI Assessment — {a.get('assessmentType', 'Symptom Check')}",
                'detail': a.get('result', ''),
                'color': '#7c5cfc'
            })

    # Vault records / reports
    if patient:
        for r in patient.get('records', []):
            dt = r.get('uploaded_at')
            if dt:
                events.append({
                    'date': dt,
                    'type': 'report',
                    'icon': '📋',
                    'title': f"Report Uploaded — {r.get('title', 'Medical Record')}",
                    'detail': '',
                    'color': '#0d9488'
                })

    # Sort descending (newest first)
    events.sort(key=lambda x: x['date'] if isinstance(x['date'], datetime) else datetime.min, reverse=True)
    # Convert dates to readable strings
    for e in events:
        if isinstance(e['date'], datetime):
            e['date_str'] = e['date'].strftime('%d %b %Y')
        else:
            e['date_str'] = str(e['date'])
    return events


# ── Clinical Patient Profile ──────────────────────────────────────────────────

@clinical_bp.route('/patient-profile/<patient_id>/<case_id>')
@login_required
@doctor_required
def patient_clinical_profile(patient_id, case_id):
    doctor = get_current_user()

    patient = db_module.get_user_by_id(patient_id)
    if not patient:
        flash('Patient not found.', 'error')
        return redirect(url_for('clinical.doctor_dashboard'))

    # Verify doctor has access via a linked case
    authorized = False
    if db_module.consultation_cases_col is not None:
        linked = db_module.consultation_cases_col.find_one({
            'case_id': case_id,
            'patient_id': ObjectId(patient_id)
        })
        if linked:
            case_doc_id = str(linked.get('doctor_id', ''))
            if case_doc_id == str(doctor['_id']) or linked.get('specialty') == doctor.get('type_of_doctor'):
                authorized = True

    if not authorized:
        flash('Access restricted to authorized clinician.', 'error')
        return redirect(url_for('clinical.doctor_dashboard'))

    patient_str = _str_doc(patient)

    # Get all cases for this patient (only same specialty as doctor — specialist access control)
    all_cases = []
    if db_module.consultation_cases_col is not None:
        specialty_cases = list(db_module.consultation_cases_col.find({
            'patient_id': ObjectId(patient_id),
            'specialty': doctor.get('type_of_doctor')
        }).sort('created_at', -1))
        all_cases = [_str_doc(c) for c in specialty_cases]

    # AI assessments
    ai_assessments = []
    if db_module.assessments_col is not None:
        assessments = list(db_module.assessments_col.find(
            {'patientId': patient_id}).sort('createdAt', -1).limit(10))
        for a in assessments:
            a['_id'] = str(a['_id'])
            ai_assessments.append(a)

    # Prescriptions issued for this patient (by this doctor's specialty)
    prescriptions = []
    if db_module.prescriptions_col is not None:
        rxs = list(db_module.prescriptions_col.find({
            'patient_id': patient_id,
            'specialty': doctor.get('type_of_doctor')
        }).sort('created_at', -1))
        prescriptions = [_str_doc(rx) for rx in rxs]

    # Current case
    current_case = db_module.consultation_cases_col.find_one({'case_id': case_id}) if db_module.consultation_cases_col else None
    current_case_str = _str_doc(current_case) if current_case else {}

    _log(doctor, patient_id, case_id, "Viewed clinical patient profile")

    return render_template('doctor-patient-profile.html',
                           doctor=_str_doc(doctor),
                           patient=patient_str,
                           current_case=current_case_str,
                           all_cases=all_cases,
                           ai_assessments=ai_assessments,
                           prescriptions=prescriptions,
                           username=doctor['username'])


# ── Prescriptions ─────────────────────────────────────────────────────────────

@clinical_bp.route('/prescriptions')
@login_required
@doctor_required
def doctor_prescriptions():
    doctor = get_current_user()
    doctor_id = str(doctor['_id'])

    rxs = []
    if db_module.prescriptions_col is not None:
        cursor = db_module.prescriptions_col.find({'doctor_id': doctor_id}).sort('created_at', -1)
        rxs = [_str_doc(rx) for rx in cursor]

    return render_template('doctor-prescriptions.html',
                           doctor=_str_doc(doctor),
                           prescriptions=rxs,
                           username=doctor['username'])


@clinical_bp.route('/create-prescription/<case_id>', methods=['GET', 'POST'])
@login_required
@doctor_required
def create_prescription(case_id):
    doctor = get_current_user()
    doctor_id = doctor['_id']

    if db_module.consultation_cases_col is None:
        flash('Database unavailable.', 'error')
        return redirect(url_for('clinical.doctor_dashboard'))

    case = db_module.consultation_cases_col.find_one({'case_id': case_id})
    if not case:
        flash('Case not found.', 'error')
        return redirect(url_for('clinical.doctor_dashboard'))

    available_medicines = [
        "Paracetamol 500mg", "Paracetamol 650mg", "Ibuprofen 400mg", "Ibuprofen 600mg",
        "Amoxicillin 250mg", "Amoxicillin 500mg", "Azithromycin 250mg", "Azithromycin 500mg",
        "Cetirizine 10mg", "Loratadine 10mg", "Omeprazole 20mg", "Pantoprazole 40mg",
        "Metformin 500mg", "Metformin 1000mg", "Atorvastatin 10mg", "Atorvastatin 20mg",
        "Amlodipine 5mg", "Amlodipine 10mg", "Vitamin D3 60000IU", "Vitamin C 500mg",
        "Vitamin B12 500mcg", "Iron + Folic Acid", "Calcium 500mg + D3",
        "Clopidogrel 75mg", "Aspirin 75mg", "Ramipril 5mg", "Metoprolol 25mg",
        "Losartan 50mg", "Furosemide 40mg", "Spironolactone 25mg",
        "Salbutamol Inhaler 100mcg", "Montelukast 10mg", "Theophylline 200mg",
        "Prednisolone 10mg", "Dexamethasone 4mg", "Methylprednisolone 4mg",
        "Fluconazole 150mg", "Metronidazole 400mg", "Ciprofloxacin 500mg",
        "Doxycycline 100mg", "Clindamycin 300mg", "Cefixime 200mg",
    ]

    if request.method == 'POST':
        action = request.form.get('action', 'save')

        # Collect medicines with details
        medicine_names = request.form.getlist('medicine_name[]')
        dosages = request.form.getlist('dosage[]')
        frequencies = request.form.getlist('frequency[]')
        durations = request.form.getlist('duration[]')
        instructions_list = request.form.getlist('instructions[]')

        medicines = []
        for i, med in enumerate(medicine_names):
            if med.strip():
                medicines.append({
                    'name': sanitize_text(med),
                    'dosage': sanitize_text(dosages[i] if i < len(dosages) else ''),
                    'frequency': sanitize_text(frequencies[i] if i < len(frequencies) else ''),
                    'duration': sanitize_text(durations[i] if i < len(durations) else ''),
                    'instructions': sanitize_text(instructions_list[i] if i < len(instructions_list) else ''),
                })

        if not medicines:
            flash('Please add at least one medicine.', 'error')
            return redirect(url_for('clinical.create_prescription', case_id=case_id))

        diagnosis = sanitize_text(request.form.get('diagnosis', case.get('diagnosis', '')))
        advice_notes = sanitize_text(request.form.get('advice_notes', ''), max_len=2000)
        follow_up_date = sanitize_text(request.form.get('follow_up_date', ''))
        follow_up_reason = sanitize_text(request.form.get('follow_up_reason', ''))

        patient_id_str = str(case.get('patient_id', ''))
        patient = db_module.get_user_by_id(patient_id_str)

        # Generate unique prescription ID
        import random
        rx_id = f"RX-{case_id}-{random.randint(1000,9999)}"

        # Build prescription document
        rx_doc = {
            'rx_id': rx_id,
            'case_id': case_id,
            'appointment_id': str(case.get('appointment_id', '')),
            'patient_id': patient_id_str,
            'patient_name': case.get('patient_name', patient['username'] if patient else 'Patient'),
            'doctor_id': str(doctor_id),
            'doctor_name': doctor['username'],
            'specialty': doctor.get('type_of_doctor', 'General Physician'),
            'hospital_name': doctor.get('hospital_name', 'ArogyaX Health Centre'),
            'hospital_city': doctor.get('hospital_city', ''),
            'diagnosis': diagnosis,
            'medicines': medicines,
            'advice_notes': advice_notes,
            'follow_up_date': follow_up_date,
            'follow_up_reason': follow_up_reason,
            'status': 'Final' if action == 'send' else 'Draft',
            'created_at': datetime.utcnow(),
            'pdf_path': None
        }

        # Generate PDF
        try:
            pdf_path = generate_prescription_pdf_structured(
                rx_id=rx_id,
                case_id=case_id,
                patient_name=rx_doc['patient_name'],
                patient_age=patient.get('age', '') if patient else '',
                doctor_name=doctor['username'],
                doctor_spec=doctor.get('type_of_doctor', 'Physician'),
                hospital_name=rx_doc['hospital_name'],
                diagnosis=diagnosis,
                medicines=medicines,
                advice_notes=advice_notes,
                follow_up_date=follow_up_date
            )
            rx_doc['pdf_path'] = pdf_path
        except Exception as e:
            print(f"PDF generation error: {e}")

        # Save prescription to prescriptions collection
        if db_module.prescriptions_col is not None:
            db_module.prescriptions_col.insert_one(rx_doc)

        # ── AUTO-LINK to Patient's Health Vault ──────────────────────────
        if patient and db_module.users_col is not None:
            vault_entry = {
                'title': f"Prescription from Dr. {doctor['username']} ({case_id})",
                'rx_id': rx_id,
                'case_id': case_id,
                'doctor': doctor['username'],
                'specialty': doctor.get('type_of_doctor', ''),
                'diagnosis': diagnosis,
                'pdf_path': rx_doc.get('pdf_path'),
                'type': 'prescription',
                'issued_at': datetime.utcnow()
            }
            db_module.users_col.update_one(
                {'_id': patient['_id']},
                {'$push': {'prescriptions': vault_entry}}
            )

        # Update consultation case with diagnosis + prescription ref
        if db_module.consultation_cases_col is not None:
            db_module.consultation_cases_col.update_one(
                {'case_id': case_id},
                {'$set': {
                    'diagnosis': diagnosis,
                    'follow_up_date': follow_up_date,
                    'follow_up_reason': follow_up_reason,
                    'status': 'Completed' if action == 'send' else 'Active',
                    'updated_at': datetime.utcnow()
                }}
            )

        # Update appointment status to Prescribed
        if db_module.appointments_col is not None:
            db_module.appointments_col.update_one(
                {'case_id': case_id},
                {'$set': {'status': 'Prescribed', 'prescription_rx_id': rx_id}}
            )

        # Schedule follow-up if provided
        if follow_up_date and db_module.follow_ups_col is not None:
            db_module.follow_ups_col.insert_one({
                'case_id': case_id,
                'patient_id': patient_id_str,
                'doctor_id': str(doctor_id),
                'follow_up_date': follow_up_date,
                'reason': follow_up_reason,
                'status': 'Scheduled',
                'created_at': datetime.utcnow()
            })

        # Send email if "Send to Patient"
        if action == 'send' and patient:
            send_mail_safe(
                'Your Prescription — ArogyaX',
                patient.get('email', ''),
                f"Dear {patient.get('username', 'Patient')},\n\n"
                f"Dr. {doctor['username']} has issued your prescription.\n"
                f"Prescription ID: {rx_id}\n"
                f"Diagnosis: {diagnosis}\n"
                f"Follow-up: {follow_up_date or 'Not scheduled'}\n\n"
                f"Please check your Health Vault for full details."
            )

        _log(doctor, patient_id_str, case_id, f"Created prescription {rx_id}")
        flash('Prescription saved and added to patient\'s health records!', 'success')
        if action == 'send':
            flash('Prescription sent to patient successfully.', 'success')
        return redirect(url_for('clinical.open_case', case_id=case_id))

    # GET — show prescription form
    patient = db_module.get_user_by_id(str(case.get('patient_id', '')))
    case_str = _str_doc(case)
    doctor_str = _str_doc(doctor)

    return render_template('doctor-create-prescription.html',
                           doctor=doctor_str,
                           case=case_str,
                           patient=_str_doc(patient) if patient else {},
                           available_medicines=available_medicines,
                           username=doctor['username'])


# ── Download Prescription PDF (Doctor) ───────────────────────────────────────

@clinical_bp.route('/download-rx/<rx_id>')
@login_required
@doctor_required
def download_rx(rx_id):
    doctor = get_current_user()
    if db_module.prescriptions_col is None:
        flash('Database unavailable.', 'error')
        return redirect(url_for('clinical.doctor_prescriptions'))

    rx = db_module.prescriptions_col.find_one({'rx_id': rx_id})
    if not rx or str(rx.get('doctor_id')) != str(doctor['_id']):
        flash('Unauthorized or not found.', 'error')
        return redirect(url_for('clinical.doctor_prescriptions'))

    filepath = rx.get('pdf_path')
    if filepath and not os.path.isabs(filepath):
        filepath = os.path.join(Config.STATIC_FOLDER, filepath)
    if filepath and os.path.exists(filepath):
        return send_file(filepath, as_attachment=True)
    flash('PDF file not found.', 'error')
    return redirect(url_for('clinical.doctor_prescriptions'))


# ── Schedule Follow-up ────────────────────────────────────────────────────────

@clinical_bp.route('/schedule-followup/<case_id>', methods=['POST'])
@login_required
@doctor_required
def schedule_followup(case_id):
    doctor = get_current_user()

    follow_up_date = sanitize_text(request.form.get('follow_up_date', ''))
    follow_up_reason = sanitize_text(request.form.get('follow_up_reason', ''))

    if not follow_up_date:
        flash('Please provide a follow-up date.', 'error')
        return redirect(url_for('clinical.open_case', case_id=case_id))

    case = None
    if db_module.consultation_cases_col is not None:
        case = db_module.consultation_cases_col.find_one({'case_id': case_id})
        if case:
            db_module.consultation_cases_col.update_one(
                {'case_id': case_id},
                {'$set': {'follow_up_date': follow_up_date, 'follow_up_reason': follow_up_reason}}
            )

    if db_module.follow_ups_col is not None and case:
        db_module.follow_ups_col.insert_one({
            'case_id': case_id,
            'patient_id': str(case.get('patient_id', '')),
            'doctor_id': str(doctor['_id']),
            'follow_up_date': follow_up_date,
            'reason': follow_up_reason,
            'status': 'Scheduled',
            'created_at': datetime.utcnow()
        })

    _log(doctor, case.get('patient_id') if case else None, case_id,
         f"Scheduled follow-up for {follow_up_date}")
    flash(f'Follow-up scheduled for {follow_up_date}.', 'success')
    return redirect(url_for('clinical.open_case', case_id=case_id))


# ── AI Insights for a Case ────────────────────────────────────────────────────

@clinical_bp.route('/ai-insights/<case_id>')
@login_required
@doctor_required
def ai_insights(case_id):
    doctor = get_current_user()

    case = db_module.consultation_cases_col.find_one({'case_id': case_id}) if db_module.consultation_cases_col else None
    if not case:
        return jsonify({'error': 'Case not found'}), 404

    patient_id = str(case.get('patient_id', ''))
    assessments = []
    if db_module.assessments_col is not None:
        cursor = db_module.assessments_col.find({'patientId': patient_id}).sort('createdAt', -1).limit(10)
        for a in cursor:
            a['_id'] = str(a['_id'])
            if isinstance(a.get('createdAt'), datetime):
                a['createdAt'] = a['createdAt'].strftime('%d %b %Y')
            assessments.append(a)

    _log(doctor, patient_id, case_id, "Viewed AI insights for case")
    return jsonify({'assessments': assessments, 'case_id': case_id})


# ── Approve Appointment (redirect to case) ────────────────────────────────────

@clinical_bp.route('/approve/<appointment_id>')
@login_required
@doctor_required
def approve_appointment(appointment_id):
    doctor = get_current_user()
    if db_module.appointments_col is None:
        flash('Database unavailable.', 'error')
        return redirect(url_for('clinical.doctor_dashboard'))

    try:
        appt = db_module.appointments_col.find_one({'_id': ObjectId(appointment_id)})
    except Exception:
        flash('Appointment not found.', 'error')
        return redirect(url_for('clinical.doctor_dashboard'))

    if not appt:
        flash('Appointment not found.', 'error')
        return redirect(url_for('clinical.doctor_dashboard'))

    db_module.appointments_col.update_one(
        {'_id': ObjectId(appointment_id)},
        {'$set': {
            'status': 'Approved',
            'doctor_id': doctor['_id'],
            'doctor_name': doctor['username']
        }}
    )

    # Update case status too
    case_id = appt.get('case_id')
    if case_id and db_module.consultation_cases_col is not None:
        db_module.consultation_cases_col.update_one(
            {'case_id': case_id},
            {'$set': {
                'status': 'Active',
                'doctor_id': doctor['_id'],
                'doctor_name': doctor['username']
            }}
        )

    # Notify patient
    patient = db_module.get_user_by_id(str(appt.get('user_id', '')))
    if patient:
        send_mail_safe(
            'Appointment Confirmed — ArogyaX',
            patient.get('email', ''),
            f"Hello {patient.get('username', 'Patient')},\n\n"
            f"Your appointment has been approved by Dr. {doctor['username']}.\n"
            f"Case ID: {case_id or 'N/A'}\nTime: {appt.get('time_slot', '')}\n\n"
            f"You can now join the video consultation from your dashboard."
        )

    _log(doctor, appt.get('user_id'), case_id, "Approved appointment")
    flash('Appointment approved and patient notified.', 'success')

    if case_id:
        return redirect(url_for('clinical.open_case', case_id=case_id))
    return redirect(url_for('clinical.doctor_dashboard'))

# ── Video Consultation Notes & Prescription ────────────────────────────────────

@clinical_bp.route('/video-consultation/save-notes', methods=['POST'])
@login_required
@doctor_required
def save_video_notes():
    doctor = get_current_user()
    data = request.json
    appointment_id = data.get('appointment_id')
    medicines = sanitize_text(data.get('medicines', ''))
    instructions = sanitize_text(data.get('instructions', ''))

    if not appointment_id:
        return jsonify({'success': False, 'message': 'Missing appointment ID'}), 400

    appt = db_module.appointments_col.find_one({'_id': ObjectId(appointment_id)}) if db_module.appointments_col is not None else None
    if not appt:
        return jsonify({'success': False, 'message': 'Appointment not found'}), 404

    case_id = appt.get('case_id')
    patient_id = appt.get('user_id')

    if not case_id or not patient_id:
        return jsonify({'success': False, 'message': 'Case or Patient ID missing'}), 400

    # Prepare Rx data
    rx_data = {
        'rx_id': f"RX-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
        'case_id': case_id,
        'patient_id': str(patient_id),
        'doctor_id': doctor['_id'],
        'doctor_name': doctor['username'],
        'medicines': medicines,
        'advice': instructions,
        'created_at': datetime.utcnow()
    }

    # Generate PDF
    pdf_path = None
    try:
        pdf_path = generate_prescription_pdf_structured(rx_data, doctor, appt.get('patient_info', {}))
        if pdf_path and pdf_path.startswith('static/'):
            pdf_path = pdf_path.replace('static/', '', 1)
        rx_data['pdf_file'] = pdf_path
    except Exception as e:
        print(f"Error generating prescription PDF: {e}")

    # Save Prescription
    if db_module.prescriptions_col is not None:
        db_module.prescriptions_col.insert_one(rx_data)

    # Link to Case
    if db_module.consultation_cases_col is not None:
        db_module.consultation_cases_col.update_one(
            {'case_id': case_id},
            {
                '$push': {'prescriptions': rx_data['rx_id']},
                '$set': {'status': 'Closed - Prescribed'}
            }
        )

    # Update Appointment
    if db_module.appointments_col is not None:
        db_module.appointments_col.update_one(
            {'_id': ObjectId(appointment_id)},
            {'$set': {'status': 'Prescribed', 'prescription_file': pdf_path}}
        )

    _log(doctor, patient_id, case_id, f"Saved clinical notes & generated Rx {rx_data['rx_id']} from video consult")

    return jsonify({'success': True, 'message': 'Prescription saved to Health Vault successfully!'})
