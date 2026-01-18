import { useState, useEffect } from 'react';
import Sidebar from './components/Sidebar';
import ChatInterface from './components/ChatInterface';
import CouncilSetup from './components/CouncilSetup';
import MonitoringDashboard from './components/MonitoringDashboard';
import GroupChats from './components/GroupChats';
import NewGroupChatModal from './components/NewGroupChatModal';
import { api } from './api';
import './App.css';

function App() {
  const [conversations, setConversations] = useState([]);
  const [currentConversationId, setCurrentConversationId] = useState(null);
  const [currentConversation, setCurrentConversation] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [showSetup, setShowSetup] = useState(false);
  const [showMonitoring, setShowMonitoring] = useState(false);
  const [activeTab, setActiveTab] = useState('conversations');
  
  // Group chat state
  const [groupChats, setGroupChats] = useState([]);
  const [currentGroupChatId, setCurrentGroupChatId] = useState(null);
  const [currentGroupChat, setCurrentGroupChat] = useState(null);
  const [showNewGroupChatModal, setShowNewGroupChatModal] = useState(false);
  const [availableAdvisors, setAvailableAdvisors] = useState([]);

  // Load conversations and group chats on mount
  useEffect(() => {
    loadConversations();
    loadGroupChats();
    loadCouncilConfig();
  }, []);

  const loadCouncilConfig = async () => {
    try {
      const config = await api.getCouncilConfig();
      setAvailableAdvisors(config.advisors || []);
      if (config.advisors.length === 0 && conversations.length === 0 && groupChats.length === 0) {
        setShowSetup(true);
      }
    } catch (e) {
      console.error("Failed to load council config", e);
    }
  };

  // Load conversation details when selected
  useEffect(() => {
    if (currentConversationId) {
      loadConversation(currentConversationId);
      setShowSetup(false);
      setShowMonitoring(false);
      setActiveTab('conversations');
    }
  }, [currentConversationId]);

  // Load group chat details when selected
  useEffect(() => {
    if (currentGroupChatId) {
      loadGroupChat(currentGroupChatId);
      setShowSetup(false);
      setShowMonitoring(false);
      setActiveTab('groupChats');
    }
  }, [currentGroupChatId]);

  const loadConversations = async () => {
    try {
      const convs = await api.listConversations();
      setConversations(convs);
      if (convs.length === 0) {
          setShowSetup(true);
      }
    } catch (error) {
      console.error('Failed to load conversations:', error);
    }
  };

  const loadConversation = async (id) => {
    try {
      const conv = await api.getConversation(id);
      setCurrentConversation(conv);
    } catch (error) {
      console.error('Failed to load conversation:', error);
    }
  };

  const handleNewConversation = async () => {
    try {
      const newConv = await api.createConversation();
      setConversations([
        { id: newConv.id, created_at: newConv.created_at, message_count: 0 },
        ...conversations,
      ]);
      setCurrentConversationId(newConv.id);
      setShowSetup(false);
    } catch (error) {
      console.error('Failed to create conversation:', error);
    }
  };

  const handleDeleteConversation = async (id) => {
    try {
      await api.deleteConversation(id);
      setConversations(conversations.filter(c => c.id !== id));
      if (currentConversationId === id) {
        setCurrentConversationId(null);
        setCurrentConversation(null);
      }
    } catch (error) {
      console.error('Failed to delete conversation:', error);
    }
  };

  // Group chat functions
  const loadGroupChats = async () => {
    try {
      const chats = await api.listGroupChats();
      setGroupChats(chats);
    } catch (error) {
      console.error('Failed to load group chats:', error);
    }
  };

  const loadGroupChat = async (id) => {
    try {
      const chat = await api.getGroupChat(id);
      setCurrentGroupChat(chat);
    } catch (error) {
      console.error('Failed to load group chat:', error);
    }
  };

  const handleNewGroupChat = () => {
    setShowNewGroupChatModal(true);
  };

  const handleCreateGroupChat = async (memberIds) => {
    try {
      const newChat = await api.createGroupChat(memberIds);
      setGroupChats([
        { 
          id: newChat.id, 
          created_at: newChat.created_at, 
          title: newChat.title,
          member_ids: newChat.member_ids,
          message_count: 0 
        },
        ...groupChats,
      ]);
      setCurrentGroupChatId(newChat.id);
      setShowNewGroupChatModal(false);
      setActiveTab('groupChats');
    } catch (error) {
      console.error('Failed to create group chat:', error);
    }
  };

  const handleDeleteGroupChat = async (id) => {
    try {
      await api.deleteGroupChat(id);
      setGroupChats(groupChats.filter(c => c.id !== id));
      if (currentGroupChatId === id) {
        setCurrentGroupChatId(null);
        setCurrentGroupChat(null);
      }
    } catch (error) {
      console.error('Failed to delete group chat:', error);
    }
  };

  const handleSelectConversation = (id) => {
    setCurrentConversationId(id);
    setCurrentGroupChatId(null);
  };

  const handleSelectGroupChat = (id) => {
    setCurrentGroupChatId(id);
    setCurrentConversationId(null);
  };

  const handleTabChange = (tab) => {
    setActiveTab(tab);
    if (tab === 'conversations') {
      setCurrentGroupChatId(null);
      setCurrentGroupChat(null);
    } else if (tab === 'groupChats') {
      setCurrentConversationId(null);
      setCurrentConversation(null);
    }
  };
  
  const handleSetupComplete = () => {
      setShowSetup(false);
      loadCouncilConfig();
      // If no conversation exists, create one?
      if (!currentConversationId) {
          handleNewConversation();
      }
  };

  const handleSendMessage = async (content) => {
    if (!currentConversationId) return;

    setIsLoading(true);
    try {
      // Optimistically add user message to UI
      const userMessage = { role: 'user', content };
      setCurrentConversation((prev) => ({
        ...prev,
        messages: [...prev.messages, userMessage],
      }));

      // Create a partial assistant message that will be updated progressively
      const assistantMessage = {
        role: 'assistant',
        stage1: null,
        stage2: null,
        stage3: null,
        metadata: null,
        loading: {
          stage1: false,
          stage2: false,
          stage3: false,
        },
      };

      // Add the partial assistant message
      setCurrentConversation((prev) => ({
        ...prev,
        messages: [...prev.messages, assistantMessage],
      }));

      // Send message with streaming
      await api.sendMessageStream(currentConversationId, content, (eventType, event) => {
        switch (eventType) {
          case 'stage1_start':
            setCurrentConversation((prev) => {
              const messages = [...prev.messages];
              const lastMsg = messages[messages.length - 1];
              lastMsg.loading.stage1 = true;
              return { ...prev, messages };
            });
            break;

          case 'stage1_complete':
            setCurrentConversation((prev) => {
              const messages = [...prev.messages];
              const lastMsg = messages[messages.length - 1];
              lastMsg.stage1 = event.data;
              lastMsg.loading.stage1 = false;
              return { ...prev, messages };
            });
            break;

          case 'stage2_start':
            setCurrentConversation((prev) => {
              const messages = [...prev.messages];
              const lastMsg = messages[messages.length - 1];
              lastMsg.loading.stage2 = true;
              return { ...prev, messages };
            });
            break;

          case 'stage2_complete':
            setCurrentConversation((prev) => {
              const messages = [...prev.messages];
              const lastMsg = messages[messages.length - 1];
              lastMsg.stage2 = event.data;
              lastMsg.metadata = event.metadata;
              lastMsg.loading.stage2 = false;
              return { ...prev, messages };
            });
            break;

          case 'stage3_start':
            setCurrentConversation((prev) => {
              const messages = [...prev.messages];
              const lastMsg = messages[messages.length - 1];
              lastMsg.loading.stage3 = true;
              return { ...prev, messages };
            });
            break;

          case 'stage3_complete':
            setCurrentConversation((prev) => {
              const messages = [...prev.messages];
              const lastMsg = messages[messages.length - 1];
              lastMsg.stage3 = event.data;
              lastMsg.loading.stage3 = false;
              return { ...prev, messages };
            });
            break;

          case 'title_complete':
            // Reload conversations to get updated title
            loadConversations();
            break;

          case 'complete':
            // Stream complete, reload conversations list
            loadConversations();
            setIsLoading(false);
            break;

          case 'error':
            console.error('Stream error:', event.message);
            setIsLoading(false);
            break;

          default:
            console.log('Unknown event type:', eventType);
        }
      });
    } catch (error) {
      console.error('Failed to send message:', error);
      // Remove optimistic messages on error
      setCurrentConversation((prev) => ({
        ...prev,
        messages: prev.messages.slice(0, -2),
      }));
      setIsLoading(false);
    }
  };

  const handleSendGroupChatMessage = async (content) => {
    if (!currentGroupChatId) return;

    setIsLoading(true);
    try {
      // Optimistically add user message to UI
      const userMessage = { role: 'user', content };
      setCurrentGroupChat((prev) => ({
        ...prev,
        messages: [...prev.messages, userMessage],
      }));

      // Create a partial assistant message
      const assistantMessage = {
        role: 'assistant',
        responses: null,
      };

      // Add the partial assistant message
      setCurrentGroupChat((prev) => ({
        ...prev,
        messages: [...prev.messages, assistantMessage],
      }));

      // Send message with streaming
      await api.sendGroupChatMessageStream(currentGroupChatId, content, (eventType, event) => {
        switch (eventType) {
          case 'responses_start':
            // Loading state already set
            break;

          case 'responses_complete':
            setCurrentGroupChat((prev) => {
              const messages = [...prev.messages];
              const lastMsg = messages[messages.length - 1];
              lastMsg.responses = event.data;
              return { ...prev, messages };
            });
            break;

          case 'title_complete':
            // Reload group chats to get updated title
            loadGroupChats();
            break;

          case 'complete':
            // Stream complete, reload group chats list
            loadGroupChats();
            setIsLoading(false);
            break;

          case 'error':
            console.error('Stream error:', event.message);
            setIsLoading(false);
            break;

          default:
            console.log('Unknown event type:', eventType);
        }
      });
    } catch (error) {
      console.error('Failed to send group chat message:', error);
      // Remove optimistic messages on error
      setCurrentGroupChat((prev) => ({
        ...prev,
        messages: prev.messages.slice(0, -2),
      }));
      setIsLoading(false);
    }
  };

  return (
    <div className="app">
      <Sidebar
        conversations={conversations}
        currentConversationId={currentConversationId}
        onSelectConversation={handleSelectConversation}
        onNewConversation={handleNewConversation}
        onDeleteConversation={handleDeleteConversation}
        groupChats={groupChats}
        currentGroupChatId={currentGroupChatId}
        onSelectGroupChat={handleSelectGroupChat}
        onNewGroupChat={handleNewGroupChat}
        onDeleteGroupChat={handleDeleteGroupChat}
        activeTab={activeTab}
        onTabChange={handleTabChange}
      />
      <div className="main-content">
          <div className="top-bar">
              <button className="config-btn" onClick={() => setShowMonitoring(true)} style={{marginRight: '10px'}}>
                  📊 Monitoring
              </button>
              <button className="config-btn" onClick={() => setShowSetup(true)}>
                  ⚙️ Configure Council
              </button>
          </div>
          
          {showMonitoring ? (
            <MonitoringDashboard onClose={() => setShowMonitoring(false)} />
          ) : showSetup ? (
            <CouncilSetup onComplete={handleSetupComplete} />
          ) : activeTab === 'groupChats' ? (
            <GroupChats
                session={currentGroupChat}
                onSendMessage={handleSendGroupChatMessage}
                isLoading={isLoading}
                availableAdvisors={availableAdvisors}
                onNewChat={handleNewGroupChat}
            />
          ) : (
            <ChatInterface
                conversation={currentConversation}
                onSendMessage={handleSendMessage}
                isLoading={isLoading}
            />
          )}
      </div>
      
      {showNewGroupChatModal && (
        <NewGroupChatModal
          availableAdvisors={availableAdvisors}
          onClose={() => setShowNewGroupChatModal(false)}
          onCreate={handleCreateGroupChat}
        />
      )}
    </div>
  );
}

export default App;
