import api from '../index';

export const getLatestAnalysis = async (
  userId,
  difficulty = '중',
  duration = 30
) => {
  const response = await api.get('/api/user/latest-analysis', {
    params: { user_id: userId, difficulty, duration },
  });
  return response.data;
};

export const getRawHistory = async (userId) => {
  const response = await api.get('/api/user/raw-history', {
    params: { user_id: userId },
  });
  return response.data;
};
