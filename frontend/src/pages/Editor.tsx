// src/pages/Editor.tsx
import { useEffect, useMemo, useRef, useState } from "react";
import { useParams } from "react-router-dom";
import { getPlaceholders, fillBulk, render, download, fillOne } from "../api";
import ChatPanel from "../components/ChatPanel";

type PH = {
  key: string;
  is_filled: boolean;
  value?: string | null;
  type: string;
};

export default function Editor() {
  const { sessionId } = useParams<{ sessionId: string }>();
  const [placeholders, setPlaceholders] = useState<PH[]>([]);
  const [values, setValues] = useState<Record<string, string>>({});
  const [html, setHtml] = useState("");
  const previewRef = useRef<HTMLDivElement>(null);

  async function refresh() {
    if (!sessionId) return;
    const ph = await getPlaceholders(sessionId);
    setPlaceholders(ph);
    const current: Record<string, string> = {};
    ph.forEach((p: PH) => {
      if (p.value) current[p.key] = p.value;
    });
    setValues(current);
    const r = await render(sessionId);
    setHtml(r.html);
  }
  useEffect(() => {
    refresh();
  }, [sessionId]);

  const completed = useMemo(
    () => placeholders.length > 0 && placeholders.every((p) => p.is_filled),
    [placeholders]
  );

  // click placeholder in list -> scroll preview to it
  function scrollPreviewToKey(key: string) {
    const root = previewRef.current;
    if (!root) return;
    const node = root.querySelector<HTMLElement>(
      `.ph[data-key="${CSS.escape(key)}"]`
    );

    if (node) {
      node.classList.add("ph-focus");
      node.scrollIntoView({ behavior: "smooth", block: "center" });
      setTimeout(() => node.classList.remove("ph-focus"), 1200);
    }
  }

  // attach click handler to preview to focus corresponding field
  useEffect(() => {
    const root = previewRef.current;
    if (!root) return;

    const onClick = (e: MouseEvent) => {
      const el = (e.target as HTMLElement).closest(".ph") as HTMLElement | null;
      if (!el) return;
      const key = el.dataset.key!;
      const box = document.querySelector<HTMLElement>(
        `[data-field-box="${CSS.escape(key)}"]`
      );
      if (box) {
        box.classList.add("field-focus");
        box.scrollIntoView({ behavior: "smooth", block: "center" });
        setTimeout(() => box.classList.remove("field-focus"), 1200);
      }
    };

    root.addEventListener("click", onClick as unknown as EventListener);
    return () =>
      root.removeEventListener("click", onClick as unknown as EventListener);
  }, [html]);

  async function saveAll() {
    if (!sessionId) return;
    await fillBulk(sessionId, values);
    await refresh();
  }

  async function fillSingle(key: string) {
    if (!sessionId) return;
    const val = values[key] ?? "";
    if (!val.trim()) return;
    await fillOne(sessionId, key, val);
    await refresh();
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-indigo-50 via-white to-purple-50">
      <div className="max-w-7xl mx-auto px-6 py-6">
        <header className="flex items-center justify-between">
          <h1 className="text-2xl font-bold text-indigo-700">
            Lexsy Document Assistant
          </h1>
          <button
            onClick={() => download(sessionId!)}
            className="px-4 py-2 rounded-lg bg-purple-600 text-white hover:bg-purple-700"
          >
            Download .docx
          </button>
        </header>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mt-6">
          {/* Preview */}
          <div className="bg-white rounded-2xl shadow p-4 h-[80vh] overflow-auto">
            <h2 className="text-lg font-semibold text-indigo-700 mb-2">
              Preview
            </h2>
            <div
              ref={previewRef}
              className="docx-preview"
              dangerouslySetInnerHTML={{ __html: html }}
            />
          </div>

          {/* Fields */}
          <div className="bg-white rounded-2xl shadow p-4 h-[80vh] overflow-auto">
            <h2 className="text-lg font-semibold text-indigo-700 mb-2">
              Fields ({placeholders.filter((p) => !p.is_filled).length} pending)
            </h2>
            <div className="space-y-3">
              {placeholders.map((p) => (
                <div
                  key={p.key}
                  data-field-box={p.key}
                  className={`border rounded-lg p-3 transition ${
                    p.is_filled ? "bg-green-50 border-green-200" : "bg-white"
                  }`}
                  onClick={() => scrollPreviewToKey(p.key)}
                >
                  <div className="flex items-center justify-between">
                    <div className="font-medium whitespace-pre-wrap">
                      {p.key || "(placeholder)"}
                    </div>

                    <span
                      className={
                        p.is_filled ? "text-green-600" : "text-orange-600"
                      }
                    >
                      {p.is_filled ? "✓ filled" : "• required"}
                    </span>
                  </div>
                  <input
                    className="mt-2 w-full border rounded px-3 py-2"
                    placeholder={
                      p.type === "DATE"
                        ? "October 1, 2025"
                        : p.type === "MONEY"
                        ? "$500,000"
                        : "Enter value"
                    }
                    value={values[p.key] ?? p.value ?? ""}
                    onChange={(e) =>
                      setValues((prev) => ({
                        ...prev,
                        [p.key]: e.target.value,
                      }))
                    }
                    onKeyDown={(e) => {
                      if (e.key === "Enter") fillSingle(p.key);
                    }}
                  />
                  <div className="mt-2 flex gap-2">
                    <button
                      onClick={() => fillSingle(p.key)}
                      className="px-3 py-1 rounded bg-indigo-600 text-white hover:bg-indigo-700"
                    >
                      Fill
                    </button>
                    <button
                      onClick={() => scrollPreviewToKey(p.key)}
                      className="px-3 py-1 rounded bg-gray-100 hover:bg-gray-200"
                    >
                      Show in document
                    </button>
                  </div>
                  <div className="text-xs text-gray-400 mt-1">
                    Type: {p.type}
                  </div>
                </div>
              ))}
            </div>
            <div className="mt-4">
              <button
                onClick={saveAll}
                className="px-4 py-2 rounded-lg bg-indigo-600 text-white hover:bg-indigo-700"
              >
                Save All
              </button>
              {completed && (
                <span className="ml-3 text-green-700 font-medium">
                  All fields filled 🎉
                </span>
              )}
            </div>
          </div>

          {/* Chat */}
          <ChatPanel sessionId={sessionId!} onApplied={refresh} />
        </div>
      </div>
    </div>
  );
}
