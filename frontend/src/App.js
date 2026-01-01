import React from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import Login from './pages/Login';
import SignUp from './pages/SignUp';
import Wearable from './pages/Wearable';

function App() {
  return (
    <Routes>
      <Route path="/" element={<Navigate to="/wearable" replace />} />
      <Route path="/login" element={<Login />} />
      <Route path="/signup" element={<SignUp />} />
      <Route path="/wearable" element={<Wearable />} />
    </Routes>
  );
}

export default App;
