from fastapi import FastAPI
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from pymongo import MongoClient
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import os
from dotenv import load_dotenv
from fastapi.encoders import jsonable_encoder
from bson import ObjectId
import numpy as np
import requests
import uvicorn
from datetime import datetime, timezone
from services import UserService
from models import UserAssessment, UserPreferences
from data_sources import (
    db,
    locations_collection,
    jobs_collection,
    skills_collection,
    education_levels_collection,
    career_goals_collection,
    initialize_all_collections
)
from fastapi.middleware.cors import CORSMiddleware

load_dotenv()

app = FastAPI()

app.add_middleware(
  CORSMiddleware,
  allow_origins=["https://career-ease-frontend.vercel.app"],
  allow_credentials=True,
  allow_methods=["*"],
  allow_headers=["*"],
)

@app.on_event("startup")
async def startup_event():
    """Initialize collections when the application starts"""
    await initialize_all_collections()

# Load model
model = SentenceTransformer('all-MiniLM-L6-v2')

# Pydantic models for validation
class UserPreferences(BaseModel):
    skills: List[str]
    years_of_experience: int
    career_goals: str
    education_level: str
    location_preference: str

# Fetch jobs from Adzuna
def fetch_jobs_from_adzuna(country_code: str):
    api_key = os.getenv("ADZUNA_APP_KEY")
    app_id = os.getenv("ADZUNA_APP_ID")
    if not api_key or not app_id:
        print("Adzuna credentials not found")
        return []
    
    url = f"https://api.adzuna.com/v1/api/jobs/{country_code}/search/1"
    params = {
        "app_id": app_id,
        "app_key": api_key,
        "results_per_page": 20,
        "content-type": "application/json",
        "what": "software engineer",
        "sort_by": "date",
    }
    
    try:
        response = requests.get(url, params=params)
        print(f"Adzuna API Response Status: {response.status_code}")
        
        if response.status_code != 200:
            print(f"Error fetching jobs from Adzuna: {response.text}")
            return []
        
        jobs_data = response.json()
        results = jobs_data.get('results', [])
        print(f"Adzuna API returned {len(results)} jobs")
        return results
        
    except Exception as e:
        print(f"Exception in Adzuna API call: {str(e)}")
        return []

# Fetch jobs from MongoDB
def fetch_jobs_from_mongo():
    jobs = list(jobs_collection.find().limit(100))
    return jobs

# Recommendation logic
def get_recommendations(user_input, jobs):
    job_descriptions = [f"{job.get('title', '')} {job.get('description', '')}" for job in jobs]
    job_embeddings = model.encode(job_descriptions)
    user_embedding = model.encode([user_input])
    similarities = cosine_similarity(user_embedding, job_embeddings)
    top_indices = np.argsort(similarities[0])[::-1][:10]
    return [jobs[i] for i in top_indices]

@app.get("/")
async def root():
    return {"message": "FastAPI is running!"}

@app.post("/recommend-jobs/")
async def recommend_jobs(user_preferences: UserPreferences):
    # Get country code from locations collection
    location = locations_collection.find_one(
        {"name": user_preferences.location_preference},
        {"code": 1}
    )
    country_code = location.get("code", "us") if location else "us"
    print(f"Searching jobs for country code: {country_code}")
    
    # Fetch jobs for specific location
    jobs = fetch_jobs_from_adzuna(country_code)
    print(f"Adzuna API returned {len(jobs)} jobs")
    
    if not jobs:
        print("No jobs from Adzuna, trying MongoDB...")
        jobs = fetch_jobs_from_mongo()
        print(f"MongoDB returned {len(jobs)} jobs")
        if not jobs:
            return {"message": "No jobs found for the specified location"}
            
    user_input = f"Skills: {', '.join(user_preferences.skills)}. Years of Experience: {user_preferences.years_of_experience}. Goals: {user_preferences.career_goals}. Education: {user_preferences.education_level}. Location: {user_preferences.location_preference}."

    recommendations = get_recommendations(user_input, jobs)

    recommended_jobs = []
    for job in recommendations[:5]:
        recommended_jobs.append({
            "title": job.get("title", "Unknown Title"),
            "company": job.get("company", {}).get("display_name", "Unknown"),
            "location": job.get("location", {}).get("display_name", "Remote"),
            "salary_min": job.get("salary_min", ""),
            "salary_max": job.get("salary_max", ""),
            "salary_currency": job.get("salary_currency", "USD"),
            "contract_time": job.get("contract_time", "Unknown"),
            "required_skills": ', '.join(job.get("category", {}).get("tag", "").split(',')) if job.get("category") else "N/A",
            "description": job.get("description", "No description available"),
            "application_url": job.get("redirect_url", ""),
            "posted_date": job.get("created", "Unknown").strftime('%Y-%m-%d') if isinstance(job.get("created"), datetime) else 'Unknown',
            "expiry_date": job.get("expires", "Unknown").strftime('%Y-%m-%d') if isinstance(job.get("expires"), datetime) else 'Unknown',
            "recommended_for_experience_level": f"{user_preferences.years_of_experience}+ years",
        })

    return {"recommended_jobs": recommended_jobs}

user_service = UserService(db)

@app.post("/user/assessment")
async def submit_assessment(assessment: UserAssessment):
    await user_service.save_assessment(assessment)
    return {"message": "Assessment saved successfully"}

@app.get("/user/preferences/{email}")
async def get_preferences(email: str):
    return await user_service.get_user_preferences(email)

def convert_objectid_to_str(document):
    """Recursively converts ObjectId fields in a document to string"""
    if isinstance(document, list):
        return [convert_objectid_to_str(doc) for doc in document]
    elif isinstance(document, dict):
        return {k: str(v) if isinstance(v, ObjectId) else convert_objectid_to_str(v) for k, v in document.items()}
    else:
        return document

@app.get("/available-options/")
async def get_available_options():
    """Get all available options for frontend dropdowns."""
    skills = list(skills_collection.find({}, {"_id": 0}))
    locations = list(locations_collection.find({}, {"_id": 0}))
    education_levels = list(education_levels_collection.find({}, {"_id": 0}))
    career_goals = list(career_goals_collection.find({}, {"_id": 0}))

    return {
        "skills": [skill["name"] for skill in skills],
        "locations": [loc["name"] for loc in locations],
        "education_levels": [level["name"] for level in education_levels],
        "career_goals": [goal["name"] for goal in career_goals]
    }