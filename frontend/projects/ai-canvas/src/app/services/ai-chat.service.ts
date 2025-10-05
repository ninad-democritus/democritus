/**
 * AI Chat Service
 * Simple message storage service
 * Note: The actual query handling is now done in ai-chat.component.ts
 */

import { Injectable } from '@angular/core';
import { BehaviorSubject } from 'rxjs';
import { ChatMessage } from '../models/chat-message.model';

@Injectable({
  providedIn: 'root'
})
export class AIChatService {
  private messagesSubject = new BehaviorSubject<ChatMessage[]>([]);
  public messages$ = this.messagesSubject.asObservable();

  constructor() {
    // Add welcome message
    this.addMessage({
      id: this.generateId(),
      sender: 'ai',
      content: 'Hello! I can help you create data visualizations. You can either drag a chart type from the library and ask me to populate it, or simply describe what you want to see and I\'ll create a chart for you.',
      timestamp: new Date()
    });
  }

  /**
   * Add message to chat
   */
  addMessage(message: ChatMessage): void {
    const messages = this.messagesSubject.value;
    this.messagesSubject.next([...messages, message]);
  }

  /**
   * Update an existing message
   */
  updateMessage(id: string, updates: Partial<ChatMessage>): void {
    const messages = this.messagesSubject.value.map(msg => {
      if (msg.id === id) {
        const updated = { ...msg, ...updates };
        console.log('[AIChatService] Updated message:', {
          id,
          oldQueryInProgress: msg.queryInProgress,
          newQueryInProgress: updated.queryInProgress,
          content: updated.content
        });
        return updated;
      }
      return msg;
    });
    this.messagesSubject.next(messages);
  }

  /**
   * Remove message from chat
   */
  removeMessage(id: string): void {
    const messages = this.messagesSubject.value.filter(m => m.id !== id);
    this.messagesSubject.next(messages);
  }

  /**
   * Clear all messages
   */
  clearMessages(): void {
    this.messagesSubject.next([]);
  }

  /**
   * Generate unique ID
   */
  private generateId(): string {
    return `msg-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
  }
}

