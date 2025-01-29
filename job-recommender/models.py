from pydantic import BaseModel, EmailStr
from typing import List, Optional

class UserAssessment(BaseModel):
    name: str
    email: EmailStr
    phone: str
    current_skills: List[str]
    target_skills: List[str]
    years_of_experience: int
    career_goals: str
    education_level: str
    location_preference: str

class UserPreferences(BaseModel):
    skills: List[str]
    years_of_experience: int
    career_goals: str
    education_level: str
    location_preference: str 