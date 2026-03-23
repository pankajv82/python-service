import datetime
import math
import sqlite3
import uuid
from sqlalchemy import create_engine

def make_error(message, code, status):
        return {
            "error": message,
            "code": code,  
            "status": status,
            "timestamp": datetime.now(datetime.timezone.utc).isoformat()
        }

class PlayerService:
    def __init__(self):
        conn = sqlite3.connect("player.db")
        self.conn = conn
        self.cursor = conn.cursor()
        self.columns = self.get_columns()

    def get_all_players(self):

        query = "SELECT * FROM players"
        result = self.cursor.execute(query).fetchall()
        players = []
        for row in result:
            dic = self.convert_row_to_dict(row)
            players.append(dic)

        return players
   
    def get_all_players_with_pagination(self, page=1, size=20, sort_by="playerId", order="asc"):

        try:
            # Request Validation
            if not isinstance(page, int) or page < 1:
                return make_error("page must be posotive integer", "INVALID_INPUT", 400)
            
            if not isinstance(size, int) or size < 1:
                return make_error("size must be posotive integer", "INVALID_INPUT", 400)
            
            ALLOWED_SORT = {"playerId", "birthYear", "nameLast", "nameFirst"}

            if sort_by not in ALLOWED_SORT:
                sort_by = "playerId"
            
            #fix below query to get total count of records in players table
            self.cursor.execute("SELECT COUNT(*) FROM players")
            total = self.cursor.fetchone()[0]
            
            offset = (page - 1) * size

            if offset >= total and total >0:
                return {"players": [], "total": total, "page":page, "size":size}
            
            is_dec = (order.lower() == "desc")

            query = f"SELECT * FROM players ORDER BY {sort_by} {order} LIMIT ? OFFSET ?"
            result = self.cursor.execute(query, (size, offset)).fetchall()
            # players = []
            # for row in result:
            #     dic = self.convert_row_to_dict(row)
            #     players.append(dic)

            players = [self.convert_row_to_dict(row) for row in result]
            total_pages = math.ceil(total / size)

            return {
                "players": players,
                "metadata":{
                    "total": total, 
                    "current_page":page,
                    "page_size":size,
                    "total_pages":total_pages,
                    "has_next": page < total_pages,
                    "has_prev": page > 1
                }
            }
        
        except Exception as ex:
            return make_error("unexpected error occured")

    def get_bulk(self, player_ids:list):
        
        if not player_ids:
            return  make_error("player_ids cant be empty", "INVALID_PARAM", 400)
        
        placeholders = ", ".join("?" * len(player_ids))
        query = f"SELECT * FROM Players WHERE playerId IN ({placeholders})"
        result = self.cursor.execute(query, player_ids).fetchall()
        players = [self.convert_row_to_dict(row) for row in result]

        #rows = {r["playerId"]:r for r in (self.convert_row_to_dict(row) for row in self.cursor.fetchall())}
        
        found_ids = {r["playerId"] for r in players}
        not_found = [pid for pid in player_ids if pid not in found_ids]

        return {
            "players": players,
            "not_found": not_found,
            "total": len(players)
        }

    def search_by_player(self, player_id):

        query = "SELECT * FROM players WHERE playerId='{}'".format(player_id)
        result = self.cursor.execute(query).fetchall()

        for row in result:
            dic = self.convert_row_to_dict(row)
        return dic

    def search_by_country(self, birth_country):

        query = "SELECT * FROM players WHERE birthCountry='{}'".format(birth_country)
        result = self.cursor.execute(query).fetchall()

        return result


    def convert_row_to_dict(self, row):
        dic = { self.columns[i]: row[i] for i in range(len(row)) }
        return dic


    def get_columns(self):
        self.cursor.execute("PRAGMA table_info(players)")
        columns = [column[1] for column in self.cursor.fetchall()]
        return columns
    
    def add_player(self, data:dict):
        try:
            #Validation Logic 

            if not isinstance(data, dict) or not data:
                return make_error("request body can't be empty string", "INVALID_PARAM", 400), 400
            
            missing = {"birthYear"} - data.keys()

            if missing:
                return make_error(f"Missing required fields: {missing}", "MISSING_FIELDS", 400), 400
            
            pid = data["playerId"]

            # if not pid:
            #     pid = uuid.uuid4()

            self.cursor.execute("SELECT 1 from players WHERE playerId=?", (pid,))
            if self.cursor.fetchone():
                return make_error(f"player with {pid} already exist", "COMFLICT", 409), 409

            valid_keys = [k for k in data if k in self.columns]
            cols_str = ", ".join(valid_keys)
            placeholders = ", ".join("?" for _ in valid_keys)

            values = [data[k] for k in valid_keys]

            self.cursor.execute(
                f"INSTERT INTO players ({cols_str} VALUES ({placeholders}))", values
            )
            self.conn.commit()

            return {"message": f"player '{pid}' added"}, 201

        except Exception as e:
            return make_error("Server Error", "INTERNAL_ERROR", 500)

    def update_player(self, player_id:str, data:dict):
        try:
            #Validation Logic 

            if not player_id:
                return make_error("player_id must be non-empty", "INVALID_PARAM", 400), 400
            if not isinstance(data, dict) or not data:
                return make_error("request body can't be empty string", "INVALID_PARAM", 400), 400
            
            missing = {"birthYear"} - data.keys()

            if missing:
                return make_error(f"Missing required fields: {missing}", "MISSING_FIELDS", 400), 400
            
            pid = player_id

            # if not pid:
            #     pid = uuid.uuid4()

            self.cursor.execute("SELECT 1 from players WHERE playerId=?", (pid,))
            if not self.cursor.fetchone():
                return make_error(f"player with {pid} not found", "NOT_FOUND", 404), 404

            valid_keys = [k for k in data if k in self.columns]
            cols_str = ", ".join(valid_keys)
            placeholders = ", ".join("?" for _ in valid_keys)

            values = [data[k] for k in valid_keys]

            #set_clause = 

            self.cursor.execute(
                f"UPDATE players SET {set_clause} WHERE playerId = ?", values
            )
            self.conn.commit()

            return {"message": f"player '{pid}' added"}, 201

        except Exception as e:
            return make_error("Server Error", "INTERNAL_ERROR", 500)


    def delete(self, player_id: str):
        try:
            if not player_id or not isinstance(player_id, str):
                return make_error("player_id must be non empty string", "INVALID_PARAM",400), 400

            self.cursor.execute("SELECT 1 from players WHERE playerId = ?", (player_id))

            if not self.cursor.fetchone():
                return make_error("player not found", "NOT_FOUND",404), 404
            
            self.cursor.execute("DELETE from players WHERE playerId = ?", (player_id))
            self.conn.commit()

            return {"message": f"Player '{player_id}' deleted"}, 200
        
        except Exception as e:
            self.conn.rollback()
            return make_error("failed to delete", "INTERNAL_ERROR",500)