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
    const analysis = data.llm_result?.analysis || data.analysis || '';

    return (
      <div className="analysis-content">
        <div className="health-metrics">
          {raw.sleep_hr > 0 && (
            <div className="metric-item">
              <span className="metric-icon">😴</span>
              <div className="metric-info">
                {/* <span className="metric-label">수면</span> */}
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
                {/* <span className="metric-label">걸음수</span> */}
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
            <pre className="analysis-text">{analysis}</pre>
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
