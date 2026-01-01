import React, { useState } from 'react';
import Header from '../../components/Header';
import FileUpload from './FileUpload';
import AutoUpload from './AutoUpload';
import HealthAnalysis from './HealthAnalysis';
import ExerciseRecommend from './ExerciseRecommend';
import TrainerChatbot from './TrainerChatbot';
import './Wearable.css';

function Wearable() {
  const [analysisData, setAnalysisData] = useState(null);
  const [loading, setLoading] = useState(false);

  const handleAnalysisComplete = (data) => {
    setAnalysisData(data);
  };

  return (
    <div className="wearable-page">
      <Header />

      <main className="wearable-main">
        <div className="wearable-container">
          {/* 섹션 1: 데이터 전송 */}
          <section className="section-upload">
            <h2 className="section-title">📤 데이터 전송</h2>
            <div className="upload-wrapper">
              <FileUpload
                onAnalysisComplete={handleAnalysisComplete}
                setLoading={setLoading}
              />
              <div className="upload-divider"></div>
              <AutoUpload
                onAnalysisComplete={handleAnalysisComplete}
                setLoading={setLoading}
              />
            </div>
          </section>

          {/* 섹션 2: 분석 결과 */}
          <section className="section-analysis">
            <div className="analysis-grid">
              <HealthAnalysis data={analysisData} loading={loading} />
              <ExerciseRecommend data={analysisData} loading={loading} />
              <TrainerChatbot />
            </div>
          </section>
        </div>
      </main>
    </div>
  );
}

export default Wearable;
