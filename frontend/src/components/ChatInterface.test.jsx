import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import ChatInterface from './ChatInterface';

describe('ChatInterface', () => {
  it('renders welcome message when no conversation is selected', () => {
    render(<ChatInterface conversation={null} />);
    expect(screen.getByText(/Welcome to Circle of Trust/i)).toBeInTheDocument();
  });

  it('renders empty state for new conversation', () => {
    const conversation = { messages: [] };
    render(<ChatInterface conversation={conversation} />);
    expect(screen.getByText(/Start a conversation/i)).toBeInTheDocument();
    expect(screen.getByPlaceholderText(/Ask your question/i)).toBeInTheDocument();
  });

  it('calls onSendMessage when form is submitted', () => {
    const onSendMessage = vi.fn();
    const conversation = { messages: [] };
    render(
      <ChatInterface 
        conversation={conversation} 
        onSendMessage={onSendMessage} 
        isLoading={false} 
      />
    );

    const input = screen.getByPlaceholderText(/Ask your question/i);
    fireEvent.change(input, { target: { value: 'Hello Council' } });
    
    const button = screen.getByText('Send');
    fireEvent.click(button);

    expect(onSendMessage).toHaveBeenCalledWith('Hello Council');
  });

  it('disables input when loading', () => {
    const conversation = { messages: [] };
    render(
      <ChatInterface 
        conversation={conversation} 
        isLoading={true} 
      />
    );

    const input = screen.getByPlaceholderText(/Ask your question/i);
    expect(input).toBeDisabled();
    
    const button = screen.getByText('Send');
    expect(button).toBeDisabled();
  });
});
