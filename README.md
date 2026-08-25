# 🏠 PG Accommodation Recommendation System

## 📌 Introduction
Finding suitable PG accommodation is difficult due to scattered listings and lack of personalization.  
This project provides an intelligent recommendation system that suggests PGs based on user preferences.

---

## 🎯 Features
- ✔ Preference-based filtering (budget, gender, amenities)
- ✔ Weighted similarity scoring (Euclidean distance)
- ✔ Distance-based recommendation (proximity consideration)
- ✔ Fuzzy location matching (handles spelling variations)
- ✔ Explainable recommendations (Why this PG?)
- ✔ Badge system (Budget Pick, Premium, Best Value)
- ✔ Fallback system (no empty results)
- ✔ Export recommendations to CSV

---

## 🗂 Dataset
- 1000 structured records
- Focused on **Bangalore North**
- Includes locations like Hebbal, Yelahanka, Kalyan Nagar, etc.
- Features:
  - Rent, amenities, availability
  - Latitude & Longitude
  - Distance from center
- Generated using realistic constraints and validated with housing datasets

---

## ⚙️ System Architecture
1. Data Loading & Validation
2. Preprocessing & Feature Engineering
3. Hard Filtering
4. Weighted Scoring
5. Ranking & Rating
6. Explanation Generation
7. Output Display

---

## 🧠 Algorithm
- Weighted Euclidean Distance:
  
  distance = √ Σ wᵢ (pgᵢ - userᵢ)²

- Distance-based scoring:
  
  Closer PG → lower penalty → higher rank

- Final Score:
  
  Final Score = Distance Score - Location Bonus

---

## ▶️ How to Run

### CLI recommender

From the project root, create and activate a virtual environment.

**macOS/Linux**

```bash
python3 -m venv venv
source venv/bin/activate
python3 -m pip install -r requirements.txt
python3 main.py
```

**Windows PowerShell**

```powershell
py -m venv venv
.\venv\Scripts\Activate.ps1
py -m pip install -r requirements.txt
py main.py
```

### Web application

The web application uses PostgreSQL, an ML service, an Express API, and a Vite frontend.

#### 1. Prepare PostgreSQL

Make sure PostgreSQL is running, then create `backend/.env` with:

```env
DATABASE_URL=postgresql://YOUR_USER@localhost:5432/pg_recommendation
ML_SERVICE_URL=http://localhost:8000
PORT=5005
```

Activate the root virtual environment and migrate the dataset:

```bash
python3 -m pip install -r requirements.txt
python3 scripts/migrate_to_db.py
```

#### 2. Install service dependencies

```bash
cd ml-service
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements.txt
deactivate

cd ../backend
npm install

cd ../frontend
npm install
```

On Windows, activate the ML environment with `..\ml-service\.venv\Scripts\Activate.ps1` instead.

#### 3. Start the services

Run each command in a separate terminal from the project root:

```bash
# Terminal 1: ML service
ml-service/.venv/bin/uvicorn ml-service.main:app --host 0.0.0.0 --port 8000

# Terminal 2: API backend
cd backend && npm start

# Terminal 3: frontend
cd frontend && npm run dev
```

Open the frontend at <http://localhost:5173/>.