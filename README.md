# Job Recommender API

## Setup

1. Clone the repository
2. Create a virtual environment:
```bash
python -m venv env
source env/bin/activate 
(On Windows) => env\Scripts\activate
```
3. Install dependencies:
```bash
pip install -r requirements.txt
```
4. Copy `.env.sample` to `.env` and fill in your credentials:
- MongoDB URI
- Adzuna API credentials (from https://developer.adzuna.com/)
- APILayer key (from https://apilayer.com/marketplace/skills-api)

## Running the Application

```bash
uvicorn main:app --reload
```
The server will start at: http://127.0.0.1:8000

## API Endpoints

### 1. Get Available Options
Fetches all dropdown options for the assessment form.
```bash
GET /available-options/

Response:
{
"skills": ["Python", "JavaScript", "React", ...],
"locations": ["United States", "United Kingdom", ...],
"education_levels": ["Bachelor's Degree", "Master's Degree", ...],
"career_goals": ["Software Engineer", "Data Scientist", ...]
}
```

### 2. Submit User Assessment
Saves user's complete assessment.
```bash
POST /user/assessment

Content-Type: application/json
{
"name": "John Doe",
"email": "john.doe@example.com",
"phone": "+1234567890",
"current_skills": ["Python", "JavaScript", "React"],
"target_skills": ["Machine Learning", "AWS", "Docker"],
"years_of_experience": 3,
"career_goals": "Software Engineer",
"education_level": "Bachelor's Degree",
"location_preference": "India"
}
```

### 3. Get User Preferences
Retrieves saved preferences for a user.
```bash
GET /user/preferences/john.doe@example.com

Response:
{
"skills": ["Python", "JavaScript", "React"],
"years_of_experience": 3,
"career_goals": "Software Engineer",
"education_level": "Bachelor's Degree",
"location_preference": "India"
}
```

### 4. Get Job Recommendations
Get personalized job recommendations.
```bash
POST /recommend-jobs/

Content-Type: application/json
{
"skills": ["Python", "JavaScript", "React"],
"years_of_experience": 3,
"career_goals": "Software Engineer",
"education_level": "Bachelor's Degree",
"location_preference": "India"
}
```