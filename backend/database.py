"""
ArogyaX Healthcare Platform — Database Connection & Access Layer
Backend: MongoDB Atlas (PyMongo)
"""

from pymongo import MongoClient
from bson.objectid import ObjectId
import certifi
from backend.config import Config

mongo_client = None
db = None
users_col = None
appointments_col = None
assessments_col = None

def init_db(app=None):
    global mongo_client, db, users_col, appointments_col, assessments_col
    try:
        if Config.MONGO_URI:
            mongo_client = MongoClient(
                Config.MONGO_URI,
                serverSelectionTimeoutMS=5000,
                tlsCAFile=certifi.where()
            )
            mongo_client.server_info()  # Trigger connection test
            db = mongo_client['manipal_sevak']
            users_col = db['users']
            appointments_col = db['appointments']
            assessments_col = db['assessments']
            
            # Ensure unique index on username
            users_col.create_index('username', unique=True)
            print("SUCCESS: MongoDB Atlas connected successfully.")
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
