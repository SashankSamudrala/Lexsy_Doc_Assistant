import { useState } from "react";
import { uploadDoc } from "../api";

export default function FileUpload({
  onSession,
}: {
  onSession: (sid: string) => void;
}) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleUpload(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    setLoading(true);
    setError(null);
    try {
      const resp = await uploadDoc(file);
      onSession(resp.session_id);
    } catch (err) {
      console.error(err);
      setError("Upload failed. Please try again.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="p-6 bg-white rounded-2xl shadow-md text-center max-w-lg mx-auto mt-16">
      <h2 className="text-xl font-semibold mb-3">
        Upload Your Legal Document (.docx)
      </h2>
      <input
        type="file"
        accept=".docx"
        onChange={handleUpload}
        className="block mx-auto mb-3"
      />
      {loading && <p className="text-blue-600">Uploading...</p>}
      {error && <p className="text-red-500">{error}</p>}
    </div>
  );
}
