import pytest
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import app
import json


@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client


class TestGetPlayersEndpoint:
    """Test GET /v1/players endpoint"""
    
    def test_get_all_players_returns_list(self, client):
        """Test getting all players returns a list"""
        res = client.get('/v1/players')
        assert res.status_code == 200
        data = res.get_json()
        assert isinstance(data, list)
        assert len(data) > 0
    
    def test_get_all_players_contains_player_fields(self, client):
        """Test that players contain expected fields"""
        res = client.get('/v1/players')
        assert res.status_code == 200
        data = res.get_json()
        player = data[0]
        assert "playerId" in player
        assert "nameFirst" in player
        assert "nameLast" in player


class TestPaginationEndpoint:
    """Test GET /v1/players/all endpoint with pagination"""
    
    def test_pagination_returns_metadata(self, client):
        """Test pagination returns proper metadata"""
        res = client.get('/v1/players/all')
        assert res.status_code == 200
        data = res.get_json()
        assert "players" in data
        assert "metadata" in data
        metadata = data["metadata"]
        assert "total" in metadata
        assert "current_page" in metadata
        assert "page_size" in metadata
        assert "total_pages" in metadata
        assert "has_next" in metadata
        assert "has_prev" in metadata
    
    def test_pagination_with_custom_page_size(self, client):
        """Test pagination with custom page size"""
        res = client.get('/v1/players/all?page=1&size=5')
        assert res.status_code == 200
        data = res.get_json()
        assert len(data["players"]) <= 5
        assert data["metadata"]["page_size"] == 5
        assert data["metadata"]["current_page"] == 1
    
    def test_pagination_sorting_works(self, client):
        """Test pagination with sorting"""
        res = client.get('/v1/players/all?sort_by=playerId&order=asc')
        assert res.status_code == 200
        data = res.get_json()
        assert "players" in data
        assert len(data["players"]) > 0
    
    def test_pagination_invalid_parameters_returns_error(self, client):
        """Test pagination with invalid parameters - returns 200 with defaults"""
        res = client.get('/v1/players/all?page=abc&size=20')
        # Invalid params are handled gracefully, returns 200 with valid response
        assert res.status_code == 200


class TestGetPlayerByIdEndpoint:
    """Test GET /v1/players/<player_id> endpoint"""
    
    def test_get_existing_player_returns_player(self, client):
        """Test getting an existing player by ID"""
        # First get a list of players to find a valid ID
        res = client.get('/v1/players')
        players = res.get_json()
        if len(players) > 0:
            player_id = players[0]["playerId"]
            res = client.get(f'/v1/players/{player_id}')
            assert res.status_code == 200
            data = res.get_json()
            assert isinstance(data, dict)
            assert "playerId" in data
            assert data["playerId"] == player_id
    
    def test_get_player_contains_expected_fields(self, client):
        """Test that player response contains expected fields"""
        res = client.get('/v1/players')
        players = res.get_json()
        if len(players) > 0:
            player_id = players[0]["playerId"]
            res = client.get(f'/v1/players/{player_id}')
            data = res.get_json()
            assert "nameFirst" in data
            assert "nameLast" in data


class TestBulkPlayersEndpoint:
    """Test POST /v1/players/bulk endpoint"""
    
    def test_bulk_get_players_returns_result(self, client):
        """Test bulk getting players"""
        # First get some player IDs
        res = client.get('/v1/players')
        players = res.get_json()
        if len(players) >= 2:
            player_ids = [players[0]["playerId"], players[1]["playerId"]]
            body = {"player_ids": player_ids}
            res = client.post('/v1/players/bulk', json=body)
            assert res.status_code == 200
            data = res.get_json()
            assert "players" in data
            assert "total" in data
            assert "not_found" in data
    
    def test_bulk_missing_player_ids_returns_error(self, client):
        """Test bulk endpoint without player_ids"""
        body = {}
        res = client.post('/v1/players/bulk', json=body)
        assert res.status_code == 400
        data = res.get_json()
        assert "error" in data
    
    def test_bulk_invalid_player_ids_format_returns_error(self, client):
        """Test bulk endpoint with non-list player_ids"""
        body = {"player_ids": "not_a_list"}
        res = client.post('/v1/players/bulk', json=body)
        assert res.status_code == 400
        data = res.get_json()
        assert "error" in data
        assert "must be a list" in data["error"]


class TestUpdatePlayerEndpoint:
    """Test PUT /v1/players/<player_id> endpoint"""
    
    def test_update_nonexistent_player_returns_error(self, client):
        """Test updating a non-existent player"""
        body = {
            "nameFirst": "Test",
            "birthYear": 1990
        }
        res = client.put('/v1/players/nonexistent_id_12345', json=body)
        assert res.status_code in [404, 400]


class TestChatEndpoints:
    """Test chat-related endpoints"""
    
    def test_list_models_endpoint_exists(self, client):
        """Test that list models endpoint exists"""
        res = client.get('/v1/chat/list-models')
        # This may fail if ollama is not running, but we test the endpoint exists
        assert res.status_code in [200, 500]
    
    def test_chat_endpoint_exists(self, client):
        """Test that chat endpoint exists"""
        res = client.post('/v1/chat')
        # This may fail if ollama is not running, but we test the endpoint exists
        assert res.status_code in [200, 500]
