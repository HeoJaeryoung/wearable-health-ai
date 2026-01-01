import api from '../index';

export const uploadFile = async (
  file,
  userId,
  difficulty = '중',
  duration = 30
) => {
  const formData = new FormData();
  formData.append('file', file);

  const response = await api.post('/api/file/upload', formData, {
    params: { user_id: userId, difficulty, duration },
    headers: { 'Content-Type': 'multipart/form-data' },
  });

  return response.data;
};
