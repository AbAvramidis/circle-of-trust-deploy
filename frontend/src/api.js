/**
 * API client for the Circle of Trust backend.
 */

const API_BASE = import.meta.env.MODE === 'test' 
  ? 'http://localhost:8000/api' 
  : '/api';

export const api = {
  /**
   * List all conversations.
   */
  async listConversations() {
    const response = await fetch(`${API_BASE}/conversations`);
    if (!response.ok) {
      throw new Error('Failed to list conversations');
    }
    return response.json();
  },

  /**
   * Create a new conversation.
   */
  async createConversation() {
    const response = await fetch(`${API_BASE}/conversations`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({}),
    });
    if (!response.ok) {
      throw new Error('Failed to create conversation');
    }
    return response.json();
  },

  /**
   * Get a specific conversation.
   */
  async getConversation(conversationId) {
    const response = await fetch(
      `${API_BASE}/conversations/${conversationId}`
    );
    if (!response.ok) {
      throw new Error('Failed to get conversation');
    }
    return response.json();
  },

  /**
   * Delete a conversation.
   */
  async deleteConversation(conversationId) {
    const response = await fetch(
      `${API_BASE}/conversations/${conversationId}`,
      {
        method: 'DELETE',
      }
    );
    if (!response.ok) {
      throw new Error('Failed to delete conversation');
    }
    return response.json();
  },

  /**
   * Send a message in a conversation.
   */
  async sendMessage(conversationId, content) {
    const response = await fetch(
      `${API_BASE}/conversations/${conversationId}/message`,
      {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ content }),
      }
    );
    if (!response.ok) {
      throw new Error('Failed to send message');
    }
    return response.json();
  },

  /**
   * Send a message and receive streaming updates.
   * @param {string} conversationId - The conversation ID
   * @param {string} content - The message content
   * @param {function} onEvent - Callback function for each event: (eventType, data) => void
   * @returns {Promise<void>}
   */
  async sendMessageStream(conversationId, content, onEvent) {
    const response = await fetch(
      `${API_BASE}/conversations/${conversationId}/message/stream`,
      {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ content }),
      }
    );

    if (!response.ok) {
      throw new Error('Failed to send message');
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      const chunk = decoder.decode(value, { stream: true });
      buffer += chunk;
      
      const lines = buffer.split('\n');
      // Keep the last potentially incomplete line in the buffer
      buffer = lines.pop();

      for (const line of lines) {
        if (line.trim() === '') continue;
        
        if (line.startsWith('data: ')) {
          const data = line.slice(6);
          try {
            const event = JSON.parse(data);
            onEvent(event.type, event);
          } catch (e) {
            console.error('Failed to parse SSE event:', e, 'Line:', line);
          }
        }
      }
    }
  },

  /**
   * List available Ollama models.
   */
  async listModels() {
    const response = await fetch(`${API_BASE}/models`);
    if (!response.ok) {
      throw new Error('Failed to list models');
    }
    return response.json();
  },

  /**
   * Get current council configuration.
   */
  async getCouncilConfig() {
    const response = await fetch(`${API_BASE}/council/config`);
    if (!response.ok) {
      throw new Error('Failed to get council config');
    }
    return response.json();
  },

  /**
   * Update council configuration.
   */
  async updateCouncilConfig(advisors) {
    const response = await fetch(`${API_BASE}/council/config`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ advisors }),
    });
    if (!response.ok) {
      throw new Error('Failed to update council config');
    }
    return response.json();
  },

  /**
   * Get monitoring data.
   */
  async getMonitoringData() {
    const response = await fetch(`${API_BASE}/monitoring`);
    if (!response.ok) {
      throw new Error('Failed to get monitoring data');
    }
    return response.json();
  },

  // ============================================================================
  // Group Chat APIs
  // ============================================================================

  /**
   * List all group chat sessions.
   */
  async listGroupChats() {
    const response = await fetch(`${API_BASE}/group-chats`);
    if (!response.ok) {
      throw new Error('Failed to list group chats');
    }
    return response.json();
  },

  /**
   * Create a new group chat session with selected members.
   */
  async createGroupChat(memberIds) {
    const response = await fetch(`${API_BASE}/group-chats`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ member_ids: memberIds }),
    });
    if (!response.ok) {
      throw new Error('Failed to create group chat');
    }
    return response.json();
  },

  /**
   * Get a specific group chat session.
   */
  async getGroupChat(sessionId) {
    const response = await fetch(`${API_BASE}/group-chats/${sessionId}`);
    if (!response.ok) {
      throw new Error('Failed to get group chat');
    }
    return response.json();
  },

  /**
   * Delete a group chat session.
   */
  async deleteGroupChat(sessionId) {
    const response = await fetch(`${API_BASE}/group-chats/${sessionId}`, {
      method: 'DELETE',
    });
    if (!response.ok) {
      throw new Error('Failed to delete group chat');
    }
    return response.json();
  },

  /**
   * Send a message in a group chat.
   */
  async sendGroupChatMessage(sessionId, content) {
    const response = await fetch(
      `${API_BASE}/group-chats/${sessionId}/message`,
      {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ content }),
      }
    );
    if (!response.ok) {
      throw new Error('Failed to send group chat message');
    }
    return response.json();
  },

  /**
   * Send a message in a group chat and receive streaming updates.
   * @param {string} sessionId - The group chat session ID
   * @param {string} content - The message content
   * @param {function} onEvent - Callback function for each event: (eventType, data) => void
   * @returns {Promise<void>}
   */
  async sendGroupChatMessageStream(sessionId, content, onEvent) {
    const response = await fetch(
      `${API_BASE}/group-chats/${sessionId}/message/stream`,
      {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ content }),
      }
    );

    if (!response.ok) {
      throw new Error('Failed to send group chat message');
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      const chunk = decoder.decode(value, { stream: true });
      buffer += chunk;

      const lines = buffer.split('\n');
      // Keep the last potentially incomplete line in the buffer
      buffer = lines.pop();

      for (const line of lines) {
        if (line.trim() === '') continue;

        if (line.startsWith('data: ')) {
          const data = line.slice(6);
          try {
            const event = JSON.parse(data);
            onEvent(event.type, event);
          } catch (e) {
            console.error('Failed to parse SSE event:', e, 'Line:', line);
          }
        }
      }
    }
  },
};
