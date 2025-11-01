// src/sections/ChatPanel.tsx
import { useEffect, useRef, useState } from "react";
import { applySuggestion, chat, messages, rejectSuggestion } from "../api";

export default function ChatPanel({
  sessionId,
  onApplied,
}: {
  sessionId: string;
  onApplied: () => void;
}) {
  const [history, setHistory] = useState<
    { role: "user" | "assistant"; content: string }[]
  >([]);
  const [msg, setMsg] = useState("");
  const [pending, setPending] = useState<Record<string, string>>({});
  const bottomRef = useRef<HTMLDivElement>(null);

  async function load() {
    const h = await messages(sessionId);
    setHistory(h);
  }
  useEffect(() => {
    load();
  }, [sessionId]);
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [history, pending]);

  async function send() {
    if (!msg.trim()) return;
    const resp = await chat(sessionId, msg);
    setMsg("");
    await load();
    setPending(resp.suggestions || {});
  }

  async function accept(key: string) {
    const val = pending[key];
    await applySuggestion(sessionId, key, val);
    setPending((prev) => {
      const cp = { ...prev };
      delete cp[key];
      return cp;
    });
    await onApplied();
    await load();
  }

  async function reject(key: string) {
    const val = pending[key];
    await rejectSuggestion(sessionId, key, val);
    setPending((prev) => {
      const cp = { ...prev };
      delete cp[key];
      return cp;
    });
    await load();
  }

  return (
    <div className="bg-white rounded-2xl shadow p-4 h-[80vh] overflow-auto flex flex-col">
      <h2 className="text-lg font-semibold text-indigo-700 mb-2">
        AI Assistant
      </h2>

      <div className="flex-1 space-y-3 overflow-y-auto pr-2">
        {history.map((m, i) => (
          <div
            key={i}
            className={`max-w-[85%] rounded-2xl px-3 py-2 ${
              m.role === "user"
                ? "ml-auto bg-indigo-600 text-white"
                : "mr-auto bg-gray-100 text-gray-800"
            }`}
          >
            {m.content}
          </div>
        ))}

        {/* Pending suggestions (not applied yet) */}
        {Object.keys(pending).length > 0 && (
          <div className="mr-auto bg-amber-50 text-amber-900 border border-amber-200 rounded-2xl p-3 space-y-2">
            <div className="font-semibold">Suggestions</div>
            {Object.entries(pending).map(([k, v]) => (
              <div key={k} className="flex items-center justify-between gap-2">
                <div className="text-sm">
                  <span className="font-medium">{k}</span> → {v}
                </div>
                <div className="flex gap-2">
                  <button
                    onClick={() => accept(k)}
                    className="px-2 py-1 rounded bg-green-600 text-white hover:bg-green-700"
                  >
                    Accept
                  </button>
                  <button
                    onClick={() => reject(k)}
                    className="px-2 py-1 rounded bg-red-600 text-white hover:bg-red-700"
                  >
                    Reject
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}

        <div ref={bottomRef} />
      </div>

      <div className="mt-3 flex gap-2">
        <input
          value={msg}
          onChange={(e) => setMsg(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter") send();
          }}
          placeholder="e.g., Company Name is LEXSY, INC."
          className="flex-1 border rounded px-3 py-2"
        />
        <button
          onClick={send}
          className="px-4 py-2 rounded-lg bg-purple-600 text-white hover:bg-purple-700"
        >
          Send
        </button>
      </div>
    </div>
  );
}
