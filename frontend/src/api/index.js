import axios from 'axios';

// const API_BASE_URL = 'http://localhost:8000';
// const API_BASE_URL = 'http://192.168.0.16:8000';
const API_BASE_URL = 'http://172.30.1.85:8000';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

export default api;
export { API_BASE_URL };
