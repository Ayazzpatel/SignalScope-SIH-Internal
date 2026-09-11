def test_health_reports_mock_detector(client):
    response = client.get("/api/v1/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["detector"] == "mock"
    assert body["detector_ready"] is True
    assert body["model_version"].startswith("mock-")
