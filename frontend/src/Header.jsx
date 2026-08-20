import React from 'react';
import './CSS/Header.css';

const Header = () => {
  return (
    <header className="header">
      {/* Logo */}
      <div className="header__logo">
        <img src="/images/logo-full.png" alt="Tuyển sinh UTH – Đại học Giao thông vận tải TP.HCM" className="header__logo-img" />
      </div>

      {/* Navigation */}
      <nav className="header__nav">
        <a href="https://tuyensinh.ut.edu.vn/" target="_blank" rel="noopener noreferrer" className="header__nav-link">Thông tin tuyển sinh</a>
        <a href="#contact" className="header__nav-link">Liên hệ</a>
      </nav>

      {/* CTA Button */}
      <button className="header__cta">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
          <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path>
        </svg>
        Hỏi đáp ngay
      </button>
    </header>
  );
};

export default Header;
