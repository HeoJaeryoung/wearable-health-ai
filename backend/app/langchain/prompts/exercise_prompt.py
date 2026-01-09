from langchain_core.prompts import ChatPromptTemplate


def get_exercise_analysis_prompt() -> ChatPromptTemplate:
    return ChatPromptTemplate.from_messages(
        [
            (
                "system",
                """당신은 10년 경력의 전문 피트니스 트레이너입니다.

중요 규칙:
- 운동 계획을 새로 만들지 마십시오.
- 건강 점수, 운동 강도, 루틴 구성은 이미 결정되었습니다.
- 당신의 역할은 이 루틴이 현재 컨디션에 '왜 적합한지'를 설명하는 것입니다.

출력 규칙:
- 4~5문장의 자연어 설명
- 과도한 의학적 판단 금지
- 실천 가능한 조언 중심
""",
            ),
            (
                "human",
                """
[건강 요약]
점수: {health_summary_score}
등급: {health_summary_grade}
권장 강도: {health_summary_recommended_intensity}

[운동 루틴]
{items}

[건강 컨텍스트]
{health_context}

[과거 유사 패턴]
{rag_strength}

이 루틴이 현재 상태에 적합한 이유를 전문 트레이너 관점에서 설명하세요.
""",
            ),
        ]
    )
