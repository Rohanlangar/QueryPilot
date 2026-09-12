import React, { useState, useRef, useEffect } from 'react';
import { MessageSquare, Plus, Pencil, Trash2, Check, X } from 'lucide-react';
import Button from '../common/Button';

export default function Sidebar({
  isOpen,
  conversations = [],
  sessions,
  activeConversationId,
  activeSessionId,
  onSelectConversation,
  onNewConversation,
  onDeleteConversation,
  onRenameConversation,
}) {
  const items = sessions || conversations;
  const currentId = activeSessionId || activeConversationId;

  const [editingId, setEditingId] = useState(null);
  const [editTitle, setEditTitle] = useState('');
  const [deletingId, setDeletingId] = useState(null);
  const inputRef = useRef(null);

  useEffect(() => {
    if (editingId && inputRef.current) {
      inputRef.current.focus();
      inputRef.current.select();
    }
  }, [editingId]);

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

  const handleStartEdit = (conv, e) => {
    e?.stopPropagation();
    setDeletingId(null);
    setEditingId(conv.id);
    setEditTitle(conv.title || 'Untitled conversation');
  };

  const handleCancelEdit = (e) => {
    e?.stopPropagation();
    setEditingId(null);
    setEditTitle('');
  };

  const handleSaveEdit = (convId, e) => {
    e?.stopPropagation();
    const trimmed = editTitle.trim();
    if (trimmed) {
      onRenameConversation?.(convId, trimmed);
    }
    setEditingId(null);
    setEditTitle('');
  };

  const handleStartDelete = (convId, e) => {
    e?.stopPropagation();
    setEditingId(null);
    setDeletingId(convId);
  };

  const handleCancelDelete = (e) => {
    e?.stopPropagation();
    setDeletingId(null);
  };

  const handleConfirmDelete = (convId, e) => {
    e?.stopPropagation();
    onDeleteConversation?.(convId);
    setDeletingId(null);
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
          items.map((conv) => {
            const isActive = conv.id === currentId;
            const isEditing = editingId === conv.id;
            const isDeleting = deletingId === conv.id;

            return (
              <div
                key={conv.id}
                className={`sidebar-item ${isActive ? 'active' : ''} ${isEditing ? 'editing' : ''}`}
                onClick={() => {
                  if (!isEditing && !isDeleting) {
                    onSelectConversation(conv.id);
                  }
                }}
                role="button"
                tabIndex={0}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' || e.key === ' ') {
                    if (!isEditing && !isDeleting) {
                      onSelectConversation(conv.id);
                    }
                  }
                }}
                aria-current={isActive ? 'page' : undefined}
              >
                <span className="sidebar-item-icon">
                  <MessageSquare size={16} />
                </span>

                {isEditing ? (
                  <div className="sidebar-item-edit" onClick={(e) => e.stopPropagation()}>
                    <input
                      ref={inputRef}
                      type="text"
                      className="sidebar-item-input"
                      value={editTitle}
                      onChange={(e) => setEditTitle(e.target.value)}
                      onKeyDown={(e) => {
                        if (e.key === 'Enter') {
                          e.preventDefault();
                          handleSaveEdit(conv.id, e);
                        } else if (e.key === 'Escape') {
                          e.preventDefault();
                          handleCancelEdit(e);
                        }
                      }}
                    />
                    <button
                      type="button"
                      className="sidebar-action-btn confirm-btn"
                      title="Save (Enter)"
                      onClick={(e) => handleSaveEdit(conv.id, e)}
                    >
                      <Check size={14} />
                    </button>
                    <button
                      type="button"
                      className="sidebar-action-btn cancel-btn"
                      title="Cancel (Esc)"
                      onClick={handleCancelEdit}
                    >
                      <X size={14} />
                    </button>
                  </div>
                ) : isDeleting ? (
                  <div className="sidebar-item-delete" onClick={(e) => e.stopPropagation()}>
                    <span className="sidebar-delete-prompt">Delete?</span>
                    <button
                      type="button"
                      className="sidebar-action-btn delete-confirm-btn"
                      title="Confirm delete"
                      onClick={(e) => handleConfirmDelete(conv.id, e)}
                    >
                      <Check size={14} />
                    </button>
                    <button
                      type="button"
                      className="sidebar-action-btn cancel-btn"
                      title="Cancel (Esc)"
                      onClick={handleCancelDelete}
                    >
                      <X size={14} />
                    </button>
                  </div>
                ) : (
                  <>
                    <span className="sidebar-item-text" title={conv.title || 'Untitled conversation'}>
                      {conv.title || 'Untitled conversation'}
                    </span>
                    <span className="sidebar-item-meta">
                      {formatDate(conv.created_at || conv.createdAt || conv.updated_at)}
                    </span>
                    <div className="sidebar-item-actions">
                      <button
                        type="button"
                        className="sidebar-action-btn"
                        title="Rename conversation"
                        onClick={(e) => handleStartEdit(conv, e)}
                      >
                        <Pencil size={13} />
                      </button>
                      <button
                        type="button"
                        className="sidebar-action-btn delete-btn"
                        title="Delete conversation"
                        onClick={(e) => handleStartDelete(conv.id, e)}
                      >
                        <Trash2 size={13} />
                      </button>
                    </div>
                  </>
                )}
              </div>
            );
          })
        )}
      </div>
    </aside>
  );
}
