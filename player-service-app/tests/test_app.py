import pytest
from app import app
import json


@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client


def test_pagination_metadata(client):
    res = client.get('/v1/players/all?page=1&size=5')
    data = res.get_json()

    assert res.status_code == 200
    assert "metadata" in data
    assert data["metadata"]["page_size"] == 5
    assert "total" in data["metadata"]
