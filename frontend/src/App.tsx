import { useState } from "react";

import Chat from "./components/Chat";

import "./App.css";


function App() {

  const [isOpen, setIsOpen] =
    useState(false);


  return (
    <>

      {isOpen && (
        <Chat
          onClose={() =>
            setIsOpen(false)
          }
        />
      )}


      <button
        className={`chat-launcher ${
          isOpen
            ? "chat-launcher-open"
            : ""
        }`}
        onClick={() =>
          setIsOpen(
            (open) => !open
          )
        }
        aria-label={
          isOpen
            ? "Close chatbot"
            : "Open chatbot"
        }
      >

        {isOpen ? (

          "×"

        ) : (

          <svg
            width="26"
            height="26"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
            aria-hidden="true"
          >

            <rect
              x="3"
              y="5"
              width="18"
              height="14"
              rx="3"
            />

            <path d="M8 19v2" />

            <path d="M16 19v2" />

            <circle
              cx="9"
              cy="12"
              r="1"
            />

            <circle
              cx="15"
              cy="12"
              r="1"
            />

            <path d="M12 5V3" />

          </svg>

        )}

      </button>

    </>
  );
}


export default App;