import unittest
import json
from unittest.mock import patch, MagicMock
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import app
from player_service import PlayerService


class TestAIScoutQuery(unittest.TestCase):
    """Test cases for /v1/scout/query endpoint"""
    
    def setUp(self):
        self.client = app.test_client()
        self.endpoint = '/v1/scout/query'
    
    def test_scout_query_missing_query_field(self):
        """Test scout query with missing query field"""
        response = self.client.post(self.endpoint, json={})
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertIn("error", data)
    
    def test_scout_query_empty_query(self):
        """Test scout query with empty query string"""
        response = self.client.post(self.endpoint, json={"query": ""})
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertIn("error", data)
    
    @patch('app.PlayerService.get_all_players')
    @patch('app.ollama.chat')
    def test_scout_query_success(self, mock_ollama, mock_get_players):
        """Test successful scout query"""
        # Mock player data
        mock_get_players.return_value = [
            {'nameFirst': 'John', 'nameLast': 'Doe', 'playerId': 'john001'},
            {'nameFirst': 'Jane', 'nameLast': 'Smith', 'playerId': 'jane001'}
        ]
        
        # Mock ollama response
        mock_ollama.return_value = {
            'message': {'content': json.dumps({"answer": "Test answer", "data_used": ["John Doe"], "confidence": "high"})}
        }
        
        response = self.client.post(self.endpoint, json={"query": "Who is the best player?"})
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data["status"], "success")
        self.assertIn("answer", data)
        self.assertIn("query", data)
    
    @patch('app.PlayerService.get_all_players')
    def test_scout_query_no_player_data(self, mock_get_players):
        """Test scout query when no player data available"""
        mock_get_players.return_value = []
        
        response = self.client.post(self.endpoint, json={"query": "Who is the best player?"})
        self.assertEqual(response.status_code, 404)
        data = json.loads(response.data)
        self.assertIn("error", data)


class TestAICompare(unittest.TestCase):
    """Test cases for /v1/ai/compare endpoint"""
    
    def setUp(self):
        self.client = app.test_client()
        self.endpoint = '/v1/ai/compare'
    
    def test_compare_missing_parameters(self):
        """Test compare without required parameters"""
        response = self.client.get(self.endpoint)
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertIn("error", data)
    
    def test_compare_same_player_ids(self):
        """Test compare when both player IDs are the same"""
        response = self.client.get(f"{self.endpoint}?player_id_1=john001&player_id_2=john001")
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertIn("error", data)
    
    def test_compare_invalid_player_id_length(self):
        """Test compare with player ID exceeding max length"""
        long_id = "x" * 21
        response = self.client.get(f"{self.endpoint}?player_id_1={long_id}&player_id_2=jane001")
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertIn("error", data)
    
    @patch('app.PlayerService.search_by_player')
    def test_compare_player_not_found(self, mock_search):
        """Test compare when first player not found"""
        mock_search.return_value = []
        
        response = self.client.get(f"{self.endpoint}?player_id_1=invalid&player_id_2=jane001")
        self.assertEqual(response.status_code, 404)
        data = json.loads(response.data)
        self.assertIn("error", data)
    
    @patch('app.PlayerService.search_by_player')
    @patch('app.ollama.chat')
    def test_compare_success(self, mock_ollama, mock_search):
        """Test successful player comparison"""
        # Mock player data
        mock_search.side_effect = [
            [{'nameFirst': 'John', 'nameLast': 'Doe', 'birthCountry': 'USA', 'birthYear': '1990', 
              'G': 100, 'AB': 400, 'H': 120, 'HR': 25, 'BA': 0.300, 'OBP': 0.350, 'SLG': 0.500}],
            [{'nameFirst': 'Jane', 'nameLast': 'Smith', 'birthCountry': 'USA', 'birthYear': '1991', 
              'G': 110, 'AB': 450, 'H': 140, 'HR': 30, 'BA': 0.311, 'OBP': 0.360, 'SLG': 0.520}]
        ]
        
        # Mock ollama response
        mock_ollama.return_value = {
            'message': {'content': json.dumps({
                "comparison_summary": "Jane is better",
                "player_1_strengths": [],
                "player_2_strengths": ["Higher BA", "More HR"],
                "winner": "jane001",
                "key_metrics": ["BA", "HR"]
            })}
        }
        
        response = self.client.get(f"{self.endpoint}?player_id_1=john001&player_id_2=jane001")
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data["status"], "success")
        self.assertIn("comparison", data)
        self.assertIn("player_1", data)
        self.assertIn("player_2", data)


class TestAIBio(unittest.TestCase):
    """Test cases for /v1/ai/bio/<player_id> endpoint"""
    
    def setUp(self):
        self.client = app.test_client()
        self.endpoint = '/v1/ai/bio'
    
    def test_bio_empty_player_id(self):
        """Test bio with empty player ID"""
        response = self.client.get(f"{self.endpoint}/")
        self.assertIn(response.status_code, [400, 404])
    
    def test_bio_invalid_player_id_format(self):
        """Test bio with invalid player ID format"""
        response = self.client.get(f"{self.endpoint}/{'x' * 21}")
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertIn("error", data)
    
    @patch('app.PlayerService.search_by_player')
    def test_bio_player_not_found(self, mock_search):
        """Test bio when player not found"""
        mock_search.return_value = []
        
        response = self.client.get(f"{self.endpoint}/invalid")
        self.assertEqual(response.status_code, 404)
        data = json.loads(response.data)
        self.assertIn("error", data)
    
    @patch('app.PlayerService.search_by_player')
    @patch('app.ollama.chat')
    def test_bio_success(self, mock_ollama, mock_search):
        """Test successful biography generation"""
        mock_search.return_value = [{
            'nameFirst': 'John', 'nameLast': 'Doe', 'playerId': 'john001',
            'birthYear': '1990', 'birthCountry': 'USA', 'deathYear': None,
            'debut': '2012', 'finalYear': '2020',
            'G': 150, 'AB': 500, 'H': 150, 'HR': 30, 'RBI': 90,
            'BA': 0.300, 'OBP': 0.350, 'SLG': 0.500
        }]
        
        mock_ollama.return_value = {
            'message': {'content': json.dumps({
                "biography": "John Doe was a great player...",
                "career_span": "2012-2020",
                "notable_stats": {"HR": 30, "RBI": 90},
                "era": "2010s"
            })}
        }
        
        response = self.client.get(f"{self.endpoint}/john001")
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data["status"], "success")
        self.assertIn("biography", data)
        self.assertIn("player_id", data)
        self.assertIn("player_name", data)


class TestTeamGenerate(unittest.TestCase):
    """Test cases for /team/generate endpoint"""
    
    def setUp(self):
        self.client = app.test_client()
        self.endpoint = '/team/generate'
    
    def test_team_generate_missing_playerId(self):
        """Test team generate without playerId"""
        response = self.client.post(self.endpoint, json={})
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertIn("error", data)
    
    def test_team_generate_empty_playerId(self):
        """Test team generate with empty playerId"""
        response = self.client.post(self.endpoint, json={"playerId": ""})
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertIn("error", data)
    
    def test_team_generate_invalid_team_size(self):
        """Test team generate with invalid team size"""
        response = self.client.post(self.endpoint, json={
            "playerId": "john001",
            "teamSize": 25  # Exceeds max of 20
        })
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertIn("error", data)
    
    @patch('app.PlayerService.search_by_player')
    def test_team_generate_player_not_found(self, mock_search):
        """Test team generate when seed player not found"""
        mock_search.return_value = []
        
        response = self.client.post(self.endpoint, json={
            "playerId": "invalid",
            "teamSize": 9
        })
        self.assertEqual(response.status_code, 404)
        data = json.loads(response.data)
        self.assertIn("error", data)
    
    @patch('app.requests.post')
    @patch('app.PlayerService.search_by_player')
    def test_team_generate_model_service_unavailable(self, mock_search, mock_post):
        """Test team generate when model service unavailable"""
        mock_search.return_value = [{
            'nameFirst': 'John', 'nameLast': 'Doe', 'playerId': 'john001'
        }]
        
        # Simulate connection error
        import requests
        mock_post.side_effect = requests.exceptions.ConnectionError()
        
        response = self.client.post(self.endpoint, json={
            "playerId": "john001",
            "teamSize": 9
        })
        self.assertEqual(response.status_code, 503)
        data = json.loads(response.data)
        self.assertIn("error", data)


class TestTeamFeedback(unittest.TestCase):
    """Test cases for /team/feedback endpoint"""
    
    def setUp(self):
        self.client = app.test_client()
        self.endpoint = '/team/feedback'
    
    def test_team_feedback_missing_fields(self):
        """Test team feedback with missing fields"""
        response = self.client.post(self.endpoint, json={})
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertIn("error", data)
    
    def test_team_feedback_invalid_rating(self):
        """Test team feedback with invalid rating"""
        response = self.client.post(self.endpoint, json={
            "playerId": "john001",
            "teamMembers": ["jane001"],
            "feedback": "Good team",
            "rating": 6  # Invalid, should be 1-5
        })
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertIn("error", data)
    
    @patch('app.PlayerService.search_by_player')
    def test_team_feedback_player_not_found(self, mock_search):
        """Test team feedback when player not found"""
        mock_search.return_value = []
        
        response = self.client.post(self.endpoint, json={
            "playerId": "invalid",
            "teamMembers": ["jane001"],
            "feedback": "Good team",
            "rating": 4
        })
        self.assertEqual(response.status_code, 404)
        data = json.loads(response.data)
        self.assertIn("error", data)
    
    @patch('app.PlayerService.search_by_player')
    def test_team_feedback_success(self, mock_search):
        """Test successful team feedback submission"""
        mock_search.return_value = [{
            'nameFirst': 'John', 'nameLast': 'Doe', 'playerId': 'john001'
        }]
        
        response = self.client.post(self.endpoint, json={
            "playerId": "john001",
            "teamMembers": ["jane001", "bob001"],
            "feedback": "Great team composition",
            "rating": 5
        })
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data)
        self.assertIn("message", data)
        self.assertEqual(data["rating"], 5)
        self.assertIn("feedback_status", data)


class TestLLMGenerate(unittest.TestCase):
    """Test cases for /llm/generate endpoint"""
    
    def setUp(self):
        self.client = app.test_client()
        self.endpoint = '/llm/generate'
    
    def test_llm_generate_missing_user_prompt(self):
        """Test LLM generate without user_prompt"""
        response = self.client.post(self.endpoint, json={})
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertIn("error", data)
    
    def test_llm_generate_missing_system_prompt(self):
        """Test LLM generate without system_prompt"""
        response = self.client.post(self.endpoint, json={
            "user_prompt": "Tell me about baseball"
        })
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertIn("error", data)
    
    def test_llm_generate_empty_prompts(self):
        """Test LLM generate with empty prompts"""
        response = self.client.post(self.endpoint, json={
            "user_prompt": "",
            "system_prompt": ""
        })
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertIn("error", data)
    
    @patch('app.requests.post')
    def test_llm_generate_model_service_unavailable(self, mock_post):
        """Test LLM generate when model service unavailable"""
        import requests
        mock_post.side_effect = requests.exceptions.ConnectionError()
        
        response = self.client.post(self.endpoint, json={
            "system_prompt": "You are a baseball expert",
            "user_prompt": "Tell me about baseball"
        })
        self.assertEqual(response.status_code, 503)
        data = json.loads(response.data)
        self.assertIn("error", data)
    
    @patch('app.requests.post')
    def test_llm_generate_success(self, mock_post):
        """Test successful LLM generation"""
        mock_post.return_value = MagicMock(
            status_code=200,
            json=lambda: {"response": "Baseball is a great sport"}
        )
        
        response = self.client.post(self.endpoint, json={
            "system_prompt": "You are a baseball expert",
            "user_prompt": "Tell me about baseball"
        })
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data["status"], "success")
        self.assertIn("response", data)
        self.assertIn("user_prompt", data)


class TestChat(unittest.TestCase):
    """Test cases for /v1/chat endpoint"""
    
    def setUp(self):
        self.client = app.test_client()
        self.endpoint = '/v1/chat'
    
    @patch('app.ollama.chat')
    def test_chat_success(self, mock_ollama):
        """Test successful chat"""
        mock_ollama.return_value = {
            'message': {'content': json.dumps({
                "response": "The sky appears blue due to Rayleigh scattering",
                "topic": "science"
            })}
        }
        
        response = self.client.post(self.endpoint)
        self.assertEqual(response.status_code, 200)
        # Response from ollama will be returned directly


class TestChatListModels(unittest.TestCase):
    """Test cases for /v1/chat/list-models endpoint"""
    
    def setUp(self):
        self.client = app.test_client()
        self.endpoint = '/v1/chat/list-models'
    
    @patch('app.ollama.list')
    def test_list_models(self, mock_list):
        """Test listing available models"""
        mock_list.return_value = {'models': [{'name': 'tinyllama'}]}
        
        response = self.client.get(self.endpoint)
        self.assertEqual(response.status_code, 200)


if __name__ == '__main__':
    unittest.main()
