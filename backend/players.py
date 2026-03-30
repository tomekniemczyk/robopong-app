"""Player profiles — file-based storage."""

import json
from datetime import datetime
from pathlib import Path

PLAYERS_FILE = Path(__file__).parent / ".players.json"


def _load() -> list:
    try:
        return json.loads(PLAYERS_FILE.read_text())
    except Exception:
        return []


def _save(data: list):
    PLAYERS_FILE.write_text(json.dumps(data, indent=2))


def get_players() -> list:
    return _load()


def get_player(player_id: int) -> dict | None:
    for p in _load():
        if p.get("id") == player_id:
            return p
    return None


def create_player(name: str) -> dict:
    players = _load()
    new_id = max((p.get("id", 0) for p in players), default=0) + 1
    player = {"id": new_id, "name": name, "created_at": datetime.now().isoformat()}
    players.append(player)
    _save(players)
    return player


def update_player(player_id: int, name: str) -> dict | None:
    players = _load()
    for p in players:
        if p.get("id") == player_id:
            p["name"] = name
            _save(players)
            return p
    return None


def delete_player(player_id: int) -> bool:
    players = _load()
    new_list = [p for p in players if p.get("id") != player_id]
    if len(new_list) == len(players):
        return False
    _save(new_list)
    return True
