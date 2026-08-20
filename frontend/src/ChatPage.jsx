import React from 'react';
import Header from './Header';
import ChatHero from './components/ChatHero';
import QuickSuggestions from './components/QuickSuggestions';
import ChatInput from './components/ChatInput';
import Footer from './components/Footer';
import './CSS/Global.css';
import './CSS/Footer.css';

const ChatPage = () => {
  return (
    <div className="chat-page">
      <Header />
      <main className="chat-main" style={{ paddingTop: '80px', minHeight: 'calc(100vh - 200px)' }}>
        <ChatHero />
        <QuickSuggestions />
        <ChatInput />
      </main>
      <Footer minimal={true} />
    </div>
  );
};

export default ChatPage;
