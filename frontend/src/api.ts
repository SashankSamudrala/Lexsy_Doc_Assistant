// src/api.ts
import axios from "axios";
const API = import.meta.env.VITE_API_URL;

export async function uploadDoc(file: File) {
  const fd = new FormData();
  fd.append("file", file);
  const res = await axios.post(`${API}/api/upload`, fd, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return res.data;
}

export async function getPlaceholders(sessionId: string) {
  const res = await axios.get(
    `${API}/api/placeholders?session_id=${sessionId}`
  );
  return res.data;
}

export async function render(sessionId: string) {
  const res = await axios.get(`${API}/api/render?session_id=${sessionId}`);
  return res.data;
}

export async function fillOne(sessionId: string, key: string, value: string) {
  const fd = new FormData();
  fd.append("session_id", sessionId);
  fd.append("key", key);
  fd.append("value", value);
  const res = await axios.post(`${API}/api/fill`, fd);
  return res.data;
}

export async function fillBulk(
  sessionId: string,
  mapping: Record<string, string>
) {
  const fd = new FormData();
  fd.append("session_id", sessionId);
  fd.append("mapping_json", JSON.stringify(mapping));
  const res = await axios.post(`${API}/api/fill-bulk`, fd);
  return res.data;
}

export async function chat(sessionId: string, message: string) {
  const fd = new FormData();
  fd.append("session_id", sessionId);
  fd.append("message", message);
  const res = await axios.post(`${API}/api/chat`, fd);
  return res.data as { reply: string; suggestions: Record<string, string> };
}

export async function messages(sessionId: string) {
  const res = await axios.get(`${API}/api/messages?session_id=${sessionId}`);
  return res.data as { role: "user" | "assistant"; content: string }[];
}

export async function applySuggestion(
  sessionId: string,
  key: string,
  value: string
) {
  const fd = new FormData();
  fd.append("session_id", sessionId);
  fd.append("key", key);
  fd.append("value", value);
  const res = await axios.post(`${API}/api/apply-suggestion`, fd);
  return res.data;
}

export async function rejectSuggestion(
  sessionId: string,
  key: string,
  value: string
) {
  const fd = new FormData();
  fd.append("session_id", sessionId);
  fd.append("key", key);
  fd.append("value", value);
  const res = await axios.post(`${API}/api/reject-suggestion`, fd);
  return res.data;
}

export function download(sessionId: string) {
  window.open(`${API}/api/download?session_id=${sessionId}`, "_blank");
}
