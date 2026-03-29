from datetime import datetime, timezone
import math
import sqlite3
import uuid
import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor
from sqlalchemy import create_engine

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class PlayerService:
    def __init__(self):
        logger.info('Initializing PlayerService')
        conn = sqlite3.connect("player.db")
        self.conn = conn
        self.cursor = conn.cursor()
        self.columns = self.get_columns()
        logger.info(f'PlayerService initialized with {len(self.columns)} columns')

    def get_all_players(self):
        logger.info('get_all_players() called')
        try:
            query = "SELECT * FROM players"
            result = self.cursor.execute(query).fetchall()
            players = []
            for row in result:
                dic = self.convert_row_to_dict(row)
                players.append(dic)
            logger.info(f'Retrieved {len(players)} players')
            return players
        except Exception as e:
            logger.error(f'Error in get_all_players: {str(e)}')
            raise
   
    def get_all_players_with_pagination(self, page=1, size=20, sort_by="playerId", order="asc"):
        logger.info(f'get_all_players_with_pagination() - page={page}, size={size}, sort_by={sort_by}, order={order}')
        try:
            # Request Validation
            if not isinstance(page, int) or page < 1:
                logger.warning(f'Invalid page parameter: {page}')
                return {
                    "error": "page must be posotive integer",
                    "code": "INVALID_INPUT",
                    "status": 400,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
            
            if not isinstance(size, int) or size < 1:
                logger.warning(f'Invalid size parameter: {size}')
                return {
                    "error": "size must be posotive integer",
                    "code": "INVALID_INPUT",
                    "status": 400,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
            
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
            logger.info(f'Pagination result - total: {total}, page: {page}, players: {len(players)}')
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
            logger.error(f'Error in get_all_players_with_pagination: {str(ex)}')
            return {
                "error": "unexpected error occured",
                "code": "INTERNAL_ERROR",
                "status": 500,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }

    def search_by_player(self, player_id):
        logger.info(f'Searching for player: {player_id}')
        try:
            query = "SELECT * FROM players WHERE playerId='{}'".format(player_id)
            result = self.cursor.execute(query).fetchall()

            for row in result:
                dic = self.convert_row_to_dict(row)
            if result:
                logger.info(f'Player found: {player_id}')
            else:
                logger.warning(f'Player not found: {player_id}')
            return dic
        except Exception as e:
            logger.error(f'Error in search_by_player: {str(e)}')
            raise

    def search_by_country(self, birth_country):
        logger.info(f'Searching for players from country: {birth_country}')
        try:
            query = "SELECT * FROM players WHERE birthCountry='{}'".format(birth_country)
            result = self.cursor.execute(query).fetchall()
            logger.info(f'Found {len(result)} players from {birth_country}')
            return result
        except Exception as e:
            logger.error(f'Error in search_by_country: {str(e)}')
            raise

    def search_by_country_multiple(self, birth_countries: list):
        """Search for players from multiple countries"""
        logger.info(f'Searching for players from multiple countries: {birth_countries}')
        try:
            if not birth_countries:
                logger.warning('Empty birth_countries list')
                return {
                "error": "birth_countries cant be empty",
                "code": "INVALID_PARAM",
                "status": 400,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        
            placeholders = ", ".join("?" * len(birth_countries))
            query = f"SELECT * FROM players WHERE birthCountry IN ({placeholders})"
            result = self.cursor.execute(query, birth_countries).fetchall()
            players = [self.convert_row_to_dict(row) for row in result]
            logger.info(f'Found {len(players)} players from {len(birth_countries)} countries')
            return {
                "players": players,
                "countries": birth_countries,
                "total": len(players)
            }
        except Exception as e:
            logger.error(f'Error in search_by_country_multiple: {str(e)}')
            raise

    def search_by_country_multiple_async(self, birth_countries: list):
        """Fetch players from multiple countries using asyncio and search_by_country (max 5 concurrent)"""
        logger.info(f'search_by_country_multiple_async() - countries: {len(birth_countries)}')
        
        if not birth_countries:
            logger.warning('Empty birth_countries list in async')
            return {
                "error": "birth_countries cant be empty",
                "code": "INVALID_PARAM",
                "status": 400,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        
        async def fetch_countries_async():
            semaphore = asyncio.Semaphore(5)
            
            async def fetch_with_semaphore(country):
                async with semaphore:
                    return await asyncio.to_thread(self.search_by_country, country)
            
            tasks = [fetch_with_semaphore(country) for country in birth_countries]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            return results
        
        try:
            results = asyncio.run(fetch_countries_async())
            players = []
            not_found = []
            
            for country, result in zip(birth_countries, results):
                if isinstance(result, Exception):
                    not_found.append(country)
                elif result:
                    players.extend([self.convert_row_to_dict(row) if not isinstance(row, dict) else row for row in result])
                else:
                    not_found.append(country)
            
            return {
                "players": players,
                "countries": birth_countries,
                "not_found": not_found,
                "total": len(players)
            }
        except Exception as e:
            logger.error(f'Error in search_by_country_multiple_async: {str(e)}')
            return {
                "error": "Error fetching players from countries with asyncio",
                "code": "INTERNAL_ERROR",
                "status": 500,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }, 500

    def search_by_country_multiple_threadpool(self, birth_countries: list):
        """Fetch players from multiple countries using ThreadPoolExecutor and search_by_country (max 5 workers)"""
        logger.info(f'search_by_country_multiple_threadpool() - countries: {len(birth_countries)}')
        
        if not birth_countries:
            logger.warning('Empty birth_countries list in threadpool')
            return {
                "error": "birth_countries cant be empty",
                "code": "INVALID_PARAM",
                "status": 400,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        
        try:
            players = []
            not_found = []
            
            with ThreadPoolExecutor(max_workers=5) as executor:
                future_to_country = {executor.submit(self.search_by_country, country): country for country in birth_countries}
                
                for future in future_to_country:
                    try:
                        result = future.result()
                        if result:
                            players.extend([self.convert_row_to_dict(row) if not isinstance(row, dict) else row for row in result])
                        else:
                            not_found.append(future_to_country[future])
                    except Exception:
                        not_found.append(future_to_country[future])
            
            return {
                "players": players,
                "countries": birth_countries,
                "not_found": not_found,
                "total": len(players)
            }, 200
        except Exception as e:
            logger.error(f'Error in search_by_country_multiple_threadpool: {str(e)}')
            return {
                "error": "Error fetching players from countries with threadpool",
                "code": "INTERNAL_ERROR",
                "status": 500,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }, 500


    def convert_row_to_dict(self, row):
        dic = { self.columns[i]: row[i] for i in range(len(row)) }
        return dic


    def get_columns(self):
        self.cursor.execute("PRAGMA table_info(players)")
        columns = [column[1] for column in self.cursor.fetchall()]
        return columns
    
    def add_player(self, data:dict):
        logger.info(f'Adding new player with data: {data.get("playerId", "unknown")}')  
        try:
            #Validation Logic 

            if not isinstance(data, dict) or not data:
                return {
                    "error": "request body can't be empty string",
                    "code": "INVALID_PARAM",
                    "status": 400,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }, 400
            
            missing = {"birthYear"} - data.keys()

            if missing:
                return {
                    "error": f"Missing required fields: {missing}",
                    "code": "MISSING_FIELDS",
                    "status": 400,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }, 400
            
            pid = data["playerId"]

            # if not pid:
            #     pid = uuid.uuid4()

            self.cursor.execute("SELECT 1 from players WHERE playerId=?", (pid,))
            if self.cursor.fetchone():
                return {
                    "error": f"player with {pid} already exist",
                    "code": "COMFLICT",
                    "status": 409,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }, 409

            valid_keys = [k for k in data if k in self.columns]
            cols_str = ", ".join(valid_keys)
            placeholders = ", ".join("?" for _ in valid_keys)

            values = [data[k] for k in valid_keys]

            self.cursor.execute(
                f"INSTERT INTO players ({cols_str} VALUES ({placeholders}))", values
            )
            self.conn.commit()
            logger.info(f'Player {pid} added successfully')
            return {"message": f"player '{pid}' added"}, 201

        except Exception as e:
            logger.error(f'Error in add_player: {str(e)}')
            return {
                "error": "Server Error",
                "code": "INTERNAL_ERROR",
                "status": 500,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }

    def update_player(self, player_id:str, data:dict):
        logger.info(f'Updating player: {player_id}')
        try:
            #Validation Logic 

            if not player_id:
                return {
                    "error": "player_id must be non-empty",
                    "code": "INVALID_PARAM",
                    "status": 400,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }, 400
            if not isinstance(data, dict) or not data:
                return {
                    "error": "request body can't be empty string",
                    "code": "INVALID_PARAM",
                    "status": 400,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }, 400
            
            missing = {"birthYear"} - data.keys()

            if missing:
                return {
                    "error": f"Missing required fields: {missing}",
                    "code": "MISSING_FIELDS",
                    "status": 400,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }, 400
            
            pid = player_id

            # if not pid:
            #     pid = uuid.uuid4()

            self.cursor.execute("SELECT 1 from players WHERE playerId=?", (pid,))
            if not self.cursor.fetchone():
                return {
                    "error": f"player with {pid} not found",
                    "code": "NOT_FOUND",
                    "status": 404,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }, 404

            valid_keys = [k for k in data if k in self.columns]
            set_clause = ", ".join(f"{k}=?" for k in valid_keys)

            values = [data[k] for k in valid_keys]
            values.append(pid)

            self.cursor.execute(
                f"UPDATE players SET {set_clause} WHERE playerId = ?", values
            )
            self.conn.commit()
            logger.info(f'Player {pid} updated successfully')
            return {"message": f"player '{pid}' updated"}, 200

        except Exception as e:
            logger.error(f'Error in update_player: {str(e)}')
            return {
                "error": "Server Error",
                "code": "INTERNAL_ERROR",
                "status": 500,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }, 500


    def delete(self, player_id: str):
        logger.info(f'Deleting player: {player_id}')
        try:
            if not player_id or not isinstance(player_id, str):
                return {
                    "error": "player_id must be non empty string",
                    "code": "INVALID_PARAM",
                    "status": 400,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }, 400

            self.cursor.execute("SELECT 1 from players WHERE playerId = ?", (player_id))

            if not self.cursor.fetchone():
                return {
                    "error": "player not found",
                    "code": "NOT_FOUND",
                    "status": 404,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }, 404
            
            self.cursor.execute("DELETE from players WHERE playerId = ?", (player_id))
            self.conn.commit()
            logger.info(f'Player {player_id} deleted successfully')
            return {"message": f"Player '{player_id}' deleted"}, 200
        
        except Exception as e:
            logger.error(f'Error in delete: {str(e)}')
            self.conn.rollback()
            return {
                "error": "failed to delete",
                "code": "INTERNAL_ERROR",
                "status": 500,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }

    def get_bulk(self, player_ids:list):
        logger.info(f'Getting bulk players: {len(player_ids)} IDs')
        try:
            if not player_ids:
                logger.warning('Empty player_ids list')
                return {
                "error": "player_ids cant be empty",
                "code": "INVALID_PARAM",
                "status": 400,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        
            placeholders = ", ".join("?" * len(player_ids))
            query = f"SELECT * FROM Players WHERE playerId IN ({placeholders})"
            result = self.cursor.execute(query, player_ids).fetchall()
            players = [self.convert_row_to_dict(row) for row in result]

            found_ids = {r["playerId"] for r in players}
            not_found = [pid for pid in player_ids if pid not in found_ids]
            logger.info(f'Bulk result - found: {len(players)}, not_found: {len(not_found)}')
            return {
                "players": players,
                "not_found": not_found,
                "total": len(players)
            }
        except Exception as e:
            logger.error(f'Error in get_bulk: {str(e)}')
            raise

    def get_bulk_async(self, player_ids: list):
        """Fetch multiple players using asyncio and search_by_player (max 5 concurrent)"""
        logger.info(f'get_bulk_async() - player_ids: {len(player_ids)}')
        
        if not player_ids:
            logger.warning('Empty player_ids list in async')
            return {
                "error": "player_ids cant be empty",
                "code": "INVALID_PARAM",
                "status": 400,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        
        async def fetch_players_async():
            semaphore = asyncio.Semaphore(5)
            
            async def fetch_with_semaphore(pid):
                async with semaphore:
                    return await asyncio.to_thread(self.search_by_player, pid)
            
            tasks = [fetch_with_semaphore(pid) for pid in player_ids]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            return results
        
        try:
            results = asyncio.run(fetch_players_async())
            players = []
            not_found = []
            
            for pid, result in zip(player_ids, results):
                if isinstance(result, Exception):
                    not_found.append(pid)
                elif result:
                    players.append(result)
                else:
                    not_found.append(pid)
            
            return {
                "players": players,
                "not_found": not_found,
                "total": len(players)
            }
        except Exception as e:
            logger.error(f'Error in get_bulk_async: {str(e)}')
            return {
                "error": "Error fetching players with asyncio",
                "code": "INTERNAL_ERROR",
                "status": 500,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }, 500

    def get_bulk_threadpool(self, player_ids: list):
        """Fetch multiple players using ThreadPoolExecutor and search_by_player"""
        logger.info(f'get_bulk_threadpool() - player_ids: {len(player_ids)}')
        
        if not player_ids:
            logger.warning('Empty player_ids list in threadpool')
            return {
                "error": "player_ids cant be empty",
                "code": "INVALID_PARAM",
                "status": 400,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        
        try:
            players = []
            not_found = []
            
            with ThreadPoolExecutor(max_workers=5) as executor:
                future_to_pid = {executor.submit(self.search_by_player, pid): pid for pid in player_ids}
                
                for future in future_to_pid:
                    try:
                        result = future.result()
                        if result:
                            players.append(result)
                        else:
                            not_found.append(future_to_pid[future])
                    except Exception:
                        not_found.append(future_to_pid[future])
            
            return {
                "players": players,
                "not_found": not_found,
                "total": len(players)
            }, 200
        except Exception as e:
            logger.error(f'Error in get_bulk_threadpool: {str(e)}')
            return {
                "error": "Error fetching players with threadpool",
                "code": "INTERNAL_ERROR",
                "status": 500,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }, 500
