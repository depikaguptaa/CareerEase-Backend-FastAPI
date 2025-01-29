from fastapi import HTTPException
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError
import requests
import os
from typing import List
from dotenv import load_dotenv
from datetime import datetime, timedelta

# Load environment variables
load_dotenv()

# Get MongoDB URI
mongodb_uri = os.getenv("MONGO_URI")
if not mongodb_uri:
    raise ValueError("MONGO_URI environment variable is not set. Please check your .env file.")

# Initialize MongoDB connection
try:
    client = MongoClient(mongodb_uri, serverSelectionTimeoutMS=5000)
    # Verify the connection
    client.admin.command('ping')
    print("Successfully connected to MongoDB Atlas!")
    db = client.careerease

except (ConnectionFailure, ServerSelectionTimeoutError) as e:
    print(f"Failed to connect to MongoDB Atlas: {str(e)}")
    print(f"Connection string being used: {mongodb_uri.replace(mongodb_uri.split('@')[0], '***')}")
    raise HTTPException(
        status_code=500,
        detail="Database connection failed. Please check your connection string and make sure your IP is whitelisted in MongoDB Atlas."
    )

# Initialize MongoDB collections
skills_collection = db.skills
locations_collection = db.locations
career_goals_collection = db.career_goals
education_levels_collection = db.education_levels
jobs_collection = db.jobs

# Predefined education levels
EDUCATION_LEVELS = [
    "High School",
    "Associate's Degree",
    "Bachelor's Degree",
    "Master's Degree",
    "PhD",
    "Other"
]

# Predefined career goals
CAREER_GOALS = [
    "Software Engineer",
    "Data Scientist",
    "Product Manager",
    "DevOps Engineer",
    "Full Stack Developer",
    "AI/ML Engineer",
    "Cloud Architect",
    "Security Engineer"
]

async def fetch_skills():
    api_key = os.getenv("APILAYER_API_KEY")
    if not api_key:
        raise HTTPException(
            status_code=500,
            detail="APILAYER_API_KEY not found in environment variables. Please check your .env file."
        )

    try:
        # List of queries to get a broader range of skills
        queries = [
            "software", "programming", "web", "data", "cloud",
            "devops", "security", "database", "frontend", "backend",
            "mobile", "ai", "machine learning", "analytics"
        ]
        
        all_skills = set()  # Use set to avoid duplicates
        
        for query in queries:
            url = f"https://api.apilayer.com/skills?q={query}"
            headers = {
                "apikey": api_key
            }
            
            response = requests.get(url, headers=headers)
            
            if response.status_code == 401:
                raise HTTPException(
                    status_code=401,
                    detail="Invalid API key. Please check your APILayer API key."
                )
            elif response.status_code != 200:
                print(f"Error fetching skills for query '{query}': {response.text}")
                continue
                
            skills_data = response.json()
            all_skills.update(skills_data)  # Add new skills to set
        
        # Convert set to list of dictionaries
        skills = [{"name": skill} for skill in sorted(all_skills)]
        
        # Store in MongoDB
        if skills:
            try:
                # Clear existing skills before inserting new ones
                skills_collection.delete_many({})
                skills_collection.insert_many(skills)
            except Exception as e:
                raise HTTPException(
                    status_code=500,
                    detail=f"Database error while storing skills: {str(e)}"
                )
        
        return skills
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Skills API error: {str(e)}"
        )

async def get_skills():
    try:
        # Explicitly exclude _id field and convert cursor to list
        skills = list(skills_collection.find({}, {"_id": 0}))
        if not skills:
            return await fetch_skills()
        return [{"name": skill["name"]} for skill in skills]
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching skills: {str(e)}"
        )

async def fetch_locations():
    try:
        response = requests.get("https://restcountries.com/v3.1/all")
        if response.status_code != 200:
            raise HTTPException(
                status_code=response.status_code,
                detail="Failed to fetch locations from external API"
            )
            
        countries = [
            {
                "name": country["name"]["common"],
                "code": country["cca2"].lower(),
                "region": country["region"]
            } 
            for country in response.json()
        ]
        
        # Clear existing locations before inserting new ones
        locations_collection.delete_many({})
        locations_collection.insert_many(countries)
        return countries
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

async def get_locations():
    try:
        # Explicitly exclude _id field and convert cursor to list
        locations = list(locations_collection.find({}, {"_id": 0}))
        if not locations:
            # Clear existing locations before fetching new ones
            locations_collection.delete_many({})
            locations = await fetch_locations()
            
        # Ensure we're returning a clean, serializable format
        return [{
            "name": str(loc.get("name", "")),
            "code": str(loc.get("code", "")),
            "region": str(loc.get("region", ""))
        } for loc in locations]
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching locations: {str(e)}"
        )

async def get_education_levels():
    return EDUCATION_LEVELS

async def get_career_goals():
    return CAREER_GOALS

def initialize_sample_jobs():
    if jobs_collection.count_documents({}) == 0:
        sample_jobs = [
            {
                "title": "Software Engineer",
                "company": {"display_name": "Tech Corp"},
                "location": {"display_name": "New York, NY"},
                "description": "Looking for a skilled software engineer...",
                "salary_min": 80000,
                "salary_max": 120000,
                "salary_currency": "USD",
                "contract_time": "full_time",
                "category": {"tag": "python,javascript,react"},
                "created": datetime.now(),
                "expires": datetime.now() + timedelta(days=30),
                "redirect_url": "https://example.com/apply"
            },
            # Add more sample jobs as needed
        ]
        jobs_collection.insert_many(sample_jobs)

async def initialize_all_collections():
    # Initialize predefined education levels
    if education_levels_collection.count_documents({}) == 0:
        education_levels = [{"name": level} for level in EDUCATION_LEVELS]
        education_levels_collection.insert_many(education_levels)
    
    # Initialize predefined career goals
    if career_goals_collection.count_documents({}) == 0:
        career_goals = [{"name": goal} for goal in CAREER_GOALS]
        career_goals_collection.insert_many(career_goals)
    
    # Fetch and store locations
    if locations_collection.count_documents({}) == 0:
        await fetch_locations()
    
    # Fetch and store skills
    if skills_collection.count_documents({}) == 0:
        await fetch_skills()
    
    # Initialize sample jobs
    initialize_sample_jobs() 