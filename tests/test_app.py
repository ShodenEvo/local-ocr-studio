from fastapi.testclient import TestClient
from app.main import app


def test_home_page():
    response = TestClient(app).get("/")
    assert response.status_code == 200
    assert "Local OCR Studio" in response.text


def test_status_endpoint():
    response = TestClient(app).get("/api/status")
    assert response.status_code == 200
    body = response.json()
    assert "tesseract" in body
    assert "easyocr" in body
    assert "gpu" in body
