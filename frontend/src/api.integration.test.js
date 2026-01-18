import { describe, it, expect, beforeAll } from 'vitest';
import { api } from './api';

describe('API Integration Tests', () => {
  let isBackendRunning = false;

  beforeAll(async () => {
    try {
      const response = await fetch('http://localhost:8001/');
      if (response.ok) {
        isBackendRunning = true;
      }
    } catch (e) {
      console.warn('Backend is not running. Integration tests will be skipped.');
    }
  });

  it('should list conversations', async () => {
    if (!isBackendRunning) return;
    
    const conversations = await api.listConversations();
    expect(Array.isArray(conversations)).toBe(true);
  });

  it('should create a new conversation', async () => {
    if (!isBackendRunning) return;

    const conversation = await api.createConversation();
    expect(conversation).toHaveProperty('id');
    expect(conversation).toHaveProperty('messages');
    expect(Array.isArray(conversation.messages)).toBe(true);
  });

  it('should get a conversation by id', async () => {
    if (!isBackendRunning) return;

    // Create one first
    const newConv = await api.createConversation();
    
    // Fetch it
    const fetchedConv = await api.getConversation(newConv.id);
    expect(fetchedConv.id).toBe(newConv.id);
  });
});
