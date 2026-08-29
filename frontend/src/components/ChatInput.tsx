import { useState } from "react";
import type {
  FormEvent,
  KeyboardEvent,
} from "react";

interface ChatInputProps {
  onSend: (message: string) => void;
  disabled?: boolean;
}

export default function ChatInput({
  onSend,
  disabled = false,
}: ChatInputProps) {

  const [value, setValue] = useState("");

  function sendMessage() {

    const message = value.trim();

    if (!message || disabled) {
      return;
    }

    onSend(message);
    setValue("");
  }

  function handleSubmit(
    event: FormEvent<HTMLFormElement>
  ) {

    event.preventDefault();

    sendMessage();
  }

  function handleKeyDown(
    event: KeyboardEvent<HTMLTextAreaElement>
  ) {

    if (
      event.key === "Enter" &&
      !event.shiftKey
    ) {

      event.preventDefault();

      sendMessage();
    }
  }

  return (
    <form
      className="chat-input-container"
      onSubmit={handleSubmit}
    >

      <textarea
        value={value}
        onChange={(event) =>
          setValue(event.target.value)
        }
        onKeyDown={handleKeyDown}
        placeholder="Ask about the service documentation..."
        disabled={disabled}
        rows={1}
      />

      <button
        type="submit"
        disabled={
          disabled ||
          !value.trim()
        }
        aria-label="Send message"
      >
        ↑
      </button>

    </form>
  );
}