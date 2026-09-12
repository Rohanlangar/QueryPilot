import React, { useRef, useEffect, useState } from 'react';
import { Database } from 'lucide-react';
import MessageBubble from './MessageBubble';
import ChatInput from './ChatInput';
import Chip from '../common/Chip';
import Loader from '../common/Loader';
import PipelineLoader from './PipelineLoader';
import useChatStore from '../../store/chatStore';

const SAMPLE_QUESTIONS = [
  "What were last month's top 10 products by revenue?",
  "Show me the monthly sales trend for 2024",
  "Which region has the highest customer churn rate?",
  "Compare Q3 vs Q4 performance by department",
  "List all orders above $10,000 in the last 30 days",
  "What's the average delivery time by category?",
];

export default function ChatContainer({
  messages = [],
  isLoading = false,
  activeConnection,
  onSendMessage,
}) {
  const messagesEndRef = useRef(null);
  const [suggestedText, setSuggestedText] = useState('');
  const currentStageId = useChatStore((state) => state.currentStageId);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSuggestedSelect = (question) => {
    setSuggestedText(question);
    // Reset after a tick so the useEffect in ChatInput fires
    setTimeout(() => setSuggestedText(''), 0);
  };

  return (
    <div className="chat-main">
      <div className="chat-messages">
        {messages.length === 0 ? (
          <div className="chat-empty">
            <div className="chat-empty-icon">
              <Database size={28} />
            </div>
            <h2 className="chat-empty-title">Ask your database anything</h2>
            <p className="chat-empty-desc">
              Type a question in plain English. QueryPilot will generate, validate, optimize, and explain the SQL for you.
            </p>
            <div className="chat-empty-suggestions">
              {SAMPLE_QUESTIONS.map((q, idx) => (
                <Chip
                  key={idx}
                  onClick={() => handleSuggestedSelect(q)}
                >
                  {q}
                </Chip>
              ))}
            </div>
          </div>
        ) : (
          <>
            {messages.map((msg) => (
              <MessageBubble
                key={msg.id}
                message={msg}
                onSuggestedSelect={handleSuggestedSelect}
              />
            ))}
            {isLoading && (
              <div className="message message-agent">
                <div className="agent-response" style={{ width: '100%', maxWidth: '640px' }}>
                  <PipelineLoader activeStageId={currentStageId} />
                </div>
              </div>
            )}
          </>
        )}
        <div ref={messagesEndRef} />
      </div>

      <ChatInput
        onSend={onSendMessage}
        disabled={isLoading}
        activeConnection={activeConnection}
        suggestedText={suggestedText}
      />
    </div>
  );
}
