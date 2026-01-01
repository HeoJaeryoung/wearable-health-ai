import React, { useState, useRef } from 'react';
import { uploadFile } from '../../api/wearable';
import '../../css/wearable/FileUpload.css';

function FileUpload({ onAnalysisComplete, setLoading }) {
  const [file, setFile] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [difficulty, setDifficulty] = useState('중');
  const [duration, setDuration] = useState(30);
  const fileInputRef = useRef(null);

  const handleFileSelect = (e) => {
    const selectedFile = e.target.files[0];
    if (selectedFile) {
      const validTypes = ['.zip', '.db'];
      const fileExt = selectedFile.name
        .toLowerCase()
        .slice(selectedFile.name.lastIndexOf('.'));

      if (!validTypes.includes(fileExt)) {
        setError('ZIP 또는 DB 파일만 업로드 가능합니다.');
        setFile(null);
        return;
      }

      setFile(selectedFile);
      setError('');
      setSuccess('');
    }
  };

  const handleUpload = async () => {
    if (!file) {
      setError('파일을 선택해주세요.');
      return;
    }

    const userId = localStorage.getItem('user_email') || 'guest@test.com';

    setUploading(true);
    setLoading(true);
    setError('');
    setSuccess('');

    try {
      const result = await uploadFile(file, userId, difficulty, duration);
      // setSuccess(
      //   `분석 완료! ${result.total_days_saved || 0}일치 데이터 저장됨`
      // );
      onAnalysisComplete(result);
      setFile(null);
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
    } catch (err) {
      setError(err.response?.data?.detail || '업로드 중 오류가 발생했습니다.');
    } finally {
      setUploading(false);
      setLoading(false);
    }
  };

  return (
    <div className="upload-group">
      <h4 className="upload-title">📁 파일 업로드 (.zip/.db)</h4>

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

        <input
          type="file"
          ref={fileInputRef}
          onChange={handleFileSelect}
          accept=".zip,.db"
          hidden
        />

        <button
          className="btn-select-file"
          onClick={() => fileInputRef.current?.click()}
        >
          {file ? file.name : '파일 선택'}
        </button>

        <button
          className="btn-primary btn-analyze"
          onClick={handleUpload}
          disabled={!file || uploading}
        >
          {uploading ? '분석 중...' : '분석하기'}
        </button>
      </div>

      {error && <div className="upload-message error">{error}</div>}
      {success && <div className="upload-message success">{success}</div>}
    </div>
  );
}

export default FileUpload;
