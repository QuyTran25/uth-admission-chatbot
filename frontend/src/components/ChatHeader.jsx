import React from 'react';
import '../CSS/ChatHeader.css';

const ChatHeader = () => {
  return (
    <header className="chat-header">
      <nav className="chat-header__nav">
        <div className="chat-header__left">
          <a href="/" className="chat-header__logo">
            <img src="/images/logo-full.png" alt="UTH Logo" />
          </a>
          <div className="chat-header__links">
            <a href="#tuyensinh" className="chat-header__link">Thông tin tuyển sinh</a>
            <a href="#lienhe" className="chat-header__link">Liên hệ</a>
          </div>
        </div>
        <button className="chat-header__cta">Hỏi đáp ngay</button>
      </nav>
    </header>
  );
};

export default ChatHeader;
