import type {
  ChatRequest,
  ChatResponse,
} from "../types/chat";


const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ||
  "http://127.0.0.1:8000";


export async function sendMessage(
  question: string
): Promise<ChatResponse> {

  const request: ChatRequest = {
    question,
  };


  const response = await fetch(
    `${API_BASE_URL}/api/v1/chat`,
    {
      method: "POST",

      headers: {
        "Content-Type": "application/json",
      },

      body: JSON.stringify(request),
    }
  );


  if (!response.ok) {

    throw new Error(
      `API request failed: HTTP ${response.status}`
    );

  }


  return response.json();
}