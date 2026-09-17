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
  year_used,
  fallback_warning_text
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
  
  return (
    <div className="bot-message-wrapper">
      {/* Main answer content */}
      <div className="bot-answer-text bot-prose">
        <ReactMarkdown remarkPlugins={[remarkGfm]}>
          {cleanContent}
        </ReactMarkdown>
      </div>
      
      {/* Citation badges */}
      {behavior !== 'refused' && behavior !== 'error' && (
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
