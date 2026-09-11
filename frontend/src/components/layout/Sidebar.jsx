import React from 'react';
import { MessageSquare, Plus } from 'lucide-react';
import Button from '../common/Button';

export default function Sidebar({
  isOpen,
  conversations = [],
  activeConversationId,
  onSelectConversation,
  onNewConversation,
}) {
  const formatDate = (dateStr) => {
    const d = new Date(dateStr);
    const now = new Date();
    const diff = now - d;
    if (diff < 60000) return 'Just now';
    if (diff < 3600000) return `${Math.floor(diff / 60000)}m ago`;
    if (diff < 86400000) return `${Math.floor(diff / 3600000)}h ago`;
    return d.toLocaleDateString();
  };

  return (
    <aside className={`sidebar ${isOpen ? 'sidebar-open' : ''}`} aria-label="Conversations">
      <div className="sidebar-header">
        <Button
          variant="secondary"
          icon={Plus}
          fullWidth
          size="sm"
          onClick={onNewConversation}
        >
          New Conversation
        </Button>
      </div>
      <div className="sidebar-content">
        {conversations.length === 0 ? (
          <div style={{ padding: '32px 14px', textAlign: 'center' }}>
            <p className="text-body-sm text-muted">No conversations yet.</p>
            <p className="text-label-sm text-muted" style={{ marginTop: '8px' }}>
              Start by asking your database a question.
            </p>
          </div>
        ) : (
          conversations.map((conv) => (
            <button
              key={conv.id}
              className={`sidebar-item ${conv.id === activeConversationId ? 'active' : ''}`}
              onClick={() => onSelectConversation(conv.id)}
              aria-current={conv.id === activeConversationId ? 'page' : undefined}
            >
              <span className="sidebar-item-icon">
                <MessageSquare size={16} />
              </span>
              <span className="sidebar-item-text">
                {conv.title || 'Untitled conversation'}
              </span>
              <span className="sidebar-item-meta">
                {formatDate(conv.createdAt)}
              </span>
            </button>
          ))
        )}
      </div>
    </aside>
  );
}
