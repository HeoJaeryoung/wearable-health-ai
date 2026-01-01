import api from '../index';

export const getLatestAppData = async (userId, watchType = 'galaxy') => {
  const response = await api.get('/api/app/latest', {
    params: { user_id: userId, watch_type: watchType },
  });
  return response.data;
};

export const getAppHistory = async (userId, watchType = null, limit = 10) => {
  const response = await api.get('/api/app/history', {
    params: { user_id: userId, watch_type: watchType, limit },
  });
  return response.data;
};
