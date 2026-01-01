import api from './index';

export const login = async (email, password) => {
  const response = await api.post('/api/auth/login', {
    email,
    password,
  });
  return response.data;
};

export const signup = async (email, password) => {
  const response = await api.post('/api/auth/signup', {
    email,
    password,
  });
  return response.data;
};

export const checkAuth = async () => {
  const token = localStorage.getItem('token');
  if (!token) return null;

  try {
    const response = await api.get('/api/auth/me', {
      headers: { Authorization: `Bearer ${token}` },
    });
    return response.data;
  } catch {
    localStorage.removeItem('token');
    return null;
  }
};
