# test_routine.py
import os

os.environ["EVAL_MODE"] = "baseline"

from app.core.llm_analysis import run_llm_analysis

test_raw = {
    "sleep_hr": 7.5,
    "steps": 8500,
    "heart_rate": 72,
    "resting_heart_rate": 62,
    "active_calories": 380,
    "bmi": 23.5,
    "weight": 72.0,
}

result = run_llm_analysis(
    summary={"raw": test_raw},
    user_id="test_user",
    difficulty_level="중",
    duration_min=10,
)

print("\n" + "=" * 50)
routine = result.get("ai_recommended_routine", {})
items = routine.get("items", [])
print(f"운동 개수: {len(items)}")

total_sec = 0
for item in items:
    item_sec = (item.get("duration_sec", 30) * item.get("set_count", 3)) + (
        item.get("rest_sec", 15) * (item.get("set_count", 3) - 1)
    )
    total_sec += item_sec
    print(f'  - {item.get("exercise_name")}: {item_sec}초')

print(f"실제 총 시간: {total_sec}초 (목표 600초)")
print(f"정확도: {total_sec/600*100:.1f}%")
