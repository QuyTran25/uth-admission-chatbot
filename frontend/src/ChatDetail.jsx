import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import Header from './Header';
import axios from 'axios';
import BotMessage from './components/BotMessage';
import './CSS/ChatDetail.css';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

const ChatDetail = () => {
  const navigate = useNavigate();
  
  // Chat state
  const [messages, setMessages] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [showRatingModal, setShowRatingModal] = useState(false);
  const [showThankYouModal, setShowThankYouModal] = useState(false);
  const [rating, setRating] = useState(0);
  const [hoverRating, setHoverRating] = useState(0);
  const [feedback, setFeedback] = useState('');
  const [inputValue, setInputValue] = useState('');
  
  // B3: Load chat history from localStorage on mount
  useEffect(() => {
    const savedChat = localStorage.getItem('uth_chat_history');
    if (savedChat) {
      try {
        setMessages(JSON.parse(savedChat));
      } catch (e) {
        console.error('Error loading chat history:', e);
        localStorage.removeItem('uth_chat_history');
      }
    }
  }, []);
  
  // B3: Save chat history to localStorage whenever messages change
  useEffect(() => {
    if (messages.length > 0) {
      localStorage.setItem('uth_chat_history', JSON.stringify(messages));
    }
  }, [messages]);
  
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
      console.error('Error sending message:', err);
      setError(err.response?.data?.detail || 'Có lỗi xảy ra. Vui lòng thử lại sau.');
      
      const errorMessage = {
        id: Date.now() + 2,
        role: 'bot',
        content: 'Xin lỗi, tôi gặp sự cố. Vui lòng thử lại sau.',
        behavior: 'refused',
        citations: [],
        citation_precision: 0.0,
        refused_reason: 'system_error',
        timestamp: new Date().toISOString()
      };
      
      setMessages(prev => [...prev, errorMessage]);
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
  
  // Handle new chat - B3: reset
  const handleNewChat = () => {
    if (window.confirm('Bạn có chắc chắn muốn bắt đầu cuộc trò chuyện mới? Toàn bộ lịch sử chat sẽ bị xóa.')) {
      setMessages([]);
      localStorage.removeItem('uth_chat_history');
    }
  };
  
  // Handle rating submission
  const handleRatingSubmit = (e) => {
    e.preventDefault();
    setShowRatingModal(false);
    setShowThankYouModal(true);
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
                <i className="fa-regular fa-calendar" style={{color: '#006a63'}}></i> 
                Thông tin Open Day UTH 2026
              </button>
              <button 
                className="prompt-chip" 
                onClick={() => handleChipClick('Tôi muốn biết về học bổng của trường')}
              >
                <i className="fa-regular fa-lightbulb" style={{color: '#006a63'}}></i> 
                Tôi muốn biết về học bổng của trường
              </button>
              <button 
                className="prompt-chip" 
                onClick={() => handleChipClick('Có nên học ở UTH không?')}
              >
                <i className="fa-solid fa-graduation-cap" style={{color: '#006a63'}}></i> 
                Có nên học ở UTH không?
              </button>
              <button 
                className="prompt-chip" 
                onClick={() => handleChipClick('Điểm chuẩn các ngành năm 2024')}
              >
                <i className="fa-solid fa-chart-line" style={{color: '#006a63'}}></i> 
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
