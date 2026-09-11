import { create } from 'zustand';

const useChatStore = create((set, get) => ({
  conversations: [],
  activeConversationId: null,
  isLoading: false,
  streamingMessage: null,

  createConversation: (connectionId) => {
    const id = `conv-${Date.now()}`;
    const newConv = {
      id,
      title: '',
      createdAt: new Date().toISOString(),
      connectionId,
      messages: [],
    };
    set((state) => ({
      conversations: [newConv, ...state.conversations],
      activeConversationId: id,
    }));
    return id;
  },

  setActiveConversation: (id) => {
    set({ activeConversationId: id });
  },

  deleteConversation: (id) => {
    set((state) => ({
      conversations: state.conversations.filter((c) => c.id !== id),
      activeConversationId:
        state.activeConversationId === id
          ? state.conversations[0]?.id || null
          : state.activeConversationId,
    }));
  },

  addMessage: (conversationId, message) => {
    set((state) => ({
      conversations: state.conversations.map((conv) => {
        if (conv.id !== conversationId) return conv;
        const messages = [...conv.messages, message];
        const title = conv.title || (message.role === 'user' ? message.content.slice(0, 60) : conv.title);
        return { ...conv, messages, title };
      }),
    }));
  },

  updateMessage: (conversationId, messageId, updates) => {
    set((state) => ({
      conversations: state.conversations.map((conv) => {
        if (conv.id !== conversationId) return conv;
        return {
          ...conv,
          messages: conv.messages.map((msg) =>
            msg.id === messageId ? { ...msg, ...updates } : msg
          ),
        };
      }),
    }));
  },

  updatePipelineStatus: (conversationId, messageId, stages) => {
    const { updateMessage } = get();
    updateMessage(conversationId, messageId, { pipelineStatus: stages });
  },

  setLoading: (loading) => set({ isLoading: loading }),

  setStreamingMessage: (msg) => set({ streamingMessage: msg }),

  getActiveConversation: () => {
    const state = get();
    return state.conversations.find((c) => c.id === state.activeConversationId) || null;
  },
}));

export default useChatStore;
