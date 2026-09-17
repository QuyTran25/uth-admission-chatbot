import React from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
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
  // Format text: strip citation IDs, preserve line breaks, format numbered/bullet lists
  const formatContent = (raw) => {
    if (!raw) return '';
    let text = raw.replace(/\[\[[^\]]+\]\]/g, '');
    // Thay thế khoảng trắng ngang liên tiếp, giữ nguyên \n
    text = text.replace(/[^\S\r\n]{2,}/g, ' ');
    // Tách các mục danh sách (1. 2. hoặc - •) nếu bị viết liền trên cùng 1 dòng
    text = text.replace(/([^\n])\s+(\d+\.\s+)/g, '$1\n\n$2');
    text = text.replace(/([^\n])\s+([•\-*]\s+)/g, '$1\n\n$2');
    // Tách câu kết nếu dính liền sau điểm số
    text = text.replace(/(\b\d+\s+điểm\s*\.?)\s+([A-ZÀ-Ỹ])/g, '$1\n\n$2');
    // Giới hạn tối đa 2 dấu xuống dòng
    text = text.replace(/\n{3,}/g, '\n\n');
    return text.trim();
  };

  const cleanContent = formatContent(content);
  
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
      <div className="bot-answer-text bot-prose">
        <ReactMarkdown remarkPlugins={[remarkGfm]}>
          {cleanContent}
        </ReactMarkdown>
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
