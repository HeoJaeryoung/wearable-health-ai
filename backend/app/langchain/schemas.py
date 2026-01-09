from pydantic import BaseModel, Field
from typing import List


class ExerciseAnalysisOutput(BaseModel):
    analysis: str = Field(description="운동 루틴에 대한 트레이너 코멘트")
    used_factors: List[str] = Field(description="분석에 사용된 주요 요인")
    confidence: float = Field(description="분석 신뢰도 (0~1)")
