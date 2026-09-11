import React from 'react';
import { MessageSquare, Plus } from 'lucide-react';
import Button from '../common/Button';

export default function Sidebar({
  isOpen,
  conversations = [],
  sessions,
  activeConversationId,
  activeSessionId,
  onSelectConversation,
  onNewConversation,
}) {
  const items = sessions || conversations;
  const currentId = activeSessionId || activeConversationId;

  const formatDate = (dateStr) => {
    if (!dateStr) return '';
    const d = new Date(dateStr);
    if (isNaN(d.getTime())) return '';
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
        {items.length === 0 ? (
          <div style={{ padding: '32px 14px', textAlign: 'center' }}>
            <p className="text-body-sm text-muted">No conversations yet.</p>
            <p className="text-label-sm text-muted" style={{ marginTop: '8px' }}>
              Start by asking your database a question.
            </p>
          </div>
        ) : (
          items.map((conv) => (
            <button
              key={conv.id}
              className={`sidebar-item ${conv.id === currentId ? 'active' : ''}`}
              onClick={() => onSelectConversation(conv.id)}
              aria-current={conv.id === currentId ? 'page' : undefined}
            >
              <span className="sidebar-item-icon">
                <MessageSquare size={16} />
              </span>
              <span className="sidebar-item-text">
                {conv.title || 'Untitled conversation'}
              </span>
              <span className="sidebar-item-meta">
                {formatDate(conv.created_at || conv.createdAt || conv.updated_at)}
              </span>
            </button>
          ))
        )}
      </div>
    </aside>
  );
}
