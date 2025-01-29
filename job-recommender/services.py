from models import UserAssessment, UserPreferences
from fastapi import HTTPException
from datetime import datetime, timezone
from bson import json_util
import json

class UserService:
    def __init__(self, db):
        self.user_collection = db.users
        self.preferences_collection = db.user_preferences

    async def save_assessment(self, assessment: UserAssessment):
        try:
            # Save full assessment
            user_data = assessment.dict()
            user_data["created_at"] = datetime.now(timezone.utc)
            result = self.user_collection.insert_one(user_data)
            
            # Create and save preferences subset
            preferences = UserPreferences(
                skills=assessment.current_skills,
                years_of_experience=assessment.years_of_experience,
                career_goals=assessment.career_goals,
                education_level=assessment.education_level,
                location_preference=assessment.location_preference
            )
            
            preferences_data = preferences.dict()
            preferences_data["user_id"] = result.inserted_id
            preferences_data["email"] = assessment.email
            
            self.preferences_collection.insert_one(preferences_data)
            
            return {
                "message": "Assessment saved successfully",
                "user_id": str(result.inserted_id)
            }
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Error saving assessment: {str(e)}"
            )

    async def get_user_preferences(self, email: str) -> UserPreferences:
        try:
            preferences = self.preferences_collection.find_one(
                {"email": email},
                {"_id": 0, "user_id": 0, "email": 0}
            )
            
            if not preferences:
                raise HTTPException(status_code=404, detail="User preferences not found")
            
            return UserPreferences(**preferences)
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Error fetching user preferences: {str(e)}"
            ) 