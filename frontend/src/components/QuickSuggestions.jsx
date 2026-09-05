import React from 'react';
import { useNavigate } from 'react-router-dom';
import '../CSS/QuickSuggestions.css';

const QuickSuggestions = () => {
  const navigate = useNavigate();

  const suggestions = [
    { icon: 'fas fa-calendar-alt', text: 'Thông tin Open Day UTH 2026' },
    { icon: 'fas fa-lightbulb', text: 'Tôi muốn biết về học bổng của trường' },
    { icon: 'fas fa-graduation-cap', text: 'Có nên học ở UTH không?' },
    { icon: 'fas fa-chart-line', text: 'Điểm chuẩn các ngành năm 2024' }
  ];

  return (
    <section className="quick-suggestions">
      <div className="quick-suggestions__grid">
        {suggestions.map((s, i) => (
          <button 
            key={i} 
            className="quick-suggestion-btn"
            onClick={() => {
              sessionStorage.setItem('uth_initial_query', s.text);
              navigate('/chat/detail', { state: { initialQuery: s.text } });
            }}
          >
            <div className="quick-suggestion-btn__icon">
              <i className={s.icon}></i>
            </div>
            <span className="quick-suggestion-btn__text">{s.text}</span>
          </button>
        ))}
      </div>
    </section>
  );
};

export default QuickSuggestions;
