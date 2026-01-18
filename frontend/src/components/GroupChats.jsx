import { useState, useEffect, useRef } from 'react';
import './GroupChats.css';

export default function GroupChats({
  session,
  onSendMessage,
  isLoading,
  availableAdvisors,
  onNewChat,
}) {
  const [input, setInput] = useState('');
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [session]);

  const handleSubmit = (e) => {
    e.preventDefault();
    if (input.trim() && !isLoading) {
      onSendMessage(input.trim());
      setInput('');
    }
  };

  const getAdvisorName = (advisorId) => {
    const advisor = availableAdvisors.find((a) => a.id === advisorId);
    return advisor ? advisor.name : advisorId;
  };

  const renderMessage = (message) => {
    if (message.role === 'user') {
      return (
        <div key={message.id} className="message user-message">
          <div className="message-header">
            <span className="message-role">You</span>
          </div>
          <div className="message-content">{message.content}</div>
        </div>
      );
    }

    if (message.role === 'assistant') {
      return (
        <div key={message.id} className="message assistant-message">
          <div className="group-responses">
            {message.responses ? (
              message.responses.map((resp, idx) => (
                <div key={idx} className="advisor-response">
                  <div className="response-header">
                    <span className="advisor-name">{resp.advisor_name}</span>
                    <span className="advisor-model">{resp.model}</span>
                  </div>
                  <div className="response-content">{resp.response}</div>
                </div>
              ))
            ) : (
              <div className="loading-responses">
                <div className="spinner"></div>
                <span>Council members are responding...</span>
              </div>
            )}
          </div>
        </div>
      );
    }
  };

  if (!session) {
    return (
      <div className="group-chats-container">
        <div className="empty-state">
          <h2>Start a Group Chat</h2>
          <p>Select council members to start a conversation</p>
          <button className="primary-btn" onClick={onNewChat}>
            + New Group Chat
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="group-chats-container">
      <div className="group-chat-header">
        <div className="session-info">
          <h2>{session.title}</h2>
          <div className="session-members">
            {session.member_ids.map((id) => (
              <span key={id} className="member-badge">
                {getAdvisorName(id)}
              </span>
            ))}
          </div>
        </div>
      </div>

      <div className="messages-container">
        {session.messages && session.messages.length > 0 ? (
          <>
            {session.messages.map((message) => renderMessage(message))}
            <div ref={messagesEndRef} />
          </>
        ) : (
          <div className="no-messages">
            <p>Start the conversation with your selected council members</p>
          </div>
        )}
      </div>

      <div className="input-container">
        <form onSubmit={handleSubmit} className="input-form">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask your question..."
            disabled={isLoading}
            className="message-input"
          />
          <button
            type="submit"
            disabled={isLoading || !input.trim()}
            className="send-button"
          >
            {isLoading ? 'Sending...' : 'Send'}
          </button>
        </form>
      </div>
    </div>
  );
}
