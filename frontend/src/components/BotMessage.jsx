import React from 'react';
import CitationBadges from './CitationBadges';

const BotMessage = ({ 
  content, 
  behavior, 
  citations, 
  citation_precision, 
  refused_reason, 
  oos_categories, 
  year_used 
}) => {
  // Strip [[chunk_id]] tags from displayed text
  const cleanContent = content ? content.replace(/\[\[chunk_id:\d+\]\]/g, '').trim() : '';
  
  // B5: Render behavior-specific banners
  const renderBehaviorBanner = () => {
    switch (behavior) {
      case 'fallback_warning':
        return (
          <div className="behavior-banner warning">
            <span className="behavior-icon">⚠️</span>
            <span className="behavior-text">
              Câu trả lời có thể chưa chính xác. Vui lòng xác nhận lại với trường.
            </span>
          </div>
        );
      case 'refused':
        return (
          <div className="behavior-banner refused">
            <span className="behavior-icon">❌</span>
            <span className="behavior-text">
              {refused_reason === 'off_topic' 
                ? 'Câu hỏi nằm ngoài phạm vi tư vấn tuyển sinh của UTH.'
                : refused_reason === 'harmful'
                ? 'Câu hỏi vi phạm chính sách sử dụng.'
                : 'Không thể trả lời câu hỏi này.'
              }
            </span>
          </div>
        );
      case 'clarify':
        return (
          <div className="behavior-banner clarify">
            <span className="behavior-icon">❓</span>
            <span className="behavior-text">
              Vui lòng cung cấp thêm thông tin để mình trả lời chính xác hơn.
            </span>
            {oos_categories && oos_categories.length > 0 && (
              <span className="behavior-hint">
                (Cần thêm: {oos_categories.join(', ')})
              </span>
            )}
          </div>
        );
      default:
        return null;
    }
  };
  
  return (
    <div className="bot-message-wrapper">
      {/* Behavior banner */}
      {renderBehaviorBanner()}
      
      {/* Main answer content */}
      <div className="bot-answer-text">
        {cleanContent.split('\n').map((line, index) => (
          <React.Fragment key={index}>
            {line}
            {index < cleanContent.split('\n').length - 1 && <br />}
          </React.Fragment>
        ))}
      </div>
      
      {/* B2: Citation badges */}
      {behavior !== 'refused' && (
        <CitationBadges citations={citations} />
      )}
      
      {/* Latency info */}
      {year_used && (
        <div className="bot-meta">
          <span className="year-used">Dữ liệu năm {year_used}</span>
        </div>
      )}
    </div>
  );
};

export default BotMessage;
