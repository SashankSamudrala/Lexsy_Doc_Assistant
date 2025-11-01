import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { uploadDoc } from "../api";

export default function Home() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [fileName, setFileName] = useState<string>("");
  const navigate = useNavigate();

  async function handleUpload(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    setFileName(file.name);
    setLoading(true);
    setError(null);
    try {
      const resp = await uploadDoc(file);
      // go to editor with session id
      navigate(`/editor/${resp.session_id}`);
    } catch (err) {
      console.error(err);
      setError("Upload failed. Please try again.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-indigo-50 via-white to-purple-50">
      <header className="max-w-5xl mx-auto px-6 py-8 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="h-10 w-10 rounded-xl bg-indigo-600 flex items-center justify-center text-white font-bold">
            L
          </div>
          <h1 className="text-2xl font-bold text-indigo-700">
            Lexsy · AI Legal Workflows
          </h1>
        </div>
        <span className="text-sm text-gray-500">
          Fast, scalable & founder-friendly
        </span>
      </header>

      <main className="max-w-5xl mx-auto px-6 py-8 grid md:grid-cols-2 gap-10 items-center">
        <div>
          <h2 className="text-4xl font-extrabold text-indigo-800 leading-tight">
            Turn legal templates into{" "}
            <span className="text-purple-600">interactive</span> documents.
          </h2>
          <p className="mt-4 text-gray-600">
            Upload a Word template (.docx). We’ll detect dynamic placeholders,
            let you fill them via chat, and export a polished final document.
          </p>
          <div className="mt-8 p-6 bg-white rounded-2xl shadow flex items-center gap-4">
            <input
              type="file"
              accept=".docx"
              onChange={handleUpload}
              className="block"
            />
            {loading && <span className="text-indigo-600">Uploading…</span>}
            {fileName && !loading && (
              <span className="text-gray-600">Selected: {fileName}</span>
            )}
            {error && <span className="text-red-500">{error}</span>}
          </div>
          <p className="text-sm text-gray-400 mt-3">
            We never publish your files. Processing is local to this session.
          </p>
        </div>

        <div className="rounded-2xl bg-white shadow p-6">
          <div className="rounded-xl h-72 bg-gradient-to-br from-purple-100 to-indigo-100 flex items-center justify-center text-indigo-700 font-semibold">
            Preview-ready. Chat-powered. Founder-friendly.
          </div>
          <ul className="mt-6 text-gray-700 space-y-2 list-disc pl-5">
            <li>Detects placeholders automatically</li>
            <li>Word-like preview with highlighted fields</li>
            <li>LLM suggestions & normalization (Groq)</li>
            <li>Download as .docx</li>
          </ul>
        </div>
      </main>
    </div>
  );
}
