import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import Header from './Header';
import './CSS/ChatDetail.css';

const ChatDetail = () => {
  const navigate = useNavigate();
  const [showRatingModal, setShowRatingModal] = useState(false);
  const [showThankYouModal, setShowThankYouModal] = useState(false);
  const [rating, setRating] = useState(0);
  const [hoverRating, setHoverRating] = useState(0);
  const [feedback, setFeedback] = useState('');

  const handleNewChat = () => {
    navigate('/chat');
  };

  const handleRatingSubmit = (e) => {
    e.preventDefault();
    setShowRatingModal(false);
    setShowThankYouModal(true);
  };

  return (
    <div className="chat-detail-page">
      <Header />
      
      <main className="chat-detail-main">
        {/* Chat Area */}
        <div className="chat-container">
          <div className="chat-messages">
            {/* User message */}
            <div className="chat-message user">
              <div className="message-content">
                Tôi muốn biết về học bổng của trường
              </div>
            </div>

            {/* Bot response */}
            <div className="chat-message bot">
              <div className="message-content">
                <p>Chào bạn — mình tóm tắt nhanh các chính sách học bổng chính của Trường Đại học Giao thông vận tải TP. HCM (UTH) hiện hành (năm 2026):</p>
                
                <h4 style={{marginTop: '16px', fontWeight: '700'}}>Học bổng khuyến tài</h4>
                <p>Điều kiện: Tổng điểm 3 môn xét tuyển THPT (không tính điểm ưu tiên/điểm cộng) từ <strong>26 điểm trở lên</strong>.</p>
                <p>Mức thưởng: 1.000.000 VNĐ cho mỗi 1 điểm (tính theo tổng điểm; chọn người cao nhất mỗi ngành).</p>

                <h4 style={{marginTop: '16px', fontWeight: '700'}}>Quỹ học bổng</h4>
                <p>Năm 2026, nhà trường dành <strong>60 tỷ đồng</strong> để cấp học bổng cho sinh viên.</p>

                <p style={{marginTop: '16px'}}>Muốn biết chi tiết điều kiện, thủ tục xin học bổng hoặc danh sách chính xác 6 ngành kỹ thuật được ưu đãi cho nữ, bạn có thể liên hệ:</p>
                
                <ul style={{listStyle: 'none', paddingLeft: 0, marginTop: '8px'}}>
                  <li>Email: <a href="mailto:tuyensinh@uth.edu.vn" style={{color: '#1ea59a', textDecoration: 'underline'}}>tuyensinh@uth.edu.vn</a></li>
                  <li>Trang tra cứu tuyển sinh: <a href="https://xettuyen.uth.edu.vn" target="_blank" rel="noopener noreferrer" style={{color: '#1ea59a', textDecoration: 'underline'}}>https://xettuyen.uth.edu.vn</a></li>
                  <li>Hotline: (028) 3899 6199</li>
                </ul>

                <p style={{marginTop: '16px'}}>Hy vọng giúp bạn nắm được chính sách chính.</p>
              </div>
            </div>
          </div>

          {/* Quick Actions */}
          <div className="chat-actions">
            <button className="btn-action new-chat" onClick={handleNewChat}>
              <i className="fa-solid fa-plus"></i>
              Cuộc trò chuyện mới
            </button>
            <button className="btn-action end-chat" onClick={() => setShowRatingModal(true)}>
              <i className="fa-regular fa-circle-check"></i>
              Kết thúc & đánh giá
            </button>
          </div>

          {/* Prompt Chips */}
          <div className="prompt-chips">
            <button className="prompt-chip"><i className="fa-regular fa-calendar" style={{color: '#006a63'}}></i> Thông tin Open Day UTH 2026</button>
            <button className="prompt-chip"><i className="fa-regular fa-lightbulb" style={{color: '#006a63'}}></i> Tôi muốn biết về học bổng của trường</button>
            <button className="prompt-chip"><i className="fa-solid fa-graduation-cap" style={{color: '#006a63'}}></i> Có nên học ở UTH không?</button>
            <button className="prompt-chip"><i className="fa-solid fa-chart-line" style={{color: '#006a63'}}></i> Điểm chuẩn các ngành năm 2024</button>
          </div>

          {/* Input Box */}
          <div className="chat-input-area">
            <div className="chat-input-box">
              <input type="text" placeholder="Bạn muốn hỏi gì?" />
              <div className="chat-input-controls">
                <button className="control-btn mic"><i className="fa-solid fa-microphone"></i></button>
                <button className="control-btn send"><i className="fa-solid fa-arrow-right"></i></button>
              </div>
            </div>
          </div>
        </div>
      </main>

      {/* Rating Modal */}
      {showRatingModal && (
        <div className="modal-overlay">
          <div className="modal-content rating-modal">
            <button className="modal-close" onClick={() => setShowRatingModal(false)}>×</button>
            <h3 className="modal-title">Đánh giá dịch vụ</h3>
            <p className="modal-subtitle">Trải nghiệm của bạn như thế nào?</p>
            
            <form onSubmit={handleRatingSubmit}>
              {/* Star Rating */}
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

              {/* Feedback Field */}
              <textarea
                className="feedback-textarea"
                placeholder="Hãy chia sẻ thêm ý kiến của bạn để giúp chúng tôi hoàn thiện hơn..."
                value={feedback}
                onChange={(e) => setFeedback(e.target.value)}
                rows={4}
              />

              <div className="modal-buttons">
                <button type="button" className="btn-secondary" onClick={() => setShowRatingModal(false)}>Hủy</button>
                <button type="submit" className="btn-primary-rating" disabled={rating === 0}>Hoàn thành</button>
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
            <button className="btn-done" onClick={() => {
              setShowThankYouModal(false);
              navigate('/chat');
            }}>Quay lại trang chủ</button>
          </div>
        </div>
      )}
    </div>
  );
};

export default ChatDetail;
