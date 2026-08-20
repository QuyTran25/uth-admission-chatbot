import React from 'react';
import '../CSS/ChatHero.css';

const ChatHero = () => {
  const getGreeting = () => {
    const hour = new Date().getHours();
    if (hour >= 5 && hour < 11) return 'Chào buổi sáng';
    if (hour >= 11 && hour < 13) return 'Chào buổi trưa';
    if (hour >= 13 && hour < 18) return 'Chào buổi chiều';
    return 'Chào buổi tối';
  };

  return (
    <section className="chat-hero">
      <div className="chat-hero__icon-wrapper">
        <img src="/images/sun-icon.jpg" alt="Sun Icon" className="chat-hero__icon" />
      </div>
      <h1 className="chat-hero__title">
        {getGreeting()}
      </h1>
      <p className="chat-hero__subtitle">
        Mình có thể giúp gì cho bạn?
      </p>
    </section>
  );
};

export default ChatHero;
