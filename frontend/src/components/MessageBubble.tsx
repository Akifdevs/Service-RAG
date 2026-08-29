import type { Message } from "../types/chat";

interface MessageBubbleProps {
  message: Message;
}

export default function MessageBubble({
  message,
}: MessageBubbleProps) {

  const isUser =
    message.role === "user";

  return (
    <div
      className={`message-row ${
        isUser
          ? "message-row-user"
          : "message-row-assistant"
      }`}
    >

      {!isUser && (
        <div className="avatar assistant-avatar">
          AI
        </div>
      )}

      <div
        className={`message-bubble ${
          isUser
            ? "user-message"
            : "assistant-message"
        }`}
      >
        {message.content}
      </div>

      {isUser && (
        <div className="avatar user-avatar">
          You
        </div>
      )}

    </div>
  );
}