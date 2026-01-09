import React from 'react';
import '../../css/wearable/ExerciseRecommend.css';

function ExerciseRecommend({ data, loading }) {
  const renderContent = () => {
    if (loading) {
      return (
        <div className="analysis-loading">
          <div className="loading-spinner"></div>
          <p>분석 중...</p>
        </div>
      );
    }

    if (!data) {
      return (
        <div className="analysis-empty">
          <span className="empty-icon">🏃</span>
          <p>데이터를 업로드하면</p>
          <p>운동 추천이 표시됩니다</p>
        </div>
      );
    }

    const routine =
      data.llm_result?.ai_recommended_routine ||
      data.ai_recommended_routine ||
      {};
    const debugInfo = data.llm_result?.debug_info || data.debug_info || {};
    const items = routine.items || [];
    const totalTime = routine.total_time_min || 0;
    const totalCalories = routine.total_calories || 0;
    const intensity = debugInfo.intensity || '중';

    // analysis 문장 추출 (items 체크 전에 선언)
    const analysis =
      data.llm_result?.analysis ||
      data.analysis ||
      '오늘 컨디션에 맞는 루틴입니다.';

    if (items.length === 0) {
      return (
        <div className="analysis-empty">
          <span className="empty-icon">🏃</span>
          <p>추천 운동이 없습니다</p>
        </div>
      );
    }

    return (
      <div className="routine-content">
        {/* 요약 정보 */}
        <div className="routine-summary">
          <div className="summary-item">
            <span className="summary-icon">💪</span>
            <span className="summary-value">{intensity}</span>
          </div>
          <div className="summary-item">
            <span className="summary-icon">⏱️</span>
            <span className="summary-value">{totalTime}분</span>
          </div>
          <div className="summary-item">
            <span className="summary-icon">🔥</span>
            <span className="summary-value">{totalCalories}kcal</span>
          </div>
        </div>

        {/* AI 분석 섹션 */}
        <div className="routine-analysis">
          <h4 className="routine-section-title">AI 분석</h4>
          <p className="routine-analysis-text">{analysis}</p>
        </div>

        {/* 추천 루틴 섹션 */}
        <div className="routine-exercises">
          <h4 className="routine-section-title">추천 루틴</h4>
          <div className="routine-list">
            {items.map((item, index) => (
              <div key={index} className="routine-item">
                <div className="routine-number">{index + 1}</div>
                <div className="routine-info">
                  <span className="routine-name">{item.exercise_name}</span>
                  <span className="routine-detail">
                    {item.duration_sec}초 × {item.set_count}세트
                  </span>
                </div>
                {item.calories && (
                  <span className="routine-calories">{item.calories}kcal</span>
                )}
              </div>
            ))}
          </div>
        </div>
      </div>
    );
  };

  return (
    <div className="analysis-card">
      <div className="analysis-card-header exercise-header">
        <span className="analysis-icon">🏋️</span>
        <h3>운동 추천</h3>
      </div>
      <div className="analysis-card-body">{renderContent()}</div>
    </div>
  );
}

export default ExerciseRecommend;
