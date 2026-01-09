import React from 'react';
import '../../css/wearable/HealthAnalysis.css';

function HealthAnalysis({ data, loading }) {
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
          <span className="empty-icon">📊</span>
          <p>데이터를 업로드하면</p>
          <p>건강 분석 결과가 표시됩니다</p>
        </div>
      );
    }

    const summary = data.summary || {};
    const raw = summary.raw || {};

    // ✅ 건강 분석 정보 (health_info에서 가져오기)
    const healthInfo = data.health_info || {};
    const sleepInfo = healthInfo.sleep || {};
    const activityInfo = healthInfo.activity || {};
    const heartRateInfo = healthInfo.heart_rate || {};
    const healthScore = healthInfo.health_score || {};

    // ✅ 건강 분석 텍스트 생성
    const buildHealthAnalysis = () => {
      const parts = [];

      // 건강 점수
      if (healthScore.score) {
        parts.push(
          `현재 건강 점수는 ${healthScore.score}점(${healthScore.grade}등급)입니다.`
        );
      }

      // 수면 분석
      if (sleepInfo.message) {
        parts.push(sleepInfo.message);
      }

      // 활동량 분석
      if (activityInfo.message) {
        parts.push(activityInfo.message);
      }

      // 심박수 분석
      if (heartRateInfo.message) {
        parts.push(heartRateInfo.message);
      }

      return parts.join(' ');
    };

    const analysis = buildHealthAnalysis();

    return (
      <div className="analysis-content">
        <div className="health-metrics">
          {raw.sleep_hr > 0 && (
            <div className="metric-item">
              <span className="metric-icon">😴</span>
              <div className="metric-info">
                <span className="metric-value">
                  {raw.sleep_hr?.toFixed(1)}시간
                </span>
              </div>
            </div>
          )}
          {raw.steps > 0 && (
            <div className="metric-item">
              <span className="metric-icon">👟</span>
              <div className="metric-info">
                <span className="metric-value">
                  {raw.steps?.toLocaleString()}보
                </span>
              </div>
            </div>
          )}
        </div>

        {analysis && (
          <div className="ai-analysis">
            <h4>AI 분석</h4>
            <p className="analysis-text">{analysis}</p>
          </div>
        )}
      </div>
    );
  };

  return (
    <div className="analysis-card">
      <div className="analysis-card-header">
        <span className="analysis-icon">💪</span>
        <h3>건강 분석</h3>
      </div>
      <div className="analysis-card-body">{renderContent()}</div>
    </div>
  );
}

export default HealthAnalysis;
