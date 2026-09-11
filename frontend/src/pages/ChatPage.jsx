import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import PageLayout from '../components/layout/PageLayout';
import Sidebar from '../components/layout/Sidebar';
import ChatContainer from '../components/chat/ChatContainer';
import useChatStore from '../store/chatStore';
import useConnectionStore from '../store/connectionStore';

export default function ChatPage() {
  const { id: routeConvId } = useParams();
  const navigate = useNavigate();
  const [sidebarOpen, setSidebarOpen] = useState(true);

  const {
    sessions = [],
    activeSessionId,
    activeMessages = [],
    isLoading,
    isSending,
    fetchSessions,
    loadSession,
    createConversation,
    setActiveSession,
    sendMessage,
  } = useChatStore();

  const activeConnection = useConnectionStore((s) => s.getActiveConnection());

  // Fetch sessions on initial mount
  useEffect(() => {
    fetchSessions();
  }, [fetchSessions]);

  // Load session when route ID changes
  useEffect(() => {
    if (routeConvId && routeConvId !== activeSessionId) {
      loadSession(routeConvId);
    }
  }, [routeConvId, activeSessionId, loadSession]);

  const currentConvId = routeConvId || activeSessionId;

  const handleSelectConversation = (sessionId) => {
    setActiveSession(sessionId);
    loadSession(sessionId);
    navigate(`/chat/${sessionId}`);
  };

  const handleNewConversation = async () => {
    try {
      const newSessionId = await createConversation(activeConnection?.id || null);
      if (newSessionId) {
        navigate(`/chat/${newSessionId}`);
      }
    } catch (err) {
      console.error('Failed to create conversation:', err);
    }
  };

  const handleSendMessage = async (text) => {
    let convId = currentConvId;

    // Auto-create conversation if none exists
    if (!convId) {
      try {
        convId = await createConversation(activeConnection?.id || null);
        if (convId) {
          navigate(`/chat/${convId}`);
        }
      } catch (err) {
        console.error('Failed to auto-create conversation:', err);
        return;
      }
    }

    if (convId) {
      await sendMessage(convId, text);
    }
  };

  return (
    <PageLayout withSidebar={sidebarOpen}>
      <Sidebar
        isOpen={sidebarOpen}
        sessions={sessions}
        conversations={sessions}
        activeSessionId={currentConvId}
        activeConversationId={currentConvId}
        onSelectConversation={handleSelectConversation}
        onNewConversation={handleNewConversation}
      />

      <div className="chat-page">
        <ChatContainer
          messages={activeMessages}
          isLoading={isLoading || isSending}
          activeConnection={activeConnection}
          onSendMessage={handleSendMessage}
        />
      </div>
    </PageLayout>
  );
}
