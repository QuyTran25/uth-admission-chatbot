import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import Header from './Header';
import ChatHero from './components/ChatHero';
import QuickSuggestions from './components/QuickSuggestions';
import ChatInput from './components/ChatInput';
import Footer from './components/Footer';
import './CSS/Global.css';
import './CSS/Footer.css';
import './CSS/ChatDetail.css';

const ChatPage = () => {
  const navigate = useNavigate();
  const [savedConversations, setSavedConversations] = useState([]);

  const loadSavedConversations = () => {
    try {
      setSavedConversations(JSON.parse(localStorage.getItem('uth_saved_conversations') || '[]'));
    } catch {
      setSavedConversations([]);
    }
  };

  useEffect(() => {
    loadSavedConversations();
  }, []);

  const openConversation = (conversation) => {
    localStorage.setItem('uth_chat_history', JSON.stringify(conversation.messages));
    localStorage.setItem('uth_active_conversation_id', String(conversation.id));
    navigate('/chat/detail');
  };

  const deleteConversation = (event, id) => {
    event.stopPropagation();
    const nextConversations = savedConversations.filter((conversation) => conversation.id !== id);
    localStorage.setItem('uth_saved_conversations', JSON.stringify(nextConversations));
    if (String(id) === localStorage.getItem('uth_active_conversation_id')) {
      localStorage.removeItem('uth_active_conversation_id');
    }
    setSavedConversations(nextConversations);
  };

  return (
    <div className="chat-page">
      <Header />
      <main className="chat-main" style={{ paddingTop: '80px', minHeight: 'calc(100vh - 200px)' }}>
        <div className="chat-page-toolbar">
          <button className="btn-return-home" type="button" onClick={() => navigate('/')}>
            <i className="fa-solid fa-arrow-left"></i>
            Quay lại trang chủ
          </button>
        </div>
        <ChatHero />
        <QuickSuggestions />
        <ChatInput />

        <section className="saved-conversations" aria-labelledby="saved-conversations-title">
          <div className="saved-conversations-heading">
            <div>
              <span className="saved-conversations-eyebrow">LỊCH SỬ CÁ NHÂN</span>
              <h2 id="saved-conversations-title">Cuộc trò chuyện đã lưu</h2>
            </div>
            <span className="saved-conversations-count">{savedConversations.length}</span>
          </div>

          {savedConversations.length ? (
            <div className="saved-conversations-list">
              {savedConversations.map((conversation) => (
                <div className="saved-conversation-card" key={conversation.id} onClick={() => openConversation(conversation)} role="button" tabIndex="0">
                  <span className="saved-conversation-icon"><i className="fa-regular fa-message"></i></span>
                  <span className="saved-conversation-copy">
                    <strong>{conversation.title}</strong>
                    <small>{new Date(conversation.savedAt).toLocaleString('vi-VN')}</small>
                  </span>
                  <button
                    type="button"
                    className="saved-conversation-delete"
                    aria-label={`Xóa cuộc trò chuyện: ${conversation.title}`}
                    onClick={(event) => deleteConversation(event, conversation.id)}
                  >
                    <i className="fa-solid fa-trash-can"></i>
                  </button>
                  <i className="fa-solid fa-chevron-right saved-conversation-arrow"></i>
                </div>
              ))}
            </div>
          ) : (
            <div className="saved-conversations-empty">
              <i className="fa-regular fa-bookmark"></i>
              <p>Chưa có cuộc trò chuyện nào được lưu.</p>
              <span>Hãy lưu cuộc trò chuyện khi quay lại trang chủ để xem lại sau.</span>
            </div>
          )}
        </section>
      </main>
      <Footer minimal={true} />
    </div>
  );
};

export default ChatPage;
