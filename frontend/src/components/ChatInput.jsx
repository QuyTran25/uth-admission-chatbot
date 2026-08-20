import React from 'react';
import { useNavigate } from 'react-router-dom';
import '../CSS/ChatInput.css';

const ChatInput = () => {
  const navigate = useNavigate();

  const handleSend = () => {
    navigate('/chat/detail');
  };

  return (
    <section className="chat-input-container">
      <div className="chat-input-container__inner">
        <button className="chat-input__mic-btn">
          <i className="fas fa-microphone"></i>
        </button>
        <input 
          type="text" 
          className="chat-input__field" 
          placeholder="Bạn muốn hỏi gì?"
        />
        <button className="chat-input__send-btn" onClick={handleSend}>
          <i className="fas fa-paper-plane"></i>
        </button>
      </div>
    </section>
  );
};

export default ChatInput;
