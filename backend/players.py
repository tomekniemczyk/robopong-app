"""Player profiles — SQLite storage via db module."""

import db


def get_players() -> list:
    return db.get_players()


def get_player(player_id: int) -> dict | None:
    return db.get_player(player_id)


def create_player(name: str) -> dict:
    return db.create_player(name)


def update_player(player_id: int, name: str) -> dict | None:
    return db.update_player(player_id, name)


def delete_player(player_id: int) -> bool:
    return db.delete_player(player_id)
