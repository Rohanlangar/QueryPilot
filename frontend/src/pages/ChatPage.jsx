import React, { useState } from 'react';
import { useParams } from 'react-router-dom';
import PageLayout from '../components/layout/PageLayout';
import Sidebar from '../components/layout/Sidebar';
import ChatContainer from '../components/chat/ChatContainer';
import useChatStore from '../store/chatStore';
import useConnectionStore from '../store/connectionStore';

// Demo mock data for a realistic first response
const MOCK_AGENT_RESPONSE = {
  id: 'msg-demo-1',
  role: 'agent',
  content: '',
  sql: 'SELECT p.product_name, SUM(oi.quantity * oi.unit_price) AS total_revenue\nFROM products p\nJOIN order_items oi ON p.product_id = oi.product_id\nJOIN orders o ON oi.order_id = o.order_id\nWHERE o.order_date >= CURRENT_DATE - INTERVAL \'1 month\'\nGROUP BY p.product_name\nORDER BY total_revenue DESC\nLIMIT 10;',
  optimizedSql: 'SELECT p.product_name, SUM(oi.quantity * oi.unit_price) AS total_revenue\nFROM products p\nINNER JOIN order_items oi ON p.product_id = oi.product_id\nINNER JOIN orders o ON oi.order_id = o.order_id\nWHERE o.order_date >= CURRENT_DATE - INTERVAL \'1 month\'\nGROUP BY p.product_name\nORDER BY total_revenue DESC\nFETCH FIRST 10 ROWS ONLY;',
  confidence: {
    level: 'high',
    message: 'All referenced columns verified',
    details: 'Found exact matches for products.product_name, order_items.quantity, order_items.unit_price, orders.order_date. Schema context included 4 relevant tables.',
  },
  pipelineStatus: [
    { name: 'Schema', status: 'complete', detail: 'Identified 4 relevant tables from 47 total' },
    { name: 'Generate', status: 'complete', detail: 'Generated PostgreSQL query with 2 JOINs' },
    { name: 'Validate', status: 'complete', detail: 'All columns exist, RBAC check passed' },
    { name: 'Optimize', status: 'complete', detail: 'Replaced LEFT JOINs with INNER JOINs (all non-nullable)' },
    { name: 'Explain', status: 'complete', detail: 'Generated plain-English explanation with insights' },
  ],
  results: {
    columns: [
      { name: 'product_name', type: 'string' },
      { name: 'total_revenue', type: 'number' },
    ],
    data: [
      { product_name: 'Enterprise Suite Pro', total_revenue: 248500 },
      { product_name: 'Cloud Analytics', total_revenue: 195300 },
      { product_name: 'Data Pipeline Tool', total_revenue: 167800 },
      { product_name: 'API Gateway', total_revenue: 143200 },
      { product_name: 'Security Dashboard', total_revenue: 128900 },
      { product_name: 'ML Platform', total_revenue: 112400 },
      { product_name: 'DevOps Monitor', total_revenue: 98700 },
      { product_name: 'Workflow Engine', total_revenue: 87300 },
      { product_name: 'Log Aggregator', total_revenue: 76500 },
      { product_name: 'Auth Service', total_revenue: 64200 },
    ],
  },
  explanation: 'The query found the <strong>top 10 products by revenue</strong> for the last month. <strong>Enterprise Suite Pro</strong> leads with $248,500 — nearly <strong>27% higher</strong> than the second-place product (Cloud Analytics at $195,300). The top 3 products account for 47% of total revenue, indicating significant concentration.',
  anomalies: [],
  suggestedQuestions: [
    'Compare to the same period last year',
    'Break down by region',
    'Show the monthly trend for the top 3',
  ],
  timestamp: new Date().toISOString(),
};

export default function ChatPage() {
  const { id: routeConvId } = useParams();
  const [sidebarOpen, setSidebarOpen] = useState(true);

  const {
    conversations,
    activeConversationId,
    isLoading,
    createConversation,
    setActiveConversation,
    addMessage,
    setLoading,
  } = useChatStore();

  const activeConnection = useConnectionStore((s) => s.getActiveConnection());

  // Resolve active conversation
  const currentConvId = routeConvId || activeConversationId;
  const activeConversation = conversations.find((c) => c.id === currentConvId);

  const handleNewConversation = () => {
    createConversation(activeConnection?.id || null);
  };

  const handleSendMessage = (text) => {
    let convId = currentConvId;

    // Auto-create conversation if none exists
    if (!convId) {
      convId = createConversation(activeConnection?.id || null);
    }

    // Add user message
    const userMsg = {
      id: `msg-${Date.now()}`,
      role: 'user',
      content: text,
      timestamp: new Date().toISOString(),
    };
    addMessage(convId, userMsg);
    setLoading(true);

    // Simulate agent response with demo data
    setTimeout(() => {
      const agentMsg = {
        ...MOCK_AGENT_RESPONSE,
        id: `msg-${Date.now()}`,
        timestamp: new Date().toISOString(),
      };
      addMessage(convId, agentMsg);
      setLoading(false);
    }, 2000);
  };

  return (
    <PageLayout withSidebar={sidebarOpen}>
      <Sidebar
        isOpen={sidebarOpen}
        conversations={conversations}
        activeConversationId={currentConvId}
        onSelectConversation={setActiveConversation}
        onNewConversation={handleNewConversation}
      />

      <div className="chat-page">
        <ChatContainer
          messages={activeConversation?.messages || []}
          isLoading={isLoading}
          activeConnection={activeConnection}
          onSendMessage={handleSendMessage}
        />
      </div>
    </PageLayout>
  );
}
