export type MessageRole =
  | "user"
  | "assistant";


export interface Message {
  id: string;
  role: MessageRole;
  content: string;
}


/**
 * Request sent to the FastAPI backend.
 */
export interface ChatRequest {
  question: string;
}


/**
 * Response returned by:
 *
 * POST /api/v1/chat
 */
export interface ChatResponse {
  success: boolean;
  answer: string;
  error: string | null;
  request_id: string;
}