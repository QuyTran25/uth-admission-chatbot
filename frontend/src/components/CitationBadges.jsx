import React from 'react';

const CitationBadges = ({ citations }) => {
  if (!citations || citations.length === 0) return null;
  
  // Limit to 5 citations max
  const displayCitations = citations.slice(0, 5);
  
  const handleBadgeClick = (citation) => {
    if (citation.source_urls && citation.source_urls.length > 0) {
      window.open(citation.source_urls[0], '_blank', 'noopener,noreferrer');
    }
  };
  
  return (
    <div className="citation-badges">
      <span className="citation-label">
        <i className="fa-solid fa-book-open" style={{fontSize: '12px'}}></i>
        Nguồn:
      </span>
      <div className="citation-list">
        {displayCitations.map((citation, index) => (
          <button
            key={citation.chunk_id || index}
            className="citation-badge"
            onClick={() => handleBadgeClick(citation)}
            title={`${citation.source_file || 'Nguồn không xác định'} - ${citation.section_name || ''} (${citation.admission_year || ''})`}
          >
            <i className="fa-solid fa-file-lines" style={{fontSize: '11px'}}></i>
            <span className="citation-name">
              {citation.source_file || 'Nguồn'}
              {citation.section_name && ` - ${citation.section_name}`}
            </span>
            {citation.admission_year && (
              <span className="citation-year">{citation.admission_year}</span>
            )}
          </button>
        ))}
      </div>
    </div>
  );
};

export default CitationBadges;
