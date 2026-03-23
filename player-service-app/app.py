import datetime

from flask import Flask, request, jsonify
import pandas as pd
import sqlite3
from sqlalchemy import create_engine
from player_service import PlayerService
import ollama
import os

app = Flask(__name__)

# Load CSV file in pandas dataframe and create SQLite database
csv_path = os.path.join(os.path.dirname(__file__), 'Player.csv')
df = pd.read_csv(csv_path)
engine = create_engine('sqlite:///player.db', echo=True)
df.to_sql('players', con=engine, if_exists='replace', index=False)

# Get all players
@app.route('/v1/players', methods=['GET'])
def get_players():
    player_service = PlayerService()
    result = player_service.get_all_players()
    return result

def make_error(message, code, status):
    return {
        "error": message,
        "code": code,  
        "status": status,
        "timestamp": datetime.now(datetime.timezone.utc).isoformat()
    }

# Get all players with Pagination and sorting
@app.route('/v1/players/all', methods=['GET'])
def get_all_players_with_pagination_and_sorting():
    try:
        try:
            page = request.args.get('page', 1, type = int)
            size  = request.args.get('size', 20, type = int)

        except (ValueError, TypeError):
            make_error("Pagination parameters must be integer", 400, 'BAD_REQUEST')

        sort_by = request.args.get('sort_by', 'playerId', type = str)
        order = request.args.get('order', 'asc', type = str)

        player_service = PlayerService()
        result = player_service.get_all_players_with_pagination(page=page, size=size, sort_by=sort_by, order=order)

        #Check if service returned any error 
        if isinstance(result, dict) and "error" in result:
            status = result.get("status", 400)
            return jsonify(result), status

        return jsonify(result), 200
    except Exception as e:
        return make_error("An Internal error occurred while processing", 500)

@app.route('/v1/players/<string:player_id>')
def query_player_id(player_id):
    player_service = PlayerService()
    result = player_service.search_by_player(player_id)

    if len(result) == 0:
        return jsonify({"error": "No record found with player_id={}".format(player_id)})
    else:
        return jsonify(result)
    
@app.route('/v1/players/bulk', methods=["POST"])
def bulk_get_players():
    data = request.get_json(silent=True)

    if not data or "player_ids" not in data:
        return jsonify(make_error("Request body must include 'playerIds'", 400, "BAD_REQUEST")), 400
    if not isinstance(data["player_ids"], list):
        return jsonify(make_error("'playerIds' must be a list", 400, "BAD_REQUEST")), 400

    player_service = PlayerService()
    result = player_service.get_bulk(data["player_ids"])

    return result, 200

@app.route('/v1/players/<player_id>', methods=["DELETE"])
def delete_player(player_id):
    player_service = PlayerService()
    result, status = player_service.delete(player_id)
    return jsonify(result), status

@app.route('/v1/players/<player_id>', methods=["PUT"])
def update_player(player_id):
    data = request.get_json(slient=True)
    player_service = PlayerService()
    result, status = player_service.update_player(player_id, data)
    return jsonify(result), status


@app.route('/v1/players', methods=["POST"])
def add_player():
    data = request.get_json(slient=True)
    player_service = PlayerService()
    result, status = player_service.add_player(data)
    return jsonify(result), status




@app.route('/v1/chat/list-models')
def list_models():
    return jsonify(ollama.list())

@app.route('/v1/chat', methods=['POST'])
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
