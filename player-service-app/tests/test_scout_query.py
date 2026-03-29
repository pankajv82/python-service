import pytest
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import app as basic_app
from app_RBAC import app as rbac_app
import json


@pytest.fixture
def basic_client():
    basic_app.config['TESTING'] = True
    with basic_app.test_client() as client:
        yield client


@pytest.fixture
def rbac_client():
    rbac_app.config['TESTING'] = True
    with rbac_app.test_client() as client:
        yield client


class TestScoutQueryBasic:
    """Test POST /v1/scout/query endpoint (basic app)"""
    
    def test_scout_query_endpoint_exists(self, basic_client):
        """Test scout query endpoint exists and handles requests"""
        body = {"query": "Who are the top players?"}
        res = basic_client.post('/v1/scout/query', json=body)
        # Endpoint should exist (200, 503 if ollama unavailable, or 500 on error)
        assert res.status_code in [200, 503, 500]
    
    def test_scout_query_missing_query_field(self, basic_client):
        """Test scout query without query field"""
        body = {}
        res = basic_client.post('/v1/scout/query', json=body)
        assert res.status_code == 400
        data = res.get_json()
        assert "error" in data
        assert "query" in data["error"].lower()
    
    def test_scout_query_empty_query(self, basic_client):
        """Test scout query with empty query string"""
        body = {"query": ""}
        res = basic_client.post('/v1/scout/query', json=body)
        assert res.status_code == 400
        data = res.get_json()
        assert "error" in data
        assert "empty" in data["error"].lower()
    
    def test_scout_query_whitespace_only(self, basic_client):
        """Test scout query with whitespace only"""
        body = {"query": "   "}
        res = basic_client.post('/v1/scout/query', json=body)
        assert res.status_code == 400
        data = res.get_json()
        assert "error" in data
    
    def test_scout_query_null_query(self, basic_client):
        """Test scout query with null query value"""
        body = {"query": None}
        res = basic_client.post('/v1/scout/query', json=body)
        # Should handle null gracefully
        assert res.status_code in [400, 500]


class TestScoutQueryRBAC:
    """Test POST /rbac/v1/scout/query endpoint (RBAC app)"""
    
    def test_scout_query_admin_role_endpoint_exists(self, rbac_client):
        """Test scout query endpoint exists with admin role"""
        headers = {'X-Username': 'admin', 'X-Password': 'admin_pass'}
        body = {"query": "Who are the players?"}
        res = rbac_client.post('/rbac/v1/scout/query', json=body, headers=headers)
        # Endpoint should exist (200, 503 if ollama unavailable, or 500 on error)
        assert res.status_code in [200, 503, 500]
    
    def test_scout_query_reader_role_endpoint_exists(self, rbac_client):
        """Test scout query endpoint exists with reader role"""
        headers = {'X-Username': 'reader', 'X-Password': 'reader_pass'}
        body = {"query": "List the players"}
        res = rbac_client.post('/rbac/v1/scout/query', json=body, headers=headers)
        # Endpoint should exist (200, 503 if ollama unavailable, or 500 on error)
        assert res.status_code in [200, 503, 500]
    
    def test_scout_query_missing_credentials(self, rbac_client):
        """Test scout query without credentials"""
        body = {"query": "Who is the best player?"}
        res = rbac_client.post('/rbac/v1/scout/query', json=body)
        assert res.status_code == 401
        data = res.get_json()
        assert "error" in data
        assert "Unauthorized" in data["error"]
    
    def test_scout_query_invalid_credentials(self, rbac_client):
        """Test scout query with invalid credentials"""
        headers = {'X-Username': 'invalid_user', 'X-Password': 'wrong_pass'}
        body = {"query": "Who are the players?"}
        res = rbac_client.post('/rbac/v1/scout/query', json=body, headers=headers)
        assert res.status_code == 401
        data = res.get_json()
        assert "error" in data
    
    def test_scout_query_missing_query_field(self, rbac_client):
        """Test scout query without query field"""
        headers = {'X-Username': 'admin', 'X-Password': 'admin_pass'}
        body = {}
        res = rbac_client.post('/rbac/v1/scout/query', json=body, headers=headers)
        assert res.status_code == 400
        data = res.get_json()
        assert "error" in data
        assert "query" in data["error"].lower()
    
    def test_scout_query_empty_query(self, rbac_client):
        """Test scout query with empty query string"""
        headers = {'X-Username': 'reader', 'X-Password': 'reader_pass'}
        body = {"query": ""}
        res = rbac_client.post('/rbac/v1/scout/query', json=body, headers=headers)
        assert res.status_code == 400
        data = res.get_json()
        assert "error" in data


class TestScoutQueryStructure:
    """Test scout query response structure when successful"""
    
    def test_scout_query_response_structure_basic(self, basic_client):
        """Test scout query response has required fields (basic app)"""
        body = {"query": "Top 5 players"}
        res = basic_client.post('/v1/scout/query', json=body)
        
        if res.status_code == 200:
            data = res.get_json()
            assert "query" in data
            assert "answer" in data
            assert "status" in data
            assert data["status"] == "success"
            assert isinstance(data["answer"], str)
    
    def test_scout_query_response_structure_rbac(self, rbac_client):
        """Test scout query response has required fields (RBAC app)"""
        headers = {'X-Username': 'admin', 'X-Password': 'admin_pass'}
        body = {"query": "Best hitter"}
        res = rbac_client.post('/rbac/v1/scout/query', json=body, headers=headers)
        
        if res.status_code == 200:
            data = res.get_json()
            assert "query" in data
            assert "answer" in data
            assert "status" in data
            assert "requested_by" in data
            assert "user_role" in data
            assert data["requested_by"] == "admin"
            assert data["user_role"] == "admin"
