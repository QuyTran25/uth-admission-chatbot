import React from "react";
import { DotLottieReact } from "@lottiefiles/dotlottie-react";
import { useNavigate } from "react-router-dom";

const LottieBot = () => {
  const navigate = useNavigate();

  const handleBotClick = () => {
    navigate("/chat");
  };

  return (
    <div 
      className="lottie-bot-container" 
      onClick={handleBotClick} 
      role="button" 
      tabIndex={0}
      aria-label="Trò chuyện với UTH AI"
    >
      <div className="lottie-speech-bubble">
        <span>Hỏi UTH AI ngay! 🤖</span>
      </div>
      <div className="lottie-bot-fixed" aria-hidden="true">
        <DotLottieReact
          src="/lottie/cute-bot.json"
          loop
          autoplay
        />
      </div>
    </div>
  );
};

export default LottieBot;
