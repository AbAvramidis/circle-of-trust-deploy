import { useState, useEffect } from 'react';
import './Sidebar.css';

export default function Sidebar({
  conversations,
  currentConversationId,
  onSelectConversation,
  onNewConversation,
  onDeleteConversation,
  groupChats,
  currentGroupChatId,
  onSelectGroupChat,
  onNewGroupChat,
  onDeleteGroupChat,
  activeTab,
  onTabChange,
}) {
  const handleDelete = (e, id) => {
    e.stopPropagation();
    if (window.confirm('Are you sure you want to delete this conversation?')) {
      onDeleteConversation(id);
    }
  };

  const handleDeleteGroupChat = (e, id) => {
    e.stopPropagation();
    if (window.confirm('Are you sure you want to delete this group chat?')) {
      onDeleteGroupChat(id);
    }
  };

  return (
    <div className="sidebar">
      <div className="sidebar-header">
        <h1>Circle of Trust</h1>
      </div>

      <div className="sidebar-tabs">
        <button
          className={`tab-button ${activeTab === 'conversations' ? 'active' : ''}`}
          onClick={() => onTabChange('conversations')}
        >
          Conversations
        </button>
        <button
          className={`tab-button ${activeTab === 'groupChats' ? 'active' : ''}`}
          onClick={() => onTabChange('groupChats')}
        >
          Group Chats
        </button>
      </div>

      {activeTab === 'conversations' && (
        <>
          <button className="new-conversation-btn" onClick={onNewConversation}>
            + New Conversation
          </button>

          <div className="conversation-list">
            {conversations.length === 0 ? (
              <div className="no-conversations">No conversations yet</div>
            ) : (
              conversations.map((conv) => (
                <div
                  key={conv.id}
                  className={`conversation-item ${
                    conv.id === currentConversationId ? 'active' : ''
                  }`}
                  onClick={() => onSelectConversation(conv.id)}
                >
                  <div className="conversation-content">
                    <div className="conversation-title">
                      {conv.title || 'New Conversation'}
                    </div>
                    <div className="conversation-meta">
                      {conv.message_count} messages
                    </div>
                  </div>
                  <button
                    className="delete-btn"
                    onClick={(e) => handleDelete(e, conv.id)}
                    title="Delete conversation"
                  >
                    ×
                  </button>
                </div>
              ))
            )}
          </div>
        </>
      )}

      {activeTab === 'groupChats' && (
        <>
          <button className="new-conversation-btn" onClick={onNewGroupChat}>
            + New Group Chat
          </button>

          <div className="conversation-list">
            {groupChats.length === 0 ? (
              <div className="no-conversations">No group chats yet</div>
            ) : (
              groupChats.map((chat) => (
                <div
                  key={chat.id}
                  className={`conversation-item ${
                    chat.id === currentGroupChatId ? 'active' : ''
                  }`}
                  onClick={() => onSelectGroupChat(chat.id)}
                >
                  <div className="conversation-content">
                    <div className="conversation-title">
                      {chat.title || 'New Group Chat'}
                    </div>
                    <div className="conversation-meta">
                      {chat.message_count} messages · {chat.member_ids.length} members
                    </div>
                  </div>
                  <button
                    className="delete-btn"
                    onClick={(e) => handleDeleteGroupChat(e, chat.id)}
                    title="Delete group chat"
                  >
                    ×
                  </button>
                </div>
              ))
            )}
          </div>
        </>
      )}
    </div>
  );
}
