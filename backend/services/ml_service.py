"""
ArogyaX Healthcare Platform — Machine Learning Diagnostic Service
Model: Decision Tree Classifier trained on medical symptom dataset
"""

import os
import csv
import numpy as np
import pandas as pd
from sklearn.tree import DecisionTreeClassifier
from sklearn.model_selection import train_test_split
from backend.config import Config

ML_MODEL_AVAILABLE = False
dt_model = None
symptoms_columns = []
symptom_dictionary = {}
symptoms_display_list = []

def init_ml(app=None):
    global ML_MODEL_AVAILABLE, dt_model, symptoms_columns, symptom_dictionary, symptoms_display_list
    try:
        # Search in frontend/static/Data or static/Data
        data_path = os.path.join(Config.STATIC_FOLDER, "Data", "Training.csv")
        if not os.path.exists(data_path):
            data_path = os.path.join(Config.BASE_DIR, "static", "Data", "Training.csv")
            
        if os.path.exists(data_path):
            data = pd.read_csv(data_path)
            df = pd.DataFrame(data)
            cols = df.columns[:-1]
            x = df[cols]
            y = df['prognosis']
            x_train, x_test, y_train, y_test = train_test_split(x, y, test_size=0.33, random_state=42)
            
            dt_model = DecisionTreeClassifier()
            dt_model.fit(x_train, y_train)
            
            symptoms_columns = df.columns.values[:-1]
            symptom_dictionary = dict(zip(symptoms_columns, range(len(symptoms_columns))))
            ML_MODEL_AVAILABLE = True
            print("SUCCESS: Disease prediction ML model loaded.")
        else:
            print("WARNING: Training dataset not found. ML model disabled.")
    except Exception as e:
        print(f"WARNING: ML model load failed: {e}")
        ML_MODEL_AVAILABLE = False

    # Load symptoms list for form dropdowns
    try:
        test_path = os.path.join(Config.STATIC_FOLDER, "Data", "Testing.csv")
        if not os.path.exists(test_path):
            test_path = os.path.join(Config.BASE_DIR, "static", "Data", "Testing.csv")
        if os.path.exists(test_path):
            with open(test_path, newline='') as f:
                reader = csv.reader(f)
                symptoms_display_list = next(reader)[:-1]
    except Exception as e:
        print(f"WARNING: Could not load symptoms display list: {e}")
        symptoms_display_list = []

init_ml_model = init_ml

def predict_disease_ml(selected_symptoms):
    """
    Predict disease and calculate probability score based on selected symptoms.
    """
    if not ML_MODEL_AVAILABLE or not dt_model:
        return "General Viral Symptom Complex", 75.0
        
    user_input_label = [0] * len(symptoms_columns) if len(symptoms_columns) > 0 else [0] * 132
    for s in selected_symptoms:
        if s in symptom_dictionary:
            user_input_label[symptom_dictionary[s]] = 1
            
    user_input = np.array(user_input_label).reshape(1, -1)
    disease = dt_model.predict(user_input)[0]
    confidence = float(np.max(dt_model.predict_proba(user_input)) * 100)
    return disease, confidence

predict_disease = predict_disease_ml

def get_symptoms_list():
    return symptoms_display_list

# Backward compatible attribute alias
class _SymptomsProxy(list):
    def __iter__(self):
        return iter(symptoms_display_list)
    def __len__(self):
        return len(symptoms_display_list)
    def __getitem__(self, item):
        return symptoms_display_list[item]

symptoms_list = _SymptomsProxy()
