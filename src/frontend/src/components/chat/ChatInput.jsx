import React, { useState, useRef, useEffect } from 'react';
import { Send } from 'lucide-react';
import Button from '../common/Button';
import Chip from '../common/Chip';
import { Database } from 'lucide-react';

export default function ChatInput({
  onSend,
  disabled = false,
  activeConnection,
  suggestedText = '',
}) {
  const [text, setText] = useState('');
  const textareaRef = useRef(null);

  // If suggestedText changes (from clicking a suggestion), update the input
  useEffect(() => {
    if (suggestedText) {
      setText(suggestedText);
      textareaRef.current?.focus();
    }
  }, [suggestedText]);

  const handleSend = () => {
    const trimmed = text.trim();
    if (!trimmed || disabled) return;
    onSend(trimmed);
    setText('');
    // Reset textarea height
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleInput = (e) => {
    setText(e.target.value);
    // Auto-resize textarea
    const el = e.target;
    el.style.height = 'auto';
    el.style.height = Math.min(el.scrollHeight, 120) + 'px';
  };

  return (
    <div className="chat-input-container">
      {activeConnection && (
        <div className="chat-input-connection">
          <Chip icon={Database} variant="muted">
            {activeConnection.name} ({activeConnection.dbType})
          </Chip>
        </div>
      )}
      <div className="chat-input-wrapper">
        <textarea
          ref={textareaRef}
          className="chat-input-field"
          placeholder="Ask your database a question..."
          value={text}
          onChange={handleInput}
          onKeyDown={handleKeyDown}
          disabled={disabled}
          rows={1}
          aria-label="Query input"
        />
        <Button
          variant="secondary"
          icon={Send}
          size="icon"
          onClick={handleSend}
          disabled={!text.trim() || disabled}
          aria-label="Send query"
        />
      </div>
    </div>
  );
}
