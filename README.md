# ArogyaX

**A unified digital healthcare ecosystem connecting patients, doctors, specialists, and AI.**

---

## 🎯 Project Vision

To connect patients, doctors, specialists and AI in a single digital healthcare ecosystem.

The long-term vision of ArogyaX is to make healthcare:

- More accessible
- More connected
- More organized
- More data-driven
- More efficient
- Easier to access remotely

...while ensuring that **AI supports doctors rather than replacing them**.

---

## 🚀 Key Features

### 👤 1. Role-Based Access

ArogyaX provides different workflows according to the user's role.

| Role | Capabilities |
|---|---|
| **Patient** | Register, manage profile, maintain medical records, book appointments, use AI tools, attend consultations |
| **Doctor** | Manage appointments, review patient history, conduct consultations, prescribe medicines, access AI assistance |
| **Specialist** | Participate in specialized and second-opinion consultations |
| **Admin** | Manage users, doctors, platform operations and system statistics |

### 📝 2. Digital Patient Case Taking

ArogyaX converts traditional patient case-taking into a structured digital workflow. Doctors can record:

- Chief Complaint
- History of Present Illness
- Past Medical History
- Family History
- Personal and Social History
- Current Medications
- Allergies
- Symptoms
- Vitals
- Physical Examination
- Assessment
- Treatment Plan
- Follow-up Information

This structured information helps doctors understand the patient's current condition while maintaining a continuous medical history.

### 📁 3. Medical Vault

A centralized repository for patient healthcare documents:

- Laboratory reports
- X-rays
- Medical images
- Prescriptions
- PDFs
- Previous medical documents
- Other healthcare records

The Medical Vault allows relevant medical history to be reviewed during future consultations.

### 🤖 4. AI-Powered Clinical Decision Support

ArogyaX uses different AI approaches depending on the type of medical data.

```
                         Patient Case
                              │
             ┌────────────────┼────────────────┐
             │                │                │
          Symptoms        Risk Factors     Chest X-Ray
             │                │                │
             ▼                ▼                ▼
       Disease Random    Lung Cancer        CNN
          Forest          Random Forest
             │                │                │
             └────────────────┼────────────────┘
                              │
                              ▼
                    AI Decision Support
                              │
                              ▼
                        Doctor Review
                              │
                              ▼
                   Final Clinical Decision
```

The project contains three main trained ML/DL components:

1. General Disease Prediction
2. Lung Cancer Prediction
3. Pneumonia Detection

Generative AI is additionally used for language-based assistance.

---

## 🧠 AI Model 1 — General Disease Prediction

**Algorithm:** Random Forest Classifier

Predicts a possible disease based on a combination of symptoms.

**Dataset**
- 4,920 records
- 132 symptom features
- 41 disease classes

Symptoms are represented primarily as binary features, e.g.:

```
Itching          → 1
Skin Rash        → 1
Joint Pain       → 0
Chills           → 1
Stomach Pain     → 0
```

**Training Process**

```
Dataset → Data Cleaning → Symptom Features → Train/Validation Split
   → Random Forest → Prediction → Evaluation
```

Split: 80% Training / 20% Validation (984 validation samples)

**Model Configuration**
```python
RandomForestClassifier(
    n_estimators=100,
    max_features=85,
    random_state=42
)
```

**Reported Performance:** 100% validation accuracy*

*Based on the provided validation split — should not be interpreted as real-world clinical diagnostic accuracy.*

---

## 🫁 AI Model 2 — Lung Cancer Prediction

**Algorithm:** Random Forest Classifier

Uses demographic, lifestyle and symptom-related information to predict lung cancer risk.

**Input Features**
Gender, Age, Smoking, Yellow Fingers, Anxiety, Peer Pressure, Chronic Disease, Fatigue, Allergy, Wheezing, Alcohol Consumption, Coughing, Shortness of Breath, Swallowing Difficulty, Chest Pain

**Dataset Processing**
- Original: 309 records, 16 columns
- After deduplication: 276 records
- Class imbalance addressed via **ADASYN** (Adaptive Synthetic Sampling)
- After resampling: 477 samples
- Split: 75% Training / 25% Testing

**Reported Performance**
- Direct test split: 98% Accuracy
- 10-fold stratified cross-validation: ≈94.6% average accuracy

> ⚠️ The dataset is relatively small. The current training notebook applies ADASYN *before* the train/test split, which can introduce data leakage. A production implementation should apply resampling only to training data/folds.

---

## 🩻 AI Model 3 — Pneumonia Detection

**Algorithm:** Convolutional Neural Network (CNN)

Analyzes chest X-ray images and classifies them into **NORMAL** or **PNEUMONIA**.

**Dataset:** 5,863 grayscale chest X-ray images across 2 classes.

**Image Preprocessing**
```
Original Chest X-Ray → Grayscale Conversion → Resize to 150×150
   → Pixel Normalization → Data Augmentation → CNN
```

Input Shape: `150 × 150 × 1`

**Data Augmentation:** Rotation, Zoom, Width shifting, Height shifting, Horizontal flipping.

**CNN Architecture**
```
Input: 150×150×1
  → Conv2D (32) → BatchNorm → MaxPooling
  → Conv2D (64) → Dropout → BatchNorm → MaxPooling
  → Conv2D (64) → BatchNorm → MaxPooling
  → Conv2D (128) → Dropout → BatchNorm → MaxPooling
  → Conv2D (256) → Dropout → BatchNorm → MaxPooling
  → Flatten → Dense (128) → Dropout → Sigmoid
  → NORMAL / PNEUMONIA
```

**Training**
- Optimizer: RMSprop
- Loss: Binary Cross-Entropy
- Epochs: 12
- Batch Size: 32
- `ReduceLROnPlateau` callback used to reduce learning rate on plateau

**Reported Performance:** Final test accuracy — 92.63%

| Class | Precision | Recall | F1-Score |
|---|---|---|---|
| Pneumonia | 0.93 | 0.96 | 0.94 |
| Normal | 0.92 | 0.88 | 0.90 |
| **Overall** | - | - | **0.92** |

> ⚠️ The dataset is primarily pediatric chest X-rays, so the model may not generalize across all age groups, hospitals, imaging devices, or populations. The current notebook also applies augmentation to the validation generator — production evaluation should keep validation/test data unaugmented.

---

## ✨ Generative AI Assistance

ArogyaX can integrate **Gemini 2.5 Flash** for natural-language healthcare assistance:

- Medical case summarization
- Structuring patient information
- Simplifying complex medical information
- Highlighting important information
- Assisting doctors in reviewing case details
- Generating understandable explanations

```
Traditional ML/DL → Prediction / Classification
Generative AI     → Summary / Explanation / Assistance
```

The Generative AI layer is separate from the trained ML/DL models.

---

## 👨‍⚕️ Doctor-in-the-Loop

```
Patient Data → AI Analysis → AI Prediction/Assistance
   → Doctor Reviews Output → Doctor Uses Clinical Judgment
   → Final Assessment
```

**Why?** Medical AI should assist healthcare professionals rather than independently making clinical decisions. AI provides decision support — the doctor makes the final clinical decision.

---

## 📹 Telemedicine

Video consultation functionality for remote doctor-patient consultations. Patients can select a doctor, book an appointment, receive confirmation, join a video consultation, discuss their case, and receive a prescription afterward.

---

## 🌍 Specialist & International Consultation

Enables doctors to involve specialists (from another city, state, or country) when additional expertise is required.

```
Patient → Primary Doctor → Complex Case Identified → Specialist Required
   → Specialist Joins Video Consultation → Expert Opinion/Second Opinion
   → Primary Doctor → Final Clinical Decision
```

**Benefits:** access to rare expertise, second opinions, specialized consultation, reduced travel, better doctor-to-doctor collaboration, access to experts unavailable locally.

The specialist provides additional expertise while the primary doctor remains responsible for the overall clinical decision.

> Cross-border medical consultations would require compliance with applicable medical licensing, telemedicine, privacy, payment, and jurisdictional regulations in a real-world deployment.

---

## 🏥 Appointment Management

**Patients:** Browse doctors, select specialization, book appointments, view status, attend consultations, access prescriptions.

**Doctors:** View pending appointments, approve appointments, review patient information, conduct consultations, prescribe medicines.

---

## 💊 Digital Prescription

After a consultation, doctors generate digital prescriptions containing doctor/patient information, medicines, dosage & instructions, and the doctor's signature. Patients can access and download prescriptions as a PDF.

---

## 📰 Health Information / Blog

Healthcare-related educational content across categories such as Nutrition, Holistic Health, General Healthcare, Lifestyle, and Preventive Healthcare.

---

## ⭐ What Makes ArogyaX Unique?

ArogyaX is not simply a disease prediction model — its uniqueness comes from integrating multiple healthcare technologies into a single ecosystem.

1. **Multi-Modal AI** — Symptoms + Structured Medical Data + Risk Factors + Medical Images + Natural Language
2. **Multiple AI Models** — Random Forest + Random Forest + CNN + Generative AI
3. **Complete Healthcare Workflow** — Case Taking → Medical History → AI Assistance → Doctor Consultation → Specialist Consultation → Prescription → Medical Record → Follow-up
4. **Doctor + AI Collaboration** — AI provides decision support; the doctor makes the clinical decision
5. **Remote Specialist Access** — Telemedicine architecture enabling remote access to specialized expertise

---

## 💼 Business Model

A combination of **Healthcare SaaS + Telemedicine + AI-assisted Healthcare**.

### Revenue Streams

1. **Doctor Consultation Fees** — Patients pay for online consultations
2. **Specialist Consultation Fees** — Premium rates for specialized/international expert consultations
3. **Platform Commission** — Service fee on consultations conducted through the platform
4. **Hospital / Clinic Subscription** — Digital case-taking, patient management, records, appointments, AI assistance, telemedicine
5. **Enterprise Healthcare Plans** — Customized plans/deployments for large healthcare organizations
6. **Premium AI Features** — Advanced AI-assisted features in premium plans

```
Patient → Consultation Payment → ArogyaX Platform
   ├── Platform/Service Fee
   └── Doctor/Specialist Payment
```

### Example Business Scenario

```
Patient → Local Doctor Consultation → Complex Case Identified
   → Specialist Required → Specialist Consultation → ArogyaX Platform
      ├── Platform/Service Fee
      └── Specialist Receives Consultation Fee
```

> Actual consultation charges and commission percentages depend on the final business implementation.

---

## 🧩 System Architecture

```
                         AROGYAX
                            │
        ┌───────────────────┼───────────────────┐
        │                   │                   │
     PATIENT             DOCTOR              ADMIN
        │                   │                   │
        └───────────────────┼───────────────────┘
                            │
                       Flask Backend
                            │
          ┌─────────────────┼─────────────────┐
          │                 │                 │
     Medical Data        AI Services      Telemedicine
          │                 │                 │
          │       ┌─────────┼─────────┐       │
          │       │         │         │       │
          │   Disease RF  Lung RF    CNN      │
          │       │         │         │       │
          │       └─────────┼─────────┘       │
          │                 │                 │
          └─────────────────┼─────────────────┘
                            │
                       MongoDB Atlas
```

---

## 🛠️ Technology Stack

| Layer | Technology |
|---|---|
| Frontend | HTML5, CSS3, Vanilla JavaScript |
| Backend | Python 3.10+, Flask |
| Database | MongoDB Atlas, PyMongo |
| Machine Learning | Scikit-learn |
| Disease Model | Random Forest |
| Lung Cancer Model | Random Forest + ADASYN |
| Deep Learning | TensorFlow / Keras |
| Pneumonia Model | CNN |
| Image Processing | OpenCV |
| Generative AI | Gemini 2.5 Flash |
| PDF Generation | ReportLab |
| Authentication | Flask Sessions + Bcrypt |
| Email | Flask-Mail / Gmail SMTP |
| Deployment | Cloud Deployment |

---

## 📊 AI Performance Summary

| AI Module | Model | Dataset | Reported Performance |
|---|---|---|---|
| General Disease | Random Forest | 4,920 records | 100% validation accuracy* |
| Lung Cancer | Random Forest | 477 after ADASYN | 98% test accuracy |
| Lung Cancer CV | Random Forest | 10-fold Stratified CV | ≈94.6% average accuracy |
| Pneumonia | CNN | 5,863 X-rays | 92.63% test accuracy |

*The general disease result is based on the provided validation split and should not be interpreted as clinical accuracy.*

---

## 📁 Project Structure

```
ArogyaX/
│
├── app.py
├── requirements.txt
├── .env
├── .gitignore
├── LICENSE
├── README.md
│
├── static/
│   ├── css/
│   │   └── style.css
│   │
│   ├── js/
│   │   └── script.js
│   │
│   ├── images/
│   │   ├── logos
│   │   ├── illustrations
│   │   └── doctor photos
│   │
│   ├── Data/
│   │   └── ML datasets
│   │
│   ├── uploads/
│   │   └── profile_photos/
│   │
│   └── prescriptions/
│       └── generated PDFs
│
├── templates/
│   ├── index.html
│   ├── login.html
│   ├── patient-register.html
│   ├── patient-profile.html
│   ├── patient-dashboard.html
│   ├── book-appointment.html
│   ├── doctor-register.html
│   ├── doctor-dashboard.html
│   ├── doctor-patients.html
│   ├── doctor-profile-edit.html
│   ├── doctors.html
│   ├── prescribe-medicine.html
│   ├── admin-login.html
│   ├── admin.html
│   ├── disease_predict.html
│   ├── brain-tumor.html
│   ├── lung.html
│   ├── cataract.html
│   ├── videocall.html
│   ├── privacy-policy.html
│   └── blog_*.html
│
└── notebooks/
    ├── disease-prediction/
    ├── lung-cancer-prediction/
    ├── pneumonia-prediction/
    └── other AI research notebooks
```

---

## ⚡ Quick Start

### Prerequisites

- Python 3.10+
- MongoDB Atlas account
- Google Gemini API key
- Git

### 1. Clone the Repository

```bash
git clone https://github.com/souvik082003/ArogyaX.git
cd ArogyaX
```

### 2. Create a Virtual Environment

**Windows**
```bash
python -m venv venv
venv\Scripts\activate
```

**macOS / Linux**
```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables

Create a `.env` file in the project root:

```env
MONGO_URI=mongodb+srv://<username>:<password>@<cluster>.mongodb.net/arogyax?retryWrites=true&w=majority

GEMINI_API_KEY=your_gemini_api_key_here

SECRET_KEY=your_secret_key_here

MAIL_USERNAME=your_email@gmail.com
MAIL_PASSWORD=your_app_password
MAIL_DEFAULT_SENDER=your_email@gmail.com
```

> **Important:** Never commit `.env` or API keys to GitHub. Make sure `.env` is included in `.gitignore`.

### 5. Run the Application

```bash
python app.py
```

The application will normally be available at: **http://localhost:5000**

---

## 🔐 Authentication

ArogyaX uses:

- Flask sessions
- Bcrypt password hashing
- Role-based access

Different dashboards are provided for Patient, Doctor, and Admin.

---

## 🩺 Main API Routes

| Method | Route | Description |
|---|---|---|
| GET | `/` | Landing page / Patient dashboard |
| GET/POST | `/login` | Patient login |
| GET/POST | `/patient-register` | Patient registration |
| GET/POST | `/doctor-register` | Doctor registration |
| GET/POST | `/admin-login` | Admin login |
| GET | `/admin-dashboard` | Admin dashboard |
| GET/POST | `/book-appointment` | Appointment booking |
| GET/POST | `/disease-predict` | Disease prediction |
| GET/POST | `/brain-tumor` | Brain scan analysis |
| GET/POST | `/lung` | Lung analysis |
| GET/POST | `/cataract` | Cataract analysis |
| GET | `/doctors` | Doctor directory |
| GET/POST | `/doctor-profile-edit` | Doctor profile |
| GET | `/doctor-patients` | Doctor patient list |
| GET | `/videocall` | Telemedicine |
| GET | `/profile` | Patient profile |
| GET | `/api/health` | Health check |
| GET | `/seed-demo` | Seed demo data |

---

## 🧪 AI Development Pipeline

**General Disease Prediction**
```
Dataset → Data Cleaning → Symptom Feature Extraction → Train/Validation Split
   → Random Forest Training → Validation → Prediction
```

**Lung Cancer Prediction**
```
Dataset → Duplicate Removal → Feature Processing → ADASYN
   → Train/Test Split → Random Forest Training → Evaluation
```

**Pneumonia Detection**
```
Chest X-Rays → Grayscale Conversion → Resize → Normalization
   → Data Augmentation → CNN Training → Testing
```

---

## 🔬 Model Evaluation

Models are evaluated using: Accuracy, Precision, Recall, F1-score, Classification reports, Stratified cross-validation.

For healthcare AI, accuracy alone is not sufficient. Future production evaluation should also consider:

- Sensitivity
- Specificity
- ROC-AUC
- PR-AUC
- Calibration
- Confusion Matrix
- External Validation

---

## ⚠️ Current Limitations

ArogyaX is currently an academic/prototype healthcare platform. **The reported AI performance should not be interpreted as clinical validation.**

**General Disease Model** — The reported 100% validation accuracy may reflect the characteristics of the provided dataset and does not guarantee equivalent performance on real-world patients.

**Lung Cancer Model** — The dataset is relatively small. The current notebook also performs ADASYN before the train/test split, which may introduce data leakage. A production implementation should perform resampling only on the training portion.

**Pneumonia Model** — The dataset is primarily pediatric chest X-rays, so the model may not generalize to all age groups, hospitals, imaging devices, or populations. The current notebook also uses augmentation in the validation generator; a production evaluation pipeline should keep validation and test data unaugmented.

---

## 🔐 Security & Privacy

Healthcare data is sensitive. A production version should implement:

- HTTPS
- Strong authentication
- Role-based authorization
- Encryption
- Secure document storage
- Patient consent
- Audit logs
- Secure API communication
- Access logging
- Data retention policies
- Model/version tracking

For international specialist consultations, the platform would also need to comply with applicable medical licensing requirements, telemedicine regulations, data protection laws, patient consent requirements, cross-border healthcare regulations, and payment regulations.

---

## 🔮 Future Scope

**🧠 Advanced AI**
More disease prediction models, Explainable AI, Confidence calibration, Medical report summarization, Clinical timeline generation, Medical OCR, ECG analysis, Advanced medical image analysis, Multimodal AI

**👨‍⚕️ Healthcare**
Doctor-to-doctor consultation, Specialist recommendation, Second-opinion network, Hospital Information System integration, Electronic Health Record interoperability

**📱 Patient Experience**
Mobile application, Multilingual healthcare assistance, Medication reminders, Follow-up reminders, Wearable-device integration, Personalized health dashboard

**🌍 Global Healthcare**
International specialist network, Cross-border teleconsultation, Remote second opinions, Global specialist discovery

---

## 📈 Scalability

**Phase 1 — Prototype:** Patient + Doctor → Digital Healthcare Platform → AI Decision Support

**Phase 2 — Hospital Integration:** Patients + Doctors + Hospitals + Laboratories

**Phase 3 — Specialist Network:** Local Doctors + National Specialists + International Specialists

**Phase 4 — Intelligent Healthcare Ecosystem:** Patients, Doctors, Hospitals, Labs, Pharmacies, Specialists, AI Services, Wearables → ArogyaX

---

## 🌟 Why We Chose This Project

Healthcare is a high-impact domain where technology can address real-world problems. We chose ArogyaX because:

- Medical information is often fragmented
- Traditional case-taking can be time-consuming
- Patients may have difficulty accessing specialists
- Doctors need organized patient histories
- AI can assist with large amounts of medical information
- Telemedicine can reduce geographical barriers
- Digital records can improve continuity of care

---

## 🦄 Why Is ArogyaX Unique?

The key innovation is not the invention of a new ML algorithm. Instead, ArogyaX combines Digital Case Taking + Medical Records + Machine Learning + Deep Learning + Generative AI + Telemedicine + Specialist Collaboration — creating an integrated healthcare ecosystem rather than a standalone AI model.

---

## ✅ Feasibility

**Technical Feasibility** — Built on established technologies: Python, Flask, MongoDB, Scikit-learn, TensorFlow, OpenCV, Gemini, HTML, CSS, JavaScript.

**Economic Feasibility** — Relatively low infrastructure costs due to software-based technologies and scalable cloud services.

**Operational Feasibility** — Workflow designed around existing healthcare interactions: Patient → Doctor → AI Assistance → Specialist if Required → Doctor's Final Decision. AI is an additional tool within the healthcare workflow, not a replacement for existing clinical roles.

---

## 🎯 Project Objectives

- Digitize traditional patient case-taking
- Centralize medical information
- Maintain a continuous patient medical history
- Provide AI-assisted decision support
- Analyze symptom-based medical data
- Analyze selected medical images
- Enable remote doctor-patient consultations
- Facilitate specialist and second-opinion consultations
- Generate digital prescriptions
- Improve accessibility to healthcare expertise
- Reduce unnecessary travel for specialist consultation
- Build a scalable healthcare technology ecosystem

---

## 👥 Target Users

**Patients** — Manage health profiles, maintain Medical Vault, book appointments, consult doctors, use AI-assisted tools, attend telemedicine sessions, access prescriptions, maintain medical history

**Doctors** — Manage appointments, review patient history, conduct digital case-taking, review Medical Vault, use AI decision-support tools, prescribe medicines, conduct video consultations, invite specialists

**Specialists** — Provide expert opinions, conduct remote consultations, collaborate with primary doctors, provide second opinions

**Hospitals / Clinics** — Manage doctors and patients, digitize case-taking, manage appointments, maintain medical records, enable telemedicine, use AI-assisted healthcare tools

**Administrators** — Manage users, manage doctors, monitor system activity, manage platform operations

---

## 🧭 Long-Term Product Vision

```
                    AROGYAX
                       │
       ┌───────────────┼────────────────┐
       │               │                │
    Patients         Doctors         Specialists
       │               │                │
       └───────────────┼────────────────┘
                       │
                 AI Assistance
                       │
       ┌───────────────┼────────────────┐
       │               │                │
    Hospitals         Labs          Pharmacies
                       │
                  Medical Data
                       │
                    ArogyaX
```

The platform can eventually become a digital healthcare layer connecting patients, healthcare providers, specialists and AI-enabled healthcare services.

---

## ⚕️ Medical Disclaimer

ArogyaX is an academic/prototype healthcare technology project. The AI models demonstrated in this project are intended for **educational purposes, research, demonstration, and clinical decision-support concepts**.

They should **not** be used as standalone systems for:

- Medical diagnosis
- Treatment decisions
- Prescription
- Emergency decisions
- Patient triage without qualified clinical oversight

**All medical decisions must be made by qualified healthcare professionals.**

---

## 🤝 Contributing

Contributions are welcome.

1. Fork the repository
2. Create a feature branch:
   ```bash
   git checkout -b feature/amazing-feature
   ```
3. Commit your changes:
   ```bash
   git commit -m "Add amazing feature"
   ```
4. Push the branch:
   ```bash
   git push origin feature/amazing-feature
   ```
5. Open a Pull Request

---

## 📄 License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.
