import React from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import './CSS/Header.css';

const Header = () => {
  const navigate = useNavigate();
  const location = useLocation();

  const isChat = location.pathname === '/chat';
  const isChatDetail = location.pathname === '/chat/detail';

  // Yêu cầu 1,2: Khi rời khỏi chat chi tiết có lịch sử → hỏi có muốn lưu không
  const askSaveIfNeeded = (onDone) => {
    if (isChatDetail && localStorage.getItem('uth_chat_history')) {
      const shouldSave = window.confirm('Bạn có muốn lưu lại cuộc trò chuyện này không?');
      if (shouldSave) saveCurrentConversation();
    }
    onDone();
  };

  // Lưu cuộc trò chuyện hiện tại vào danh sách đã lưu
  const saveCurrentConversation = () => {
    try {
      const raw = localStorage.getItem('uth_chat_history');
      if (!raw) return;
      const messages = JSON.parse(raw);
      if (!messages.length) return;
      const existing = JSON.parse(localStorage.getItem('uth_saved_conversations') || '[]');
      const firstUser = messages.find((m) => m.role === 'user');
      const title = firstUser ? firstUser.content.slice(0, 60) : 'Cuộc trò chuyện UTH';
      const saved = {
        id: Date.now(),
        title,
        savedAt: new Date().toISOString(),
        messages,
      };
      existing.unshift(saved);
      localStorage.setItem('uth_saved_conversations', JSON.stringify(existing));
    } catch (e) {
      console.error('Lưu lịch sử thất bại:', e);
    }
  };

  const goToChat = () => {
    if (!isChat) navigate('/chat');
  };

  // Yêu cầu 4: Logo → về trang chủ giới thiệu
  const handleLogoClick = (e) => {
    e.preventDefault();
    askSaveIfNeeded(() => navigate('/'));
  };

  // Yêu cầu 3: Thông tin tuyển sinh → mở trang tuyensinh.ut.edu.vn
  const handleAdmissionLink = (e) => {
    e.preventDefault();
    askSaveIfNeeded(() => window.open('https://tuyensinh.ut.edu.vn/', '_blank', 'noopener,noreferrer'));
  };

  // Yêu cầu 5: Liên hệ → về trang chủ và cuộn tới #contact
  const handleContactLink = (e) => {
    e.preventDefault();
    askSaveIfNeeded(() => navigate('/', { state: { scrollTo: 'contact' } }));
  };

  return (
    <header className="header">
      {/* Logo */}
      <a href="/" className="header__logo" onClick={handleLogoClick}>
        <img src="/images/logo-full.png" alt="Tuyển sinh UTH – Đại học Giao thông vận tải TP.HCM" className="header__logo-img" />
      </a>

      {/* Navigation */}
      <nav className="header__nav">
        <a href="#thong-tin-tuyen-sinh" className="header__nav-link" onClick={handleAdmissionLink}>
          Thông tin tuyển sinh
        </a>
        <a href="#lien-he" className="header__nav-link" onClick={handleContactLink}>
          Liên hệ
        </a>
      </nav>

      {/* CTA Button */}
      <button className="header__cta" onClick={goToChat}>
        {!isChat && (
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
            <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path>
          </svg>
        )}
        {isChat ? 'Đăng nhập' : 'Hỏi đáp ngay'}
      </button>
    </header>
  );
};

export default Header;
