from pydantic import BaseModel
from typing import Dict, List


class HealthAnalysisResponse(BaseModel):
    health_score: Dict
    sleep: Dict
    activity: Dict
    heart_rate: Dict
    exercise_recommendation: Dict
