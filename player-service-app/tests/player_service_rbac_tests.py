import pytest
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from player_service_RBAC import PlayerServiceRBAC
import sqlite3


@pytest.fixture
def admin_service():
    """Create a PlayerServiceRBAC instance with admin role"""
    return PlayerServiceRBAC(role='admin')


@pytest.fixture
def reader_service():
    """Create a PlayerServiceRBAC instance with reader role"""
    return PlayerServiceRBAC(role='reader')


class TestPlayerServiceRBACInit:
    """Test initialization and role assignment"""
    
    def test_init_with_admin_role(self):
        """Test initialization with admin role"""
        service = PlayerServiceRBAC(role='admin')
        assert service.role == 'admin'
        assert service.conn is not None
        assert service.cursor is not None
        assert len(service.columns) > 0
    
    def test_init_with_reader_role(self):
        """Test initialization with reader role"""
        service = PlayerServiceRBAC(role='reader')
        assert service.role == 'reader'
        assert service.conn is not None
    
    def test_init_default_role(self):
        """Test initialization with default role (reader)"""
        service = PlayerServiceRBAC()
        assert service.role == 'reader'


class TestMaskSensitiveFields:
    """Test field masking based on roles"""
    
    def test_admin_sees_all_fields(self, admin_service):
        """Test that admin role sees all fields"""
        player_dict = {
            "playerId": "001",
            "nameFirst": "John",
            "nameLast": "Doe",
            "birthYear": 1990,
            "birthCountry": "USA"
        }
        result = admin_service.mask_sensitive_fields(player_dict)
        assert result == player_dict
        assert "playerId" in result
        assert "birthCountry" in result
    
    def test_reader_sees_only_public_fields(self, reader_service):
        """Test that reader role only sees public fields"""
        player_dict = {
            "playerId": "001",
            "nameFirst": "John",
            "nameLast": "Doe",
            "birthYear": 1990,
            "birthCountry": "USA"
        }
        result = reader_service.mask_sensitive_fields(player_dict)
        assert "playerId" in result
        assert "nameFirst" in result
        assert "nameLast" in result
        assert "birthYear" not in result
        assert "birthCountry" not in result
        assert set(result.keys()) == {'playerId', 'nameFirst', 'nameLast'}
    
    def test_mask_non_dict_returns_as_is(self, reader_service):
        """Test masking non-dict values returns them as-is"""
        result = reader_service.mask_sensitive_fields("not_a_dict")
        assert result == "not_a_dict"
        
        result = reader_service.mask_sensitive_fields(None)
        assert result is None


class TestGetColumns:
    """Test get_columns method"""
    
    def test_get_columns_returns_list(self, admin_service):
        """Test get_columns returns a list"""
        columns = admin_service.get_columns()
        assert isinstance(columns, list)
        assert len(columns) > 0
    
    def test_get_columns_contains_expected_columns(self, admin_service):
        """Test that columns contain expected field names"""
        columns = admin_service.get_columns()
        assert "playerId" in columns
        assert "nameFirst" in columns
        assert "nameLast" in columns


class TestConvertRowToDict:
    """Test convert_row_to_dict method"""
    
    def test_convert_row_to_dict(self, admin_service):
        """Test converting a database row to dictionary"""
        columns = admin_service.get_columns()
        sample_row = tuple([f"value_{i}" for i in range(len(columns))])
        
        result = admin_service.convert_row_to_dict(sample_row)
        assert isinstance(result, dict)
        assert len(result) == len(columns)
        assert all(col in result for col in columns)


class TestGetAllPlayers:
    """Test get_all_players method"""
    
    def test_admin_get_all_players(self, admin_service):
        """Test admin getting all players"""
        result = admin_service.get_all_players()
        assert isinstance(result, list)
        assert len(result) > 0
        player = result[0]
        assert isinstance(player, dict)
        assert "playerId" in player
    
    def test_reader_get_all_players_masked(self, reader_service):
        """Test reader getting all players with masked fields"""
        result = reader_service.get_all_players()
        assert isinstance(result, list)
        assert len(result) > 0
        player = result[0]
        # Reader should only see public fields
        assert set(player.keys()) == {'playerId', 'nameFirst', 'nameLast'}


class TestGetAllPlayersWithPagination:
    """Test get_all_players_with_pagination method"""
    
    def test_pagination_with_valid_parameters(self, admin_service):
        """Test pagination with valid parameters"""
        result = admin_service.get_all_players_with_pagination(page=1, size=10)
        assert isinstance(result, dict)
        assert "players" in result
        assert "metadata" in result
        metadata = result["metadata"]
        assert metadata["current_page"] == 1
        assert metadata["page_size"] == 10
    
    def test_pagination_invalid_page(self, admin_service):
        """Test pagination with invalid page"""
        result = admin_service.get_all_players_with_pagination(page=-1, size=10)
        assert isinstance(result, dict)
        assert "error" in result
    
    def test_pagination_invalid_size(self, admin_service):
        """Test pagination with invalid size"""
        result = admin_service.get_all_players_with_pagination(page=1, size=0)
        assert isinstance(result, dict)
        assert "error" in result
    
    def test_pagination_reader_role_masking(self, reader_service):
        """Test that pagination respects role-based masking"""
        result = reader_service.get_all_players_with_pagination(page=1, size=5)
        if "players" in result and len(result["players"]) > 0:
            player = result["players"][0]
            assert set(player.keys()) == {'playerId', 'nameFirst', 'nameLast'}


class TestSearchByPlayer:
    """Test search_by_player method"""
    
    def test_admin_search_by_player(self, admin_service):
        """Test admin searching for a player"""
        all_players = admin_service.get_all_players()
        if len(all_players) > 0:
            player_id = all_players[0]["playerId"]
            result = admin_service.search_by_player(player_id)
            assert isinstance(result, dict)
            assert "playerId" in result
            assert result["playerId"] == player_id
    
    def test_reader_search_by_player_masked(self, reader_service):
        """Test reader searching for a player with masked fields"""
        all_players = reader_service.get_all_players()
        if len(all_players) > 0:
            player_id = all_players[0]["playerId"]
            result = reader_service.search_by_player(player_id)
            # Reader should only see public fields
            assert set(result.keys()) == {'playerId', 'nameFirst', 'nameLast'}


class TestSearchByCountry:
    """Test search_by_country method"""
    
    def test_search_by_country(self, admin_service):
        """Test searching players by country"""
        all_players = admin_service.get_all_players()
        if len(all_players) > 0 and "birthCountry" in all_players[0]:
            country = all_players[0]["birthCountry"]
            result = admin_service.search_by_country(country)
            assert isinstance(result, (list, tuple))


class TestSearchByCountryMultiple:
    """Test search_by_country_multiple method"""
    
    def test_search_multiple_countries(self, admin_service):
        """Test searching multiple countries"""
        countries = ["USA", "Canada"]
        result = admin_service.search_by_country_multiple(countries)
        assert isinstance(result, dict)
        assert "players" in result
        assert "countries" in result
        assert "total" in result
    
    def test_search_multiple_empty_list(self, admin_service):
        """Test searching with empty country list"""
        result = admin_service.search_by_country_multiple([])
        assert isinstance(result, dict)
        assert "error" in result
    
    def test_search_multiple_reader_masking(self, reader_service):
        """Test that multi-country search respects role masking"""
        countries = ["USA"]
        result = reader_service.search_by_country_multiple(countries)
        if "players" in result and len(result["players"]) > 0:
            player = result["players"][0]
            assert set(player.keys()) == {'playerId', 'nameFirst', 'nameLast'}


class TestSearchByCountryMultipleAsync:
    """Test search_by_country_multiple_async method"""
    
    def test_search_multiple_async(self, admin_service):
        """Test async searching multiple countries"""
        countries = ["USA", "Canada"]
        result = admin_service.search_by_country_multiple_async(countries)
        assert isinstance(result, dict)
        assert "players" in result
        assert "countries" in result
    
    def test_search_multiple_async_empty_list(self, admin_service):
        """Test async search with empty list"""
        result = admin_service.search_by_country_multiple_async([])
        assert isinstance(result, dict)
        assert "error" in result
    
    def test_search_multiple_async_reader_masking(self, reader_service):
        """Test async search respects reader masking"""
        countries = ["USA"]
        result = reader_service.search_by_country_multiple_async(countries)
        if "players" in result and len(result["players"]) > 0:
            player = result["players"][0]
            assert set(player.keys()) == {'playerId', 'nameFirst', 'nameLast'}


class TestSearchByCountryMultipleThreadpool:
    """Test search_by_country_multiple_threadpool method"""
    
    def test_search_multiple_threadpool(self, admin_service):
        """Test threadpool searching multiple countries"""
        countries = ["USA", "Canada"]
        result, status = admin_service.search_by_country_multiple_threadpool(countries)
        assert isinstance(result, dict)
        assert "players" in result
        assert status == 200
    
    def test_search_multiple_threadpool_empty_list(self, admin_service):
        """Test threadpool search with empty list"""
        result = admin_service.search_by_country_multiple_threadpool([])
        assert isinstance(result, dict)
        assert "error" in result
    
    def test_search_multiple_threadpool_reader_masking(self, reader_service):
        """Test threadpool search respects reader masking"""
        countries = ["USA"]
        result, status = reader_service.search_by_country_multiple_threadpool(countries)
        if "players" in result and len(result["players"]) > 0:
            player = result["players"][0]
            assert set(player.keys()) == {'playerId', 'nameFirst', 'nameLast'}


class TestUpdatePlayer:
    """Test update_player method"""
    
    def test_update_player_nonexistent(self, admin_service):
        """Test updating non-existent player"""
        data = {"nameFirst": "Updated", "birthYear": 1990}
        result, status = admin_service.update_player("nonexistent_id_xyz", data)
        assert status == 404
        assert "error" in result
    
    def test_update_player_empty_body(self, admin_service):
        """Test updating player with empty body"""
        result, status = admin_service.update_player("some_id", {})
        assert status == 400
        assert "error" in result
    
    def test_update_player_no_id(self, admin_service):
        """Test updating with no player ID"""
        data = {"nameFirst": "Test", "birthYear": 1990}
        result, status = admin_service.update_player("", data)
        assert status == 400
        assert "error" in result


class TestGetBulk:
    """Test get_bulk method"""
    
    def test_get_bulk_empty_list(self, admin_service):
        """Test bulk get with empty list"""
        result = admin_service.get_bulk([])
        assert isinstance(result, dict)
        assert "error" in result
    
    def test_get_bulk_returns_result(self, admin_service):
        """Test bulk get returns proper structure"""
        all_players = admin_service.get_all_players()
        if len(all_players) >= 2:
            player_ids = [all_players[0]["playerId"], all_players[1]["playerId"]]
            result = admin_service.get_bulk(player_ids)
            assert isinstance(result, dict)
            assert "players" in result
            assert "total" in result
            assert "not_found" in result
    
    def test_get_bulk_reader_masking(self, reader_service):
        """Test bulk get respects reader masking"""
        all_players = reader_service.get_all_players()
        if len(all_players) >= 2:
            player_ids = [all_players[0]["playerId"], all_players[1]["playerId"]]
            result = reader_service.get_bulk(player_ids)
            if len(result.get("players", [])) > 0:
                player = result["players"][0]
                assert set(player.keys()) == {'playerId', 'nameFirst', 'nameLast'}


class TestGetBulkAsync:
    """Test get_bulk_async method"""
    
    def test_get_bulk_async_empty_list(self, admin_service):
        """Test async bulk get with empty list"""
        result = admin_service.get_bulk_async([])
        assert isinstance(result, dict)
        assert "error" in result
    
    def test_get_bulk_async_returns_result(self, admin_service):
        """Test async bulk get returns proper structure"""
        all_players = admin_service.get_all_players()
        if len(all_players) >= 2:
            player_ids = [all_players[0]["playerId"], all_players[1]["playerId"]]
            result = admin_service.get_bulk_async(player_ids)
            assert isinstance(result, dict)
            assert "players" in result
            assert "total" in result
            assert "not_found" in result
    
    def test_get_bulk_async_reader_masking(self, reader_service):
        """Test async bulk get respects reader masking"""
        all_players = reader_service.get_all_players()
        if len(all_players) >= 2:
            player_ids = [all_players[0]["playerId"], all_players[1]["playerId"]]
            result = reader_service.get_bulk_async(player_ids)
            if len(result.get("players", [])) > 0:
                player = result["players"][0]
                assert set(player.keys()) == {'playerId', 'nameFirst', 'nameLast'}


class TestGetBulkThreadpool:
    """Test get_bulk_threadpool method"""
    
    def test_get_bulk_threadpool_empty_list(self, admin_service):
        """Test threadpool bulk get with empty list"""
        result = admin_service.get_bulk_threadpool([])
        assert isinstance(result, dict)
        assert "error" in result
    
    def test_get_bulk_threadpool_returns_result(self, admin_service):
        """Test threadpool bulk get returns proper structure"""
        all_players = admin_service.get_all_players()
        if len(all_players) >= 2:
            player_ids = [all_players[0]["playerId"], all_players[1]["playerId"]]
            result, status = admin_service.get_bulk_threadpool(player_ids)
            assert isinstance(result, dict)
            assert "players" in result
            assert "total" in result
            assert "not_found" in result
            assert status == 200
    
    def test_get_bulk_threadpool_reader_masking(self, reader_service):
        """Test threadpool bulk get respects reader masking"""
        all_players = reader_service.get_all_players()
        if len(all_players) >= 2:
            player_ids = [all_players[0]["playerId"], all_players[1]["playerId"]]
            result, status = reader_service.get_bulk_threadpool(player_ids)
            if len(result.get("players", [])) > 0:
                player = result["players"][0]
                assert set(player.keys()) == {'playerId', 'nameFirst', 'nameLast'}


class TestRoleBasedFieldMasking:
    """Comprehensive tests for role-based field masking"""
    
    def test_admin_role_full_access(self, admin_service):
        """Test that admin role has full access to all fields"""
        all_players = admin_service.get_all_players()
        if len(all_players) > 0:
            player = all_players[0]
            # Admin should see all available fields
            assert "playerId" in player
            assert "nameFirst" in player
            assert "nameLast" in player
    
    def test_reader_role_restricted_fields(self, reader_service):
        """Test that reader role can only see restricted fields"""
        all_players = reader_service.get_all_players()
        if len(all_players) > 0:
            player = all_players[0]
            # Reader should only see public fields
            allowed_fields = {'playerId', 'nameFirst', 'nameLast'}
            assert set(player.keys()) == allowed_fields
    
    def test_field_masking_consistency_across_methods(self, admin_service, reader_service):
        """Test that field masking is consistent across all methods"""
        # Get a player as admin
        admin_players = admin_service.get_all_players()
        if len(admin_players) > 0:
            admin_player = admin_players[0]
            player_id = admin_player["playerId"]
            
            # Get same player as reader
            reader_players = reader_service.get_all_players()
            reader_player = next((p for p in reader_players if p["playerId"] == player_id), None)
            
            if reader_player:
                # Reader player should have fewer fields
                assert len(reader_player.keys()) < len(admin_player.keys())
                # All reader fields should be in admin fields
                assert set(reader_player.keys()).issubset(set(admin_player.keys()))
