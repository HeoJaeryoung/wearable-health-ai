import api from '../index';

export const sendMessage = async (
  userId,
  message,
  character = 'devil_coach'
) => {
  const response = await api.post('/api/chat', {
    user_id: userId,
    message,
    character,
  });
  return response.data;
};

export const sendFixedMessage = async (
  userId,
  questionType,
  character = 'devil_coach'
) => {
  const response = await api.post('/api/chat/fixed', {
    user_id: userId,
    question_type: questionType,
    character,
  });
  return response.data;
};
