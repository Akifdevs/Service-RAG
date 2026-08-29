import { useState } from "react";

import ChatInput from "./ChatInput";
import MessageBubble from "./MessageBubble";
import TypingIndicator from "./TypingIndicator";

import { sendMessage as sendChatMessage } from "../services/api";

import type { Message } from "../types/chat";


interface ChatProps {
  onClose: () => void;
}


export default function Chat({
  onClose,
}: ChatProps) {

  const [messages, setMessages] = useState<Message[]>([
    {
      id: "welcome",
      role: "assistant",
      content:
        "Hi! I can help you find answers from the service documentation.",
    },
  ]);

  const [isLoading, setIsLoading] = useState(false);


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
    setMessages((current) => [
      ...current,
      userMessage,
    ]);


    setIsLoading(true);


    try {

      // -----------------------------------------------------
      // Call backend through services/api.ts
      // -----------------------------------------------------

      const data = await sendChatMessage(
        question
      );


      // -----------------------------------------------------
      // Build assistant message
      // -----------------------------------------------------

      const assistantMessage: Message = {
        id: crypto.randomUUID(),
        role: "assistant",
        content:
          data.answer ||
          "I couldn't provide a reliable answer from the available documentation.",
      };


      setMessages((current) => [
        ...current,
        assistantMessage,
      ]);


    } catch (error) {

      console.error(
        "Chat request failed:",
        error
      );


      // -----------------------------------------------------
      // User-friendly error
      // -----------------------------------------------------

      const errorMessage: Message = {
        id: crypto.randomUUID(),
        role: "assistant",
        content:
          "Sorry, I couldn't connect to the documentation service. Please try again.",
      };


      setMessages((current) => [
        ...current,
        errorMessage,
      ]);


    } finally {

      setIsLoading(false);

    }
  }


  // =========================================================
  // RENDER
  // =========================================================

  return (
    <section
      className="chat-widget"
      aria-label="Service Assistant"
    >

      {/* =====================================================
          HEADER
          ===================================================== */}

      <header className="chat-header">

        <div className="chat-header-info">

          <div
            className="chat-avatar"
            aria-hidden="true"
          >
            ✦
          </div>


          <div>

            <h2>
              Service Assistant
            </h2>

            <span>
              Documentation powered
            </span>

          </div>

        </div>


        <button
          type="button"
          className="chat-close"
          onClick={onClose}
          aria-label="Close chatbot"
        >
          ×
        </button>

      </header>


      {/* =====================================================
          MESSAGES
          ===================================================== */}

      <div className="chat-messages">

        {messages.map((message) => (

          <MessageBubble
            key={message.id}
            message={message}
          />

        ))}


        {isLoading && (
          <TypingIndicator />
        )}

      </div>


      {/* =====================================================
          INPUT
          ===================================================== */}

      <ChatInput
        onSend={sendMessage}
        disabled={isLoading}
      />

    </section>
  );
}