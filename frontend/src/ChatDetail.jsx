import React, { useState, useEffect, useRef } from 'react';
import { useNavigate, useLocation, useSearchParams } from 'react-router-dom';
import Header from './Header';
import axios from 'axios';
import BotMessage from './components/BotMessage';
import './CSS/ChatDetail.css';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

const ChatDetail = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const [searchParams] = useSearchParams();
  const initialQueryHandled = useRef(false);

  // Chat state
  const [messages, setMessages] = useState([]);
  const [viewingConversationId, setViewingConversationId] = useState(null);
  const [isInitialized, setIsInitialized] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [showRatingModal, setShowRatingModal] = useState(false);
  const [showThankYouModal, setShowThankYouModal] = useState(false);
  const [rating, setRating] = useState(0);
  const [hoverRating, setHoverRating] = useState(0);
  const [feedback, setFeedback] = useState('');
  const [inputValue, setInputValue] = useState('');
  const [showSaveDialog, setShowSaveDialog] = useState(false);

  // B3.1: Initialization effect — URL (searchParams conversationId) là nguồn sự thật
  useEffect(() => {
    const conversationId = searchParams.get('conversationId');

    if (conversationId) {
      // Trường hợp B: xem lại một cuộc trò chuyện từ trang Lịch sử
      const savedConversations = JSON.parse(localStorage.getItem('uth_saved_conversations') || '[]');
      const conversation = savedConversations.find((item) => String(item.id) === String(conversationId));

      if (conversation) {
        setMessages(conversation.messages);
        setViewingConversationId(conversation.id);
        localStorage.setItem('uth_chat_history', JSON.stringify(conversation.messages));
        localStorage.setItem('uth_viewing_conversation_id', String(conversation.id));
      }
    } else {
      // Trường hợp A: chat mới hoàn toàn — KHÔNG nạp lại uth_chat_history cũ
      setMessages([]);
      setViewingConversationId(null);
      localStorage.removeItem('uth_chat_history');
      localStorage.removeItem('uth_viewing_conversation_id');

      // Auto-send query received from homepage
      const q = location.state?.initialQuery || sessionStorage.getItem('uth_initial_query');
      if (!initialQueryHandled.current && q) {
        initialQueryHandled.current = true;
        sessionStorage.removeItem('uth_initial_query');
        window.history.replaceState({}, '');
        sendMessage(q);
      }
    }

    setIsInitialized(true);
  }, [searchParams.get('conversationId')]);

  // B3.2: Auto-sync effect — chỉ chạy khi đã khởi tạo xong
  useEffect(() => {
    if (!isInitialized) return;
    localStorage.setItem('uth_chat_history', JSON.stringify(messages));
  }, [messages, isInitialized]);

  // B1: Send message to API
  const sendMessage = async (messageText) => {
    if (!messageText.trim()) return;

    const userMessage = {
      id: Date.now(),
      role: 'user',
      content: messageText,
      timestamp: new Date().toISOString()
    };

    setMessages(prev => [...prev, userMessage]);
    setInputValue('');
    setIsLoading(true);
    setError(null);

    try {
      const response = await axios.post(`${API_BASE_URL}/api/v1/chat`, {
        query: messageText,
        top_k: 5
      });

      const botResponse = {
        id: Date.now() + 1,
        role: 'bot',
        content: response.data.answer,
        behavior: response.data.behavior,
        citations: response.data.citations,
        citation_precision: response.data.citation_precision,
        refused_reason: response.data.refused_reason,
        oos_categories: response.data.oos_categories,
        latency_ms: response.data.latency_ms,
        year_used: response.data.year_used,
        timestamp: new Date().toISOString()
      };

      setMessages(prev => [...prev, botResponse]);

    } catch (err) {
      const status = err.response?.status;
      const detail = err.response?.data?.detail;
      let message;
      let reason;

      if (!err.response) {
        message = 'Chưa kết nối được máy chủ tư vấn. Hệ thống đang khởi động hoặc backend chưa chạy. Vui lòng chờ ít phút rồi thử lại.';
        reason = 'backend_unreachable';
      } else if (status === 429) {
        message = 'Hạn mức Gemini API đang hết hoặc bị giới hạn. Vui lòng chờ ít phút theo thông báo quota, kiểm tra đúng Google Cloud project của API key, hoặc bật billing.';
        reason = 'gemini_quota_exceeded';
      } else if (status === 503) {
        message = 'Dịch vụ AI đang quá tải tạm thời. Vui lòng thử lại sau ít phút.';
        reason = 'gemini_unavailable';
      } else {
        message = detail || 'Dịch vụ tư vấn gặp lỗi tạm thời. Vui lòng thử lại sau.';
        reason = 'system_error';
      }

      console.error('Chat request failed', { status, apiBaseUrl: API_BASE_URL });
      setError(message);
      setMessages(prev => [...prev, {
        id: Date.now() + 2,
        role: 'bot',
        content: message,
        behavior: 'refused',
        citations: [],
        citation_precision: 0.0,
        refused_reason: reason,
        timestamp: new Date().toISOString()
      }]);
    } finally {
      setIsLoading(false);
    }
  };

  // Handle form submission
  const handleSubmit = (e) => {
    e.preventDefault();
    sendMessage(inputValue);
  };

  // B4: Handle chip clicks - sends message immediately
  const handleChipClick = (chipText) => {
    sendMessage(chipText);
  };

  // B3.3: Handle new chat: reset storage, reset state và điều hướng về /chat/detail (không kèm query param)
  const handleNewChat = () => {
    if (messages.length > 0 && !window.confirm('Bắt đầu cuộc trò chuyện mới?')) {
      return;
    }
    localStorage.removeItem('uth_chat_history');
    localStorage.removeItem('uth_viewing_conversation_id');
    setMessages([]);
    setViewingConversationId(null);
    navigate('/chat/detail');
  };

  // Handle rating submission
  const handleRatingSubmit = (e) => {
    e.preventDefault();
    setShowRatingModal(false);
    setShowThankYouModal(true);
  };

  // Warn when the browser closes, reloads, or navigates away with an active conversation.
  useEffect(() => {
    const warnBeforeUnload = (event) => {
      if (messages.length > 0) {
        event.preventDefault();
        event.returnValue = '';
      }
    };
    window.addEventListener('beforeunload', warnBeforeUnload);
    return () => window.removeEventListener('beforeunload', warnBeforeUnload);
  }, [messages.length]);

  // B3.4: Lưu cuộc trò chuyện và reset draft
  const saveCurrentConversation = () => {
    if (!messages.length) return;

    const savedConversations = JSON.parse(localStorage.getItem('uth_saved_conversations') || '[]');
    const viewingId = localStorage.getItem('uth_viewing_conversation_id');
    const conversationId = viewingId || Date.now();
    const firstUserMessage = messages.find((message) => message.role === 'user');
    const title = firstUserMessage?.content?.slice(0, 60) || 'Cuộc trò chuyện UTH';

    const record = {
      id: conversationId,
      title,
      savedAt: new Date().toISOString(),
      messages,
    };

    const existingIndex = savedConversations.findIndex((c) => String(c.id) === String(conversationId));
    const updated = existingIndex >= 0
      ? savedConversations.map((c, i) => (i === existingIndex ? record : c))
      : [record, ...savedConversations];

    localStorage.setItem('uth_saved_conversations', JSON.stringify(updated));

    // Reset draft — không để lần mở chat tiếp theo tự động tiếp tục phiên này
    localStorage.removeItem('uth_chat_history');
    localStorage.removeItem('uth_viewing_conversation_id');
    setMessages([]);
    setViewingConversationId(null);
  };

  const discardCurrentConversation = () => {
    localStorage.removeItem('uth_chat_history');
    localStorage.removeItem('uth_viewing_conversation_id');
    setMessages([]);
    setViewingConversationId(null);
  };

  const handleReturnHome = (saveConversation) => {
    if (saveConversation) {
      saveCurrentConversation();
    } else {
      discardCurrentConversation();
    }
    setShowSaveDialog(false);
    navigate('/');
  };

  // Scroll to bottom on new message
  useEffect(() => {
    const chatMessages = document.querySelector('.chat-messages');
    if (chatMessages) {
      chatMessages.scrollTop = chatMessages.scrollHeight;
    }
  }, [messages, isLoading]);

  return (
    <div className="chat-detail-page">
      <Header />

      <main className="chat-detail-main">
        <div className="chat-detail-toolbar">
          <button className="btn-return-home" type="button" onClick={() => messages.length ? setShowSaveDialog(true) : navigate('/')}>
            <i className="fa-solid fa-arrow-left"></i>
            Quay lại trang chủ
          </button>
        </div>

        <div className="chat-detail-content">
        {/* Error Toast */}
        {error && (
          <div className="error-toast">
            {error}
            <button onClick={() => setError(null)}>×</button>
          </div>
        )}

        {/* Chat Area */}
        <div className="chat-container">
          <div className="chat-messages">
            {messages.length === 0 ? (
              <div className="empty-chat">
                <div className="empty-chat-icon">
                  <i className="fa-solid fa-comments"></i>
                </div>
                <h3>Bạn muốn hỏi gì?</h3>
                <p>Chọn một gợi ý bên dưới hoặc nhập câu hỏi của bạn</p>
              </div>
            ) : (
              messages.map((message) => (
                <div key={message.id} className={`chat-message ${message.role}`}>
                  {message.role === 'user' ? (
                    <div className="message-content user-message">
                      {message.content}
                    </div>
                  ) : (
                    <div className="message-content bot-message">
                      <BotMessage
                        content={message.content}
                        behavior={message.behavior}
                        citations={message.citations}
                        citation_precision={message.citation_precision}
                        refused_reason={message.refused_reason}
                        oos_categories={message.oos_categories}
                        year_used={message.year_used}
                      />
                    </div>
                  )}
                </div>
              ))
            )}

            {isLoading && (
              <div className="chat-message bot loading">
                <div className="message-content">
                  <div className="typing-indicator">
                    <span></span>
                    <span></span>
                    <span></span>
                  </div>
                  <p>Đang suy nghĩ...</p>
                </div>
              </div>
            )}
          </div>

          {/* Quick Actions */}
          {messages.length > 0 && (
            <div className="chat-actions">
              <button
                className="btn-action new-chat"
                onClick={handleNewChat}
              >
                <i className="fa-solid fa-plus"></i>
                Cuộc trò chuyện mới
              </button>
              <button
                className="btn-action end-chat"
                onClick={() => setShowRatingModal(true)}
              >
                <i className="fa-regular fa-circle-check"></i>
                Kết thúc & đánh giá
              </button>
            </div>
          )}

          {/* B4: Prompt Chips - show only if chat is empty */}
          {messages.length === 0 && (
            <div className="prompt-chips">
              <button
                className="prompt-chip"
                onClick={() => handleChipClick('Thông tin Open Day UTH 2026')}
              >
                <i className="fa-regular fa-calendar" style={{ color: '#006a63' }}></i>
                Thông tin Open Day UTH 2026
              </button>
              <button
                className="prompt-chip"
                onClick={() => handleChipClick('Tôi muốn biết về học bổng của trường')}
              >
                <i className="fa-regular fa-lightbulb" style={{ color: '#006a63' }}></i>
                Tôi muốn biết về học bổng của trường
              </button>
              <button
                className="prompt-chip"
                onClick={() => handleChipClick('Có nên học ở UTH không?')}
              >
                <i className="fa-solid fa-graduation-cap" style={{ color: '#006a63' }}></i>
                Có nên học ở UTH không?
              </button>
              <button
                className="prompt-chip"
                onClick={() => handleChipClick('Điểm chuẩn các ngành năm 2024')}
              >
                <i className="fa-solid fa-chart-line" style={{ color: '#006a63' }}></i>
                Điểm chuẩn các ngành năm 2024
              </button>
            </div>
          )}

          {/* Input Box */}
          <div className="chat-input-area">
            <div className="chat-input-box">
              <input
                type="text"
                placeholder="Bạn muốn hỏi gì?"
                value={inputValue}
                onChange={(e) => setInputValue(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleSubmit(e)}
                disabled={isLoading}
              />
              <div className="chat-input-controls">
                <button className="control-btn mic" type="button" aria-label="Nhập bằng giọng nói">
                  <i className="fa-solid fa-microphone"></i>
                </button>
                <button
                  className="control-btn send"
                  type="button"
                  onClick={handleSubmit}
                  disabled={isLoading || !inputValue.trim()}
                  aria-label="Gửi câu hỏi"
                >
                  <i className="fa-solid fa-arrow-right"></i>
                </button>
              </div>
            </div>
          </div>
        </div>
        </div>
      </main>

      {/* Rating Modal */}
      {showRatingModal && (
        <div className="modal-overlay">
          <div className="modal-content rating-modal">
            <button
              className="modal-close"
              onClick={() => setShowRatingModal(false)}
            >
              ×
            </button>
            <h3 className="modal-title">Đánh giá dịch vụ</h3>
            <p className="modal-subtitle">Trải nghiệm của bạn như thế nào?</p>

            <form onSubmit={handleRatingSubmit}>
              <div className="star-rating">
                {[1, 2, 3, 4, 5].map((star) => (
                  <button
                    type="button"
                    key={star}
                    className={`star-btn ${(hoverRating || rating) >= star ? 'active' : ''}`}
                    onClick={() => setRating(star)}
                    onMouseEnter={() => setHoverRating(star)}
                    onMouseLeave={() => setHoverRating(0)}
                  >
                    <i className="fa-solid fa-star"></i>
                  </button>
                ))}
              </div>

              <textarea
                className="feedback-textarea"
                placeholder="Hãy chia sẻ thêm ý kiến của bạn để giúp chúng tôi hoàn thiện hơn..."
                value={feedback}
                onChange={(e) => setFeedback(e.target.value)}
                rows={4}
              />

              <div className="modal-buttons">
                <button
                  type="button"
                  className="btn-secondary"
                  onClick={() => setShowRatingModal(false)}
                >
                  Hủy
                </button>
                <button
                  type="submit"
                  className="btn-primary-rating"
                  disabled={rating === 0}
                >
                  Hoàn thành
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {showSaveDialog && (
        <div className="modal-overlay" role="dialog" aria-modal="true" aria-labelledby="save-history-title">
          <div className="modal-content save-history-modal">
            <i className="fa-regular fa-bookmark save-history-icon"></i>
            <h3 id="save-history-title" className="modal-title">Lưu cuộc trò chuyện?</h3>
            <p className="modal-subtitle">Bạn có thể mở lại và tiếp tục trò chuyện từ trang Hỏi đáp.</p>
            <div className="modal-buttons">
              <button className="btn-secondary" type="button" onClick={() => handleReturnHome(false)}>Không lưu</button>
              <button className="btn-primary-rating" type="button" onClick={() => handleReturnHome(true)}>Lưu và về trang chủ</button>
            </div>
          </div>
        </div>
      )}

      {/* Thank You Modal */}
      {showThankYouModal && (
        <div className="modal-overlay">
          <div className="modal-content thank-you-modal">
            <div className="success-checkmark">
              <div className="check-icon">
                <span className="icon-line line-tip"></span>
                <span className="icon-line line-long"></span>
                <div className="icon-circle"></div>
                <div className="icon-fix"></div>
              </div>
            </div>
            <h3 className="modal-title">Cảm ơn bạn!</h3>
            <p className="modal-subtitle">Cảm ơn bạn đã trò chuyện cùng chatbot UTH!</p>
            <button
              className="btn-done"
              onClick={() => {
                setShowThankYouModal(false);
                navigate('/chat');
              }}
            >
              Quay lại trang chủ
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

export default ChatDetail;
