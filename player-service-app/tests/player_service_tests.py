import pytest
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from player_service import PlayerService
import sqlite3


@pytest.fixture
def service():
    """Create a PlayerService instance for testing"""
    return PlayerService()


class TestPlayerServiceMethods:
    """Test cases for each method in PlayerService class"""
    
    def test_get_columns(self, service):
        """Test get_columns() method"""
        columns = service.get_columns()
        assert isinstance(columns, list)
        assert len(columns) > 0
        assert "playerId" in columns
    
    def test_convert_row_to_dict(self, service):
        """Test convert_row_to_dict() method"""
        # Create a sample row with values matching column count
        columns = service.get_columns()
        sample_row = tuple([f"value_{i}" for i in range(len(columns))])
        
        result = service.convert_row_to_dict(sample_row)
        assert isinstance(result, dict)
        assert len(result) == len(columns)
        assert all(col in result for col in columns)
    
    def test_get_all_players(self, service):
        """Test get_all_players() method"""
        result = service.get_all_players()
        assert isinstance(result, list)
        assert len(result) > 0
        # Check that first player has expected structure
        player = result[0]
        assert isinstance(player, dict)
        assert "playerId" in player
    
    def test_get_all_players_with_pagination(self, service):
        """Test get_all_players_with_pagination() method"""
        result = service.get_all_players_with_pagination(page=1, size=10)
        assert isinstance(result, dict)
        assert "players" in result
        assert "metadata" in result
        metadata = result["metadata"]
        assert "total" in metadata
        assert "current_page" in metadata
        assert metadata["current_page"] == 1
        assert metadata["page_size"] == 10
    
    def test_search_by_player(self, service):
        """Test search_by_player() method"""
        # First get a valid player ID
        all_players = service.get_all_players()
        if len(all_players) > 0:
            player_id = all_players[0]["playerId"]
            result = service.search_by_player(player_id)
            assert isinstance(result, dict)
            assert "playerId" in result
            assert result["playerId"] == player_id
    
    def test_search_by_country(self, service):
        """Test search_by_country() method"""
        # Get a valid country from existing data
        all_players = service.get_all_players()
        if len(all_players) > 0 and "birthCountry" in all_players[0]:
            country = all_players[0]["birthCountry"]
            result = service.search_by_country(country)
            assert isinstance(result, (list, tuple))
            # Result should contain players from that country
    
    def test_search_by_country_multiple(self, service):
        """Test search_by_country_multiple() method"""
        countries = ["USA", "Canada"]
        result = service.search_by_country_multiple(countries)
        assert isinstance(result, dict)
        assert "players" in result
        assert "countries" in result
        assert "total" in result
        assert result["countries"] == countries
    
    def test_search_by_country_multiple_empty_list(self, service):
        """Test search_by_country_multiple() with empty list"""
        result = service.search_by_country_multiple([])
        assert isinstance(result, dict)
        assert "error" in result
    
    def test_search_by_country_multiple_async(self, service):
        """Test search_by_country_multiple_async() method"""
        countries = ["USA", "Canada"]
        result = service.search_by_country_multiple_async(countries)
        assert isinstance(result, dict)
        assert "players" in result
        assert "countries" in result
        assert "total" in result
    
    def test_search_by_country_multiple_async_empty_list(self, service):
        """Test search_by_country_multiple_async() with empty list"""
        result = service.search_by_country_multiple_async([])
        assert isinstance(result, dict)
        assert "error" in result
    
    def test_search_by_country_multiple_threadpool(self, service):
        """Test search_by_country_multiple_threadpool() method"""
        countries = ["USA", "Canada"]
        result = service.search_by_country_multiple_threadpool(countries)
        assert isinstance(result, tuple)
        assert len(result) == 2
        data, status = result
        assert isinstance(data, dict)
        assert "players" in data
        assert "countries" in data
        assert status == 200
    
    def test_search_by_country_multiple_threadpool_empty_list(self, service):
        """Test search_by_country_multiple_threadpool() with empty list"""
        result = service.search_by_country_multiple_threadpool([])
        assert isinstance(result, dict)
        assert "error" in result
    
    def test_update_player_nonexistent(self, service):
        """Test update_player() with non-existent player"""
        data = {
            "nameFirst": "Updated",
            "birthYear": 1990
        }
        result, status = service.update_player("nonexistent_id_xyz", data)
        assert status == 404
        assert isinstance(result, dict)
        assert "error" in result
    
    def test_update_player_empty_body(self, service):
        """Test update_player() with empty body"""
        result, status = service.update_player("some_id", {})
        assert status == 400
        assert isinstance(result, dict)
        assert "error" in result
    
    def test_update_player_no_player_id(self, service):
        """Test update_player() with no player_id"""
        data = {"nameFirst": "Test", "birthYear": 1990}
        result, status = service.update_player("", data)
        assert status == 400
        assert isinstance(result, dict)
        assert "error" in result
    
    def test_get_bulk_empty_list(self, service):
        """Test get_bulk() with empty list"""
        result = service.get_bulk([])
        assert isinstance(result, dict)
        assert "error" in result
    
    def test_get_bulk_returns_result(self, service):
        """Test get_bulk() returns result with structure"""
        # Get some player IDs first
        all_players = service.get_all_players()
        if len(all_players) >= 2:
            player_ids = [all_players[0]["playerId"], all_players[1]["playerId"]]
            result = service.get_bulk(player_ids)
            assert isinstance(result, dict)
            assert "players" in result
            assert "total" in result
            assert "not_found" in result
    
    def test_get_bulk_async_empty_list(self, service):
        """Test get_bulk_async() with empty list"""
        result = service.get_bulk_async([])
        assert isinstance(result, dict)
        assert "error" in result
    
    def test_get_bulk_async_returns_result(self, service):
        """Test get_bulk_async() returns result with structure"""
        all_players = service.get_all_players()
        if len(all_players) >= 2:
            player_ids = [all_players[0]["playerId"], all_players[1]["playerId"]]
            result = service.get_bulk_async(player_ids)
            assert isinstance(result, dict)
            assert "players" in result
            assert "total" in result
            assert "not_found" in result
    
    def test_get_bulk_threadpool_empty_list(self, service):
        """Test get_bulk_threadpool() with empty list"""
        result = service.get_bulk_threadpool([])
        assert isinstance(result, dict)
        assert "error" in result
    
    def test_get_bulk_threadpool_returns_result(self, service):
        """Test get_bulk_threadpool() returns result with structure"""
        all_players = service.get_all_players()
        if len(all_players) >= 2:
            player_ids = [all_players[0]["playerId"], all_players[1]["playerId"]]
            result, status = service.get_bulk_threadpool(player_ids)
            assert isinstance(result, dict)
            assert "players" in result
            assert "total" in result
            assert "not_found" in result
            assert status == 200


class TestPlayerServicePagination:
    """Additional tests for pagination edge cases"""
    
    def test_pagination_invalid_page(self, service):
        """Test pagination with invalid page number"""
        result = service.get_all_players_with_pagination(page=-1, size=10)
        assert isinstance(result, dict)
        assert "error" in result
    
    def test_pagination_invalid_size(self, service):
        """Test pagination with invalid size"""
        result = service.get_all_players_with_pagination(page=1, size=-5)
        assert isinstance(result, dict)
        assert "error" in result
    
    def test_pagination_valid_parameters(self, service):
        """Test pagination with valid parameters"""
        result = service.get_all_players_with_pagination(page=1, size=5, sort_by="playerId", order="asc")
        assert isinstance(result, dict)
        assert "players" in result
        assert "metadata" in result
        assert len(result["players"]) <= 5


class TestPlayerServiceConcurrency:
    """Test concurrent operations"""
    
    def test_get_bulk_async_concurrent_operations(self, service):
        """Test get_bulk_async handles concurrent operations"""
        all_players = service.get_all_players()
        if len(all_players) >= 5:
            # Test with multiple IDs to trigger concurrent operations
            player_ids = [p["playerId"] for p in all_players[:5]]
            result = service.get_bulk_async(player_ids)
            assert "players" in result
            assert "total" in result
    
    def test_get_bulk_threadpool_concurrent_operations(self, service):
        """Test get_bulk_threadpool handles concurrent operations"""
        all_players = service.get_all_players()
        if len(all_players) >= 5:
            # Test with multiple IDs to trigger thread pool operations
            player_ids = [p["playerId"] for p in all_players[:5]]
            result, status = service.get_bulk_threadpool(player_ids)
            assert "players" in result
            assert "total" in result
            assert status == 200
