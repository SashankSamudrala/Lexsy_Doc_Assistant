# backend/tests/test_api.py
from fastapi.testclient import TestClient
from app import app

client = TestClient(app)

def test_upload_rejects_non_docx():
    res = client.post("/api/upload", files={"file": ("x.txt", b"hi", "text/plain")})
    assert res.status_code == 400
    assert res.json()["detail"] == "Only .docx supported"
