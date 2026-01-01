import React, { useState } from 'react';
import { getLatestAppData, getLatestAnalysis } from '../../api/wearable';
import '../../css/wearable/FileUpload.css';

function AutoUpload({ onAnalysisComplete, setLoading }) {
  const [fetching, setFetching] = useState(false);
  const [fetched, setFetched] = useState(false);
  const [analyzing, setAnalyzing] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [difficulty, setDifficulty] = useState('중');
  const [duration, setDuration] = useState(30);

  const handleFetchData = async () => {
    const userId = localStorage.getItem('user_email') || 'guest@test.com';

    setFetching(true);
    setError('');
    setSuccess('');

    try {
      await getLatestAppData(userId, 'galaxy');
      setFetched(true);
      // setSuccess('데이터 전송 완료!');
    } catch (err) {
      setError(
        err.response?.data?.detail || '데이터 조회 중 오류가 발생했습니다.'
      );
      setFetched(false);
    } finally {
      setFetching(false);
    }
  };

  const handleAnalyze = async () => {
    const userId = localStorage.getItem('user_email') || 'guest@test.com';

    setAnalyzing(true);
    setLoading(true);
    setError('');
    setSuccess('');

    try {
      const result = await getLatestAnalysis(userId, difficulty, duration);
      // setSuccess('분석 완료!');
      onAnalysisComplete(result);
      setFetched(false);
    } catch (err) {
      setError(err.response?.data?.detail || '분석 중 오류가 발생했습니다.');
    } finally {
      setAnalyzing(false);
      setLoading(false);
    }
  };

  return (
    <div className="upload-group">
      <h4 className="upload-title">📱 앱에서 전송 (JSON)</h4>

      <div className="upload-row">
        <div className="option-group">
          <label className="option-label">운동강도</label>
          <select
            className="option-select"
            value={difficulty}
            onChange={(e) => setDifficulty(e.target.value)}
          >
            <option value="하">하</option>
            <option value="중">중</option>
            <option value="상">상</option>
          </select>
        </div>
        <div className="option-group">
          <label className="option-label">운동시간</label>
          <select
            className="option-select"
            value={duration}
            onChange={(e) => setDuration(Number(e.target.value))}
          >
            <option value={10}>10분</option>
            <option value={30}>30분</option>
            <option value={60}>60분</option>
          </select>
        </div>

        <button
          className="btn-select-file"
          onClick={handleFetchData}
          disabled={fetching}
        >
          {fetching ? '전송 중...' : '서버전송'}
        </button>

        <button
          className="btn-primary btn-analyze"
          onClick={handleAnalyze}
          disabled={!fetched || analyzing}
        >
          {analyzing ? '분석 중...' : '분석하기'}
        </button>
      </div>

      {error && <div className="upload-message error">{error}</div>}
      {success && <div className="upload-message success">{success}</div>}
    </div>
  );
}

export default AutoUpload;
