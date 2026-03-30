from functools import wraps
import logging

from flask import Flask, request, jsonify
import pandas as pd
import sqlite3
from sqlalchemy import create_engine
from player_service_RBAC import PlayerServiceRBAC
import ollama
import os

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)

def authenticate_request_api_key():
    """Extract username and role from API Key in X-API-Key header"""
    api_key = request.headers.get('X-API-Key')
    
    # Hardcoded API keys for testing
    VALID_API_KEYS = {
        'admin-api-key-12345': {'username': 'admin', 'role': 'admin'},
        'reader-api-key-67890': {'username': 'reader', 'role': 'reader'}
    }
    
    if api_key in VALID_API_KEYS:
        user_info = VALID_API_KEYS[api_key]
        logger.info(f'Authentication successful for user: {user_info["username"]}, role: {user_info["role"]}')
        return user_info['username'], user_info['role']
    
    logger.warning('Authentication attempt with invalid or missing API Key')
    return None, None

def require_auth(f):
    """
    Decorator that enforces API Key authentication on Flask route handlers.

    How it works:
      1. Wraps the target route function using @wraps to preserve its name/metadata.
      2. Before the route runs, calls authenticate_request_api_key() which reads
         the 'X-API-Key' header and validates it against a known key dictionary.
      3. If the key is missing or invalid → returns 401 Unauthorized immediately;
         the actual route function never executes.
      4. If the key is valid → injects 'username' and 'role' as keyword arguments
         into the route function, enabling per-route RBAC checks.

    Usage:
      @app.route('/some/path')
      @require_auth
      def my_route(username=None, role=None):
          ...

    Roles available: 'admin', 'reader'
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        username, role = authenticate_request_api_key()
        
        if not username:
            logger.warning(f'Unauthorized access attempt on {request.method} {request.path}')
            error_response = {"error": "Unauthorized - Invalid or missing API Key", "code": 401, "status": "UNAUTHORIZED"}
            return jsonify(error_response), 401
        
        logger.info(f'{request.method} {request.path} accessed by user: {username}')
        return f(*args, username=username, role=role, **kwargs)
    return decorated_function

# Load CSV file in pandas dataframe and create SQLite database
csv_path = os.path.join(os.path.dirname(__file__), 'Player.csv')
df = pd.read_csv(csv_path)
engine = create_engine('sqlite:///player.db', echo=True)
df.to_sql('players', con=engine, if_exists='replace', index=False)

# Get all players
"""
EXAMPLE: API Key Authentication
  curl -X GET "http://localhost:8000/rbac/v1/players" \
    -H "X-API-Key: admin-api-key-12345"

Valid API Keys:
  - Admin: admin-api-key-12345
  - Reader: reader-api-key-67890
"""
@app.route('/rbac/v1/players', methods=['GET'])
@require_auth
def get_players(username=None, role=None):
    player_service = PlayerServiceRBAC(role=role)
    result = player_service.get_all_players()
    return result

# Get all players with Pagination and sorting
@app.route('/rbac/v1/players/all', methods=['GET'])
@require_auth
def get_all_players_with_pagination_and_sorting(username=None, role=None):
    try:
        try:
            page = request.args.get('page', 1, type = int)
            size  = request.args.get('size', 20, type = int)

        except (ValueError, TypeError):
            error_response = {"error": "Pagination parameters must be integer", "code": 400, "status": "BAD_REQUEST"}
            return jsonify(error_response), 400

        sort_by = request.args.get('sort_by', 'playerId', type = str)
        order = request.args.get('order', 'asc', type = str)

        player_service = PlayerServiceRBAC(role=role)
        result = player_service.get_all_players_with_pagination(page=page, size=size, sort_by=sort_by, order=order)

        #Check if service returned any error 
        if isinstance(result, dict) and "error" in result:
            status = result.get("status", 400)
            return jsonify(result), status

        return jsonify(result), 200
    except Exception as e:
        error_response = {"error": "An Internal error occurred while processing", "code": 500, "status": "INTERNAL_ERROR"}
        return jsonify(error_response), 500

@app.route('/rbac/v1/players/<string:player_id>')
@require_auth
def query_player_id(player_id, username=None, role=None):
    player_service = PlayerServiceRBAC(role=role)
    result = player_service.search_by_player(player_id)

    if len(result) == 0:
        return jsonify({"error": "No record found with player_id={}".format(player_id)})
    else:
        return jsonify(result)
    
@app.route('/rbac/v1/players/bulk', methods=["POST"])
@require_auth
def bulk_get_players(username=None, role=None):
    data = request.get_json(silent=True)

    if not data or "player_ids" not in data:
        error_response = {"error": "Request body must include 'playerIds'", "code": 400, "status": "BAD_REQUEST"}
        return jsonify(error_response), 400
    if not isinstance(data["player_ids"], list):
        error_response = {"error": "'playerIds' must be a list", "code": 400, "status": "BAD_REQUEST"}
        return jsonify(error_response), 400

    player_service = PlayerServiceRBAC(role=role)
    result = player_service.get_bulk(data["player_ids"])

    return result, 200

@app.route('/rbac/v1/players/<player_id>', methods=["DELETE"])
@require_auth
def delete_player(player_id, username=None, role=None):
    if role != 'admin':
        logger.warning(f'Delete attempt by non-admin user: {username}')
        error_response = {"error": "Forbidden - Only admin can delete players", "code": 403, "status": "FORBIDDEN"}
        return jsonify(error_response), 403
    
    logger.info(f'Admin {username} deleting player: {player_id}')
    player_service = PlayerServiceRBAC(role=role)
    result, status = player_service.delete(player_id)
    return jsonify(result), status

@app.route('/rbac/v1/players/<player_id>', methods=["PUT"])
@require_auth
def update_player(player_id, username=None, role=None):
    if role != 'admin':
        logger.warning(f'Update attempt by non-admin user: {username}')
        error_response = {"error": "Forbidden - Only admin can update players", "code": 403, "status": "FORBIDDEN"}
        return jsonify(error_response), 403
    
    logger.info(f'Admin {username} updating player: {player_id}')
    data = request.get_json(silent=True)
    player_service = PlayerServiceRBAC(role=role)
    result, status = player_service.update_player(player_id, data)
    return jsonify(result), status

@app.route('/rbac/v1/players', methods=["POST"])
@require_auth
def add_player(username=None, role=None):
    if role != 'admin':
        logger.warning(f'Create attempt by non-admin user: {username}')
        error_response = {"error": "Forbidden - Only admin can add players", "code": 403, "status": "FORBIDDEN"}
        return jsonify(error_response), 403
    
    logger.info(f'Admin {username} creating new player')
    data = request.get_json(silent=True)
    player_service = PlayerServiceRBAC(role=role)
    result, status = player_service.add_player(data)
    return jsonify(result), status

@app.route('/rbac/v1/chat/list-models')
@require_auth
def list_models(username=None, role=None):
    return jsonify(ollama.list())

@app.route('/rbac/v1/chat', methods=['POST'])
@require_auth
def chat(username=None, role=None):
    # Process the data as needed
    response = ollama.chat(model='tinyllama', messages=[
        {
            'role': 'user',
            'content': 'Why is the sky blue?',
        },
    ])
    return jsonify(response), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8001, debug=True)
