import pytest
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app_RBAC import app
import json


@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client


class TestAuthentication:
    """Test authentication and authorization"""
    
    def test_missing_credentials(self, client):
        """Test request without credentials"""
        res = client.get('/rbac/v1/players')
        assert res.status_code == 401
        data = res.get_json()
        assert "error" in data
        assert "Invalid credentials" in data["error"]
    
    def test_invalid_username(self, client):
        """Test with invalid username"""
        headers = {'X-Username': 'invalid_user', 'X-Password': 'any_pass'}
        res = client.get('/rbac/v1/players', headers=headers)
        assert res.status_code == 401
        data = res.get_json()
        assert "error" in data
    
    def test_invalid_password(self, client):
        """Test with invalid password"""
        headers = {'X-Username': 'reader', 'X-Password': 'wrong_pass'}
        res = client.get('/rbac/v1/players', headers=headers)
        assert res.status_code == 401
        data = res.get_json()
        assert "error" in data


class TestAddPlayerRBAC:
    """Test POST /v1/players endpoint with RBAC"""
    
    def test_add_player_as_reader_forbidden(self, client):
        """Test adding a player as reader (should be forbidden)"""
        headers = {'X-Username': 'reader', 'X-Password': 'reader_pass'}
        body = {
            "playerId": "TEST_PLAYER_002",
            "nameFirst": "Jane",
            "nameLast": "Smith",
            "birthYear": 1992
        }
        res = client.post('/rbac/v1/players', json=body, headers=headers)
        assert res.status_code == 403
        data = res.get_json()
        assert "error" in data
        assert "admin" in data["error"]


class TestUpdatePlayerRBAC:
    """Test PUT /v1/players/<player_id> endpoint with RBAC"""
    
    def test_update_player_as_admin(self, client):
        """Test updating a player as admin"""
        headers = {'X-Username': 'admin', 'X-Password': 'admin_pass'}
        # Get an existing player first
        res = client.get('/rbac/v1/players', headers=headers)
        players = res.get_json()
        if len(players) > 0:
            player_id = players[0]["playerId"]
            body = {
                "nameFirst": "Updated",
                "nameLast": "Name",
                "birthYear": 1995
            }
            res = client.put(f'/rbac/v1/players/{player_id}', json=body, headers=headers)
            assert res.status_code in [200, 404]
            if res.status_code == 200:
                data = res.get_json()
                assert "message" in data
                assert "updated" in data["message"]
    
    def test_update_player_as_reader_forbidden(self, client):
        """Test updating a player as reader (should be forbidden)"""
        headers = {'X-Username': 'reader', 'X-Password': 'reader_pass'}
        body = {
            "nameFirst": "Test",
            "birthYear": 1990
        }
        res = client.put('/rbac/v1/players/any_id', json=body, headers=headers)
        assert res.status_code == 403
        data = res.get_json()
        assert "error" in data
        assert "admin" in data["error"]


class TestRoleBasedAccessControl:
    """Test role-based access control and field masking"""
    
    def test_admin_sees_all_fields(self, client):
        """Test that admin can see all fields"""
        headers = {'X-Username': 'admin', 'X-Password': 'admin_pass'}
        res = client.get('/rbac/v1/players', headers=headers)
        assert res.status_code == 200
        players = res.get_json()
        if len(players) > 0:
            player = players[0]
            # Admin should see all available fields
            assert "playerId" in player
            assert "nameFirst" in player
            assert "nameLast" in player
    
    def test_reader_sees_only_public_fields(self, client):
        """Test that reader can only see public fields"""
        headers = {'X-Username': 'reader', 'X-Password': 'reader_pass'}
        res = client.get('/rbac/v1/players', headers=headers)
        assert res.status_code == 200
        players = res.get_json()
        if len(players) > 0:
            player = players[0]
            # Reader should only see public fields
            assert "playerId" in player
            assert "nameFirst" in player
            assert "nameLast" in player
            # Reader should not see sensitive fields
            # Check that only expected fields are present
            allowed_fields = {'playerId', 'nameFirst', 'nameLast'}
            actual_fields = set(player.keys())
            assert actual_fields == allowed_fields, f"Reader seeing unexpected fields: {actual_fields - allowed_fields}"
    
    def test_admin_vs_reader_field_masking(self, client):
        """Test that admin sees more fields than reader"""
        admin_headers = {'X-Username': 'admin', 'X-Password': 'admin_pass'}
        reader_headers = {'X-Username': 'reader', 'X-Password': 'reader_pass'}
        
        admin_res = client.get('/rbac/v1/players', headers=admin_headers)
        reader_res = client.get('/rbac/v1/players', headers=reader_headers)
        
        admin_players = admin_res.get_json()
        reader_players = reader_res.get_json()
        
        if len(admin_players) > 0 and len(reader_players) > 0:
            admin_fields = set(admin_players[0].keys())
            reader_fields = set(reader_players[0].keys())
            # Admin should have more fields than reader
            assert len(admin_fields) >= len(reader_fields)
            # Reader fields should be a subset of admin fields
            assert reader_fields.issubset(admin_fields)
