"""
ArogyaX Healthcare Platform — Database Connection & Access Layer
Backend: MongoDB Atlas (PyMongo)
Collections:
  users               → Patient and Doctor accounts
  appointments        → Appointment bookings
  assessments         → AI symptom/scan assessments
  consultation_cases  → Clinical case entities (per appointment)
  prescriptions       → Structured prescriptions (linked to cases + patients)
  hospitals           → Hospital / clinic profiles
  follow_ups          → Scheduled follow-up appointments
  audit_trail         → Clinical action audit log
"""

from pymongo import MongoClient
from bson.objectid import ObjectId
import certifi
from backend.config import Config

mongo_client = None
db = None

# Core collections
users_col = None
appointments_col = None
assessments_col = None

# New clinical collections
consultation_cases_col = None
prescriptions_col = None
hospitals_col = None
follow_ups_col = None
audit_trail_col = None

def init_db(app=None):
    global mongo_client, db
    global users_col, appointments_col, assessments_col
    global consultation_cases_col, prescriptions_col, hospitals_col, follow_ups_col, audit_trail_col

    try:
        if Config.MONGO_URI:
            mongo_client = MongoClient(
                Config.MONGO_URI,
                serverSelectionTimeoutMS=5000,
                tlsCAFile=certifi.where()
            )
            mongo_client.server_info()  # Trigger connection test
            db = mongo_client['manipal_sevak']

            # Core collections
            users_col = db['users']
            appointments_col = db['appointments']
            assessments_col = db['assessments']

            # New clinical collections
            consultation_cases_col = db['consultation_cases']
            prescriptions_col = db['prescriptions']
            hospitals_col = db['hospitals']
            follow_ups_col = db['follow_ups']
            audit_trail_col = db['audit_trail']

            # Indexes
            users_col.create_index('username', unique=True)
            users_col.create_index([('location', '2dsphere')])
            consultation_cases_col.create_index('case_id', unique=True)
            consultation_cases_col.create_index([('patient_id', 1), ('doctor_id', 1)])
            prescriptions_col.create_index([('patient_id', 1), ('case_id', 1)])
            audit_trail_col.create_index([('doctor_id', 1), ('timestamp', -1)])

            print("SUCCESS: MongoDB Atlas connected successfully.")
            print("  Collections: users, appointments, assessments,")
            print("               consultation_cases, prescriptions, hospitals,")
            print("               follow_ups, audit_trail")
        else:
            print("WARNING: MONGO_URI not provided. Running in demo fallback mode.")
    except Exception as e:
        print(f"WARNING: MongoDB connection failed: {e}")
        print("   Running in NO-DB mode (demo fallback). Check network or MONGO_URI.")

def is_db_connected():
    return db is not None and users_col is not None

def get_user_by_id(user_id):
    if users_col is None or not user_id:
        return None
    try:
        return users_col.find_one({'_id': ObjectId(user_id)})
    except Exception:
        return None

def get_user_by_username(username):
    if users_col is None or not username:
        return None
    try:
        return users_col.find_one({'username': username})
    except Exception:
        return None

def get_case_by_id(case_id):
    """Fetch a consultation case by its AX-XXXX-XXXXX case_id string."""
    if consultation_cases_col is None or not case_id:
        return None
    try:
        return consultation_cases_col.find_one({'case_id': case_id})
    except Exception:
        return None

def log_audit(doctor_id, doctor_name, patient_id, case_id, action):
    """Log a clinical audit trail event."""
    if audit_trail_col is None:
        return
    try:
        from datetime import datetime
        audit_trail_col.insert_one({
            'doctor_id': str(doctor_id),
            'doctor_name': doctor_name,
            'patient_id': str(patient_id) if patient_id else None,
            'case_id': case_id,
            'action': action,
            'timestamp': datetime.utcnow()
        })
    except Exception:
        pass  # Audit logging should never break the main flow
