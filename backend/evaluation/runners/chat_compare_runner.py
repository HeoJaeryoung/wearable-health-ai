import json
from pathlib import Path
from app.services.chat_service import ChatService

DATA_PATH = Path("evaluation/datasets/chat_queries.json")
OUTPUT_PATH = Path("evaluation/results/chat_results.json")

EVAL_MODES = ["baseline", "langchain", "finetuned"]


def run_chat_evaluation():
    chat_service = ChatService()

    with open(DATA_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    results = []

    for case in data["test_cases"]:
        case_id = case["id"]
        message = case["input_data"]["message"]
        character = case["input_data"].get("character", "devil_coach")

        print(f"🧪 {case_id}")

        for mode in EVAL_MODES:
            result = chat_service.handle_chat(
                user_id="eval_user",
                message=message,
                character=character,
                eval_mode=mode,
            )

            results.append(
                {
                    "id": case_id,
                    "eval_mode": mode,
                    "message": message,
                    "character": character,
                    "reply": result["reply"],
                    "model_type": result["model_type"],
                }
            )

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print(f"\n✅ 저장 완료 → {OUTPUT_PATH}")


if __name__ == "__main__":
    run_chat_evaluation()
