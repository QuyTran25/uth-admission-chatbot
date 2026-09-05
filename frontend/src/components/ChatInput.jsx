import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import '../CSS/ChatInput.css';

const ChatInput = () => {
  const navigate = useNavigate();
  const [value, setValue] = useState('');

  const handleSend = () => {
    const q = value.trim();
    if (!q) return;
    sessionStorage.setItem('uth_initial_query', q);
    navigate('/chat/detail', { state: { initialQuery: q } });
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter') handleSend();
  };

  return (
    <section className="chat-input-container">
      <div className="chat-input-container__inner">
        <button className="chat-input__mic-btn" type="button">
          <i className="fas fa-microphone"></i>
        </button>
        <input 
          type="text" 
          className="chat-input__field" 
          placeholder="Bạn muốn hỏi gì?"
          value={value}
          onChange={(e) => setValue(e.target.value)}
          onKeyDown={handleKeyDown}
        />
        <button className="chat-input__send-btn" onClick={handleSend} type="button">
          <i className="fas fa-paper-plane"></i>
        </button>
      </div>
    </section>
  );
};

export default ChatInput;
