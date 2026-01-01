import React from 'react';
import { Link, useNavigate } from 'react-router-dom';
import './Header.css';

function Header() {
  const navigate = useNavigate();
  const userEmail = localStorage.getItem('user_email');
  const isLoggedIn = !!userEmail;

  const handleLogout = () => {
    localStorage.removeItem('token');
    localStorage.removeItem('user_id');
    localStorage.removeItem('user_email');
    navigate('/login');
  };

  return (
    <header className="header">
      <div className="header-container">
        <Link to="/wearable" className="header-logo">
          <span className="logo-icon">💪</span>
          <span className="logo-text">웨어러블 헬스케어</span>
        </Link>

        <nav className="header-nav">
          {isLoggedIn ? (
            <>
              <span className="user-email">{userEmail}</span>
              <button onClick={handleLogout} className="btn-secondary">
                로그아웃
              </button>
            </>
          ) : (
            <>
              <Link to="/login" className="nav-link">
                로그인
              </Link>
              <Link to="/signup" className="nav-link-signup">
                회원가입
              </Link>
            </>
          )}
        </nav>
      </div>
    </header>
  );
}

export default Header;
