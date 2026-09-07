import React from "react";
import { DotLottieReact } from "@lottiefiles/dotlottie-react";

const LottieBot = () => {
  return (
    <div className="lottie-bot-fixed" aria-hidden="true">
      <DotLottieReact
        src="/lottie/cute-bot.json"
        loop
        autoplay
      />
    </div>
  );
};

export default LottieBot;
