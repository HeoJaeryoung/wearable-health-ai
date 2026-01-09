import os, shutil, tempfile, uuid
from pathlib import Path
from datetime import datetime
from fastapi import UploadFile, HTTPException
import asyncio
from concurrent.futures import ThreadPoolExecutor

from app.core.unzipper import extract_zip_to_temp
from app.core.db_to_json import db_to_json
from app.core.db_parser import parse_db_json_to_raw_data_by_day

from app.utils.preprocess import preprocess_health_json
from app.core.vector_store import save_daily_summaries_batch
from app.core.llm_analysis import run_llm_analysis

# 비동기 처리용 Executor
executor = ThreadPoolExecutor(max_workers=4)

# ============================================================
# ZIP 저장 경로 설정
# ============================================================
BASE_DIR = Path(__file__).resolve().parent.parent.parent  # backend/
ZIP_DATA_DIR = BASE_DIR / "zip_data"
UPLOADS_DIR = ZIP_DATA_DIR / "uploads"
EXTRACTED_DIR = ZIP_DATA_DIR / "extracted"

# 디렉토리 생성
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
EXTRACTED_DIR.mkdir(parents=True, exist_ok=True)

# ============================================================
# 파싱 설정 (LangChain 리팩토링)
# ============================================================
PARSE_RECENT_DAYS = 30  # 최근 N일만 파싱 (성능 최적화)


class FileUploadService:
    """
    ZIP/DB 파일 업로드 처리 서비스

    LangChain 리팩토링 개선 사항:
    1. 최근 30일만 파싱 (420일 → 30일, 93% 감소)
    2. 원본 ZIP은 그대로 보관 (필요시 추후 파싱 가능)
    3. 파싱/임베딩 시간 대폭 단축
    """

    @staticmethod
    def get_or_create_user_id(user_id: str | None):
        if not user_id or not user_id.strip():
            return str(uuid.uuid4())
        return user_id

    @staticmethod
    async def run_blocking(func, *args):
        """동기 함수를 비동기로 실행"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(executor, lambda: func(*args))

    @staticmethod
    def detect_platform(filename: str, db_json: dict) -> str:
        """
        플랫폼 자동 감지

        Returns:
            "apple" or "samsung" or "unknown"
        """
        filename_lower = filename.lower()

        # 파일명으로 감지
        if "healthconnect" in filename_lower or "samsung" in filename_lower:
            return "samsung"
        elif (
            "export" in filename_lower
            or "apple" in filename_lower
            or "health" in filename_lower
        ):
            return "apple"

        # DB 구조로 감지 (Samsung Health Connect 특징)
        if db_json:
            samsung_tables = [
                "steps_record_table",
                "distance_record_table",
                "heart_rate_record_table",
            ]
            if all(table in db_json for table in samsung_tables):
                return "samsung"

        return "unknown"

    @staticmethod
    def filter_recent_days(
        raw_by_day: dict, recent_days: int = PARSE_RECENT_DAYS
    ) -> dict:
        """
        최근 N일치 데이터만 필터링

        Args:
            raw_by_day: 전체 날짜별 데이터 {date_int: raw_data}
            recent_days: 가져올 최근 일수 (기본 30일)

        Returns:
            최근 N일치 데이터만 포함된 딕셔너리
        """
        if not raw_by_day:
            return {}

        # 날짜 기준 정렬 (최신순)
        sorted_dates = sorted(raw_by_day.keys(), reverse=True)

        # 최근 N일만 선택
        recent_dates = sorted_dates[:recent_days]

        # 필터링된 데이터 반환
        filtered = {date: raw_by_day[date] for date in recent_dates}

        return filtered

    async def process_file(
        self,
        file: UploadFile,
        user_id: str | None,
        difficulty: str,
        duration: int,
    ):
        user_id = self.get_or_create_user_id(user_id)

        # 사용자별 타임스탬프 디렉토리
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        user_short = user_id.replace("@", "_").replace(".", "_")

        temp_dir = str(EXTRACTED_DIR / f"{user_short}_{timestamp}")
        os.makedirs(temp_dir, exist_ok=True)

        temp_path = os.path.join(temp_dir, file.filename)

        try:
            print(f"[INFO] 파일 업로드 시작: {file.filename}")

            # 1️⃣ 파일 저장
            with open(temp_path, "wb") as buffer:
                buffer.write(await file.read())

            # 원본 파일 보관
            original_save_name = f"{user_short}_{timestamp}_{file.filename}"
            original_save_path = UPLOADS_DIR / original_save_name
            shutil.copy2(temp_path, original_save_path)
            print(f"[INFO] 원본 파일 저장: {original_save_path}")

            # 2️⃣ ZIP 또는 DB 판별
            if file.filename.lower().endswith(".zip"):
                print("[INFO] ZIP 파일 압축 해제 중...")
                db_path = await self.run_blocking(extract_zip_to_temp, temp_path)
            elif file.filename.lower().endswith(".db"):
                db_path = temp_path
            else:
                raise HTTPException(400, "ZIP 또는 DB 파일만 업로드 가능합니다.")

            if not db_path:
                raise HTTPException(500, "DB 파일 경로를 찾을 수 없습니다.")

            # 3️⃣ DB → JSON (비동기 처리)
            print("[INFO] DB 파싱 중...")
            raw_db_json = await self.run_blocking(db_to_json, db_path)

            # 플랫폼 감지
            platform = self.detect_platform(file.filename, raw_db_json)
            print(f"[INFO] 감지된 플랫폼: {platform}")

            # 4️⃣ 날짜별 raw 추출 (전체)
            print("[INFO] 날짜별 데이터 추출 중...")
            raw_by_day_all = await self.run_blocking(
                parse_db_json_to_raw_data_by_day, raw_db_json
            )

            if not raw_by_day_all:
                raise HTTPException(
                    500, "DB Parser가 건강 데이터를 추출하지 못했습니다."
                )

            total_days_in_file = len(raw_by_day_all)
            all_dates = sorted(raw_by_day_all.keys())

            print(f"[INFO] 파일 내 총 {total_days_in_file}일치 데이터 발견")
            if all_dates:
                print(f"[INFO] 전체 날짜 범위: {all_dates[0]} ~ {all_dates[-1]}")

            # ============================================================
            # 🚀 LangChain 최적화: 최근 30일만 파싱
            # ============================================================
            raw_by_day = self.filter_recent_days(raw_by_day_all, PARSE_RECENT_DAYS)
            total_days = len(raw_by_day)
            dates = sorted(raw_by_day.keys())

            print(f"[INFO] ✅ 최근 {PARSE_RECENT_DAYS}일만 처리: {total_days}일")
            print(f"[INFO] 처리 날짜 범위: {dates[0]} ~ {dates[-1]}")
            print(
                f"[INFO] 스킵된 데이터: {total_days_in_file - total_days}일 (원본 ZIP에 보관)"
            )

            # 5️⃣ 최신 날짜 결정
            latest_date = max(raw_by_day.keys())
            latest_raw = raw_by_day[latest_date]

            # 6️⃣ 최신 1일치 summary (분석용)
            print("[INFO] 최신 데이터 전처리 중...")
            latest_summary = await self.run_blocking(
                preprocess_health_json, latest_raw, latest_date, platform
            )

            # 7️⃣ 최근 30일 summary → Vector DB 배치 저장
            print(f"[INFO] VectorDB에 {total_days}일치 데이터 배치 저장 중...")

            all_summaries = []
            for date_int, raw in raw_by_day.items():
                daily_summary = await self.run_blocking(
                    preprocess_health_json,
                    raw,
                    date_int,
                    platform,
                )
                all_summaries.append(daily_summary)

            source = f"zip_{platform}"
            await self.run_blocking(
                save_daily_summaries_batch, all_summaries, user_id, source
            )

            print(
                f"[SUCCESS] {total_days}일치 데이터 VectorDB 저장 완료 (플랫폼: {platform})"
            )

            # 8️⃣ LLM 분석 (최신 데이터만)
            print("[INFO] LLM 분석 실행 중...")
            llm_result = await self.run_blocking(
                run_llm_analysis,
                latest_summary,
                user_id,
                difficulty,
                duration,
            )

            # ✅ 건강 분석 (health_info) 추가
            from app.core.health_interpreter import interpret_health_data

            health_info = await self.run_blocking(
                interpret_health_data, latest_summary.get("raw", {})
            )

            print("[SUCCESS] 분석 완료")

            # 저장 정보 로그
            print(f"\n{'='*70}")
            print(f"📦 파일 저장 정보:")
            print(f"  • 파일 타입: {file.filename.split('.')[-1].upper()}")
            print(f"  • 원본 파일: {original_save_path}")
            print(f"  • 압축 해제: {temp_dir}")
            print(f"  • 플랫폼: {platform}")
            print(f"  • 파일 내 전체: {total_days_in_file}일")
            print(f"  • 실제 처리: {total_days}일 (최근 {PARSE_RECENT_DAYS}일)")
            print(f"  • 처리 범위: {dates[0]} ~ {dates[-1]}")
            print(f"{'='*70}\n")

            return {
                "message": "ZIP/DB 업로드 및 분석 성공",
                "user_id": user_id,
                "total_days_in_file": total_days_in_file,
                "total_days_saved": total_days,
                "date_range": f"{dates[0]} ~ {dates[-1]}" if dates else "",
                "latest_date": latest_date,
                "platform": platform,
                "summary": latest_summary,
                "health_info": health_info,
                "llm_result": llm_result,
                "optimization_info": {
                    "parse_limit_days": PARSE_RECENT_DAYS,
                    "skipped_days": total_days_in_file - total_days,
                },
                "file_info": {
                    "file_type": file.filename.split(".")[-1],
                    "original_path": str(original_save_path),
                    "extract_dir": temp_dir,
                },
            }

        except HTTPException:
            raise
        except Exception as e:
            print(f"[ERROR] 처리 중 오류: {str(e)}")
            import traceback

            traceback.print_exc()
            raise HTTPException(500, f"ZIP/DB 처리 중 오류 발생: {str(e)}")

        finally:
            # 9️⃣ 이전 데이터 정리 + 현재 데이터 보존
            try:
                # 현재 사용자의 모든 추출 디렉토리 찾기
                user_pattern = f"{user_short}_*"
                user_dirs = list(EXTRACTED_DIR.glob(user_pattern))

                # 현재 디렉토리 제외
                current_dir = Path(temp_dir)
                old_dirs = [d for d in user_dirs if d != current_dir]

                # 이전 추출 디렉토리 삭제
                for old_dir in old_dirs:
                    print(f"[INFO] 이전 데이터 삭제: {old_dir.name}")
                    shutil.rmtree(old_dir)

                # 같은 유저의 이전 원본 파일 삭제
                file_pattern = f"{user_short}_*.*"
                old_files = list(UPLOADS_DIR.glob(file_pattern))

                # 현재 파일 제외
                current_file = UPLOADS_DIR / original_save_name
                old_files = [f for f in old_files if f != current_file]

                for old_file in old_files:
                    print(f"[INFO] 이전 원본 파일 삭제: {old_file.name}")
                    old_file.unlink()

                print(f"[INFO] 최신 데이터 보존: {temp_dir}")
                print(f"[INFO] 최신 원본 보존: {original_save_path}")

            except Exception as e:
                print(f"[WARN] 이전 데이터 정리 중 오류 (무시): {str(e)}")
