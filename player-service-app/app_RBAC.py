import datetime
from functools import wraps

from flask import Flask, request, jsonify
import pandas as pd
import sqlite3
from sqlalchemy import create_engine
from player_service_RBAC import PlayerServiceRBAC
import ollama
import os

# Load credentials from environment variables (or use defaults)
ADMIN_USER = os.getenv('ADMIN_USER', 'admin')
ADMIN_PASSWORD = os.getenv('ADMIN_PASSWORD', 'admin_pass')
READER_USER = os.getenv('READER_USER', 'reader')
READER_PASSWORD = os.getenv('READER_PASSWORD', 'reader_pass')

CREDENTIALS = {
    ADMIN_USER: {'password': ADMIN_PASSWORD, 'role': 'admin'},
    READER_USER: {'password': READER_PASSWORD, 'role': 'reader'}
}

app = Flask(__name__)

def authenticate_request():
    """Extract username and role from request headers"""
    username = request.headers.get('X-Username')
    password = request.headers.get('X-Password')
    
    if not username or not password:
        return None, None
    
    if username not in CREDENTIALS or CREDENTIALS[username]['password'] != password:
        return None, None
    
    role = CREDENTIALS[username]['role']
    return username, role

def require_auth(f):
    """Decorator to require authentication"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        username, role = authenticate_request()
        
        if not username:
            error_response = {"error": "Unauthorized - Invalid credentials", "code": 401, "status": "UNAUTHORIZED"}
            return jsonify(error_response), 401
        
        return f(*args, username=username, role=role, **kwargs)
    return decorated_function

# Load CSV file in pandas dataframe and create SQLite database
csv_path = os.path.join(os.path.dirname(__file__), 'Player.csv')
df = pd.read_csv(csv_path)
engine = create_engine('sqlite:///player.db', echo=True)
df.to_sql('players', con=engine, if_exists='replace', index=False)

# Get all players
"""
SAMPLE REQUEST TO TEST get_players:

1. CURL REQUEST - Using Admin Role:
   curl -X GET "http://localhost:8000/v1/players" \
     -H "X-Username: admin" \
     -H "X-Password: admin_pass"
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
        error_response = {"error": "Forbidden - Only admin can delete players", "code": 403, "status": "FORBIDDEN"}
        return jsonify(error_response), 403
    
    player_service = PlayerServiceRBAC(role=role)
    result, status = player_service.delete(player_id)
    return jsonify(result), status

@app.route('/rbac/v1/players/<player_id>', methods=["PUT"])
@require_auth
def update_player(player_id, username=None, role=None):
    if role != 'admin':
        error_response = {"error": "Forbidden - Only admin can update players", "code": 403, "status": "FORBIDDEN"}
        return jsonify(error_response), 403
    
    data = request.get_json(silent=True)
    player_service = PlayerServiceRBAC(role=role)
    result, status = player_service.update_player(player_id, data)
    return jsonify(result), status

@app.route('/rbac/v1/players', methods=["POST"])
@require_auth
def add_player(username=None, role=None):
    if role != 'admin':
        error_response = {"error": "Forbidden - Only admin can add players", "code": 403, "status": "FORBIDDEN"}
        return jsonify(error_response), 403
    
    data = request.get_json(silent=True)
    player_service = PlayerServiceRBAC(role=role)
    result, status = player_service.add_player(data)
    return jsonify(result), status




@app.route('/rbac/v1/chat/list-models')
def list_models():
    return jsonify(ollama.list())

@app.route('/rbac/v1/chat', methods=['POST'])
def chat():
    # Process the data as needed
    response = ollama.chat(model='tinyllama', messages=[
        {
            'role': 'user',
            'content': 'Why is the sky blue?',
        },
    ])
    return jsonify(response), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000, debug=True)
