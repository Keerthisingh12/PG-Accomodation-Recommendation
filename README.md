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

```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python main.py