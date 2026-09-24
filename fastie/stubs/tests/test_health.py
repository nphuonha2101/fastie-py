def test_healthz(client):
    response = client.get("/healthz")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_readyz_uses_the_test_database(client):
    response = client.get("/readyz")

    assert response.status_code == 200
    assert response.json() == {"status": "ready"}
