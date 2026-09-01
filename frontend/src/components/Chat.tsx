import { useEffect, useRef, useState } from "react";

import ChatInput from "./ChatInput";
import MessageBubble from "./MessageBubble";
import TypingIndicator from "./TypingIndicator";

import { sendMessage as sendChatMessage } from "../services/api";

import type { Message } from "../types/chat";

interface ChatProps {
  onClose: () => void;
}

const SUGGESTED_QUESTIONS = [
  "Confirming the Order",
  "How do I Delete a Package?",
  "How to view lab reports?",
];

export default function Chat({ onClose }: ChatProps) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);

  const messagesEndRef = useRef<HTMLDivElement>(null);

  // =========================================================
  // AUTO-SCROLL
  // Keep the newest message (or the typing indicator) in view
  // whenever the conversation grows.
  // =========================================================

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages, isLoading]);

  // =========================================================
  // SEND MESSAGE
  // =========================================================

  async function sendMessage(question: string) {
    const userMessage: Message = {
      id: crypto.randomUUID(),
      role: "user",
      content: question,
    };

    // Add user's message immediately.
    setMessages((current) => [...current, userMessage]);

    setIsLoading(true);

    try {
      // -----------------------------------------------------
      // Call backend through services/api.ts
      // -----------------------------------------------------

      const data = await sendChatMessage(question);

      // -----------------------------------------------------
      // Build assistant message
      // -----------------------------------------------------

      const assistantMessage: Message = {
        id: crypto.randomUUID(),
        role: "assistant",
        content:
          data.answer ||
          "I'm not confident enough in the available information to answer that accurately. Could you try rephrasing, or ask something else?",
      };

      setMessages((current) => [...current, assistantMessage]);
    } catch (error) {
      console.error("Chat request failed:", error);

      // -----------------------------------------------------
      // User-friendly error
      // -----------------------------------------------------

      const errorMessage: Message = {
        id: crypto.randomUUID(),
        role: "assistant",
        content:
          "Sorry, I'm having trouble connecting right now. Please try again in a moment.",
      };

      setMessages((current) => [...current, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  }

  // =========================================================
  // RENDER
  // =========================================================

  return (
    <section className="chat-widget" aria-label="AI Assistant">
      {/* =====================================================
          HEADER
          ===================================================== */}

      <header className="chat-header">
        <div className="chat-header-info">
          <div className="chat-brand-mark" aria-hidden="true">
                        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
              <rect x="5" y="9" width="14" height="11" rx="3" />
              <path d="M12 9V5" />
              <circle cx="12" cy="4" r="1" fill="currentColor" stroke="none" />
              <path d="M3 13v3" />
              <path d="M21 13v3" />
              <circle cx="9.5" cy="14.5" r="1.1" fill="currentColor" stroke="none" />
              <circle cx="14.5" cy="14.5" r="1.1" fill="currentColor" stroke="none" />
              <path d="M9.5 18h5" />
            </svg>
          </div>

          <div className="chat-header-text">
            <h2>AI Assistant</h2>
            <span className="chat-status">
              <span className="chat-status-dot" aria-hidden="true" />
              Online, ready to help
            </span>
          </div>
        </div>

        <button type="button" className="chat-close" onClick={onClose} aria-label="Close chatbot">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
            <path d="M18 6 6 18" />
            <path d="m6 6 12 12" />
          </svg>
        </button>
      </header>

      {/* =====================================================
          MESSAGES
          ===================================================== */}

      <div className="chat-messages">
        {messages.length === 0 ? (
          <div className="chat-welcome">
            <div className="chat-welcome-mark" aria-hidden="true">
                            <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
                <rect x="5" y="9" width="14" height="11" rx="3" />
                <path d="M12 9V5" />
                <circle cx="12" cy="4" r="1" fill="currentColor" stroke="none" />
                <path d="M3 13v3" />
                <path d="M21 13v3" />
                <circle cx="9.5" cy="14.5" r="1.1" fill="currentColor" stroke="none" />
                <circle cx="14.5" cy="14.5" r="1.1" fill="currentColor" stroke="none" />
                <path d="M9.5 18h5" />
              </svg>
            </div>

            <h3>Hi, I'm your AI Assistant!</h3>
            <p>Ask me anything about ordering services, insurance, or reports — I'm here to help.</p>

            <div className="chat-suggestions">
              {SUGGESTED_QUESTIONS.map((question) => (
                <button
                  key={question}
                  type="button"
                  className="chat-suggestion-chip"
                  onClick={() => sendMessage(question)}
                  disabled={isLoading}
                >
                  <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                    <circle cx="11" cy="11" r="7" />
                    <path d="m21 21-4.3-4.3" />
                  </svg>
                  {question}
                </button>
              ))}
            </div>
          </div>
        ) : (
          messages.map((message) => <MessageBubble key={message.id} message={message} />)
        )}

        {isLoading && <TypingIndicator />}

        <div ref={messagesEndRef} />
      </div>

      {/* =====================================================
          INPUT
          ===================================================== */}

      <ChatInput onSend={sendMessage} disabled={isLoading} />
    </section>
  );
}