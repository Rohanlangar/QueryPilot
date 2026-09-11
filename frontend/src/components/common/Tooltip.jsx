import React, { useState } from 'react';

export default function Tooltip({ content, children, position = 'top' }) {
  const [visible, setVisible] = useState(false);

  return (
    <span
      className="tooltip-wrapper"
      onMouseEnter={() => setVisible(true)}
      onMouseLeave={() => setVisible(false)}
      onFocus={() => setVisible(true)}
      onBlur={() => setVisible(false)}
    >
      {children}
      {visible && content && (
        <span className="tooltip-content" role="tooltip">
          {content}
        </span>
      )}
    </span>
  );
}
