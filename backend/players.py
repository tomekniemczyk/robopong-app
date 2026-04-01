"""Player profiles — SQLite storage via db module."""

import db


def get_players() -> list:
    return db.get_players()


def get_player(player_id: int) -> dict | None:
    return db.get_player(player_id)


def create_player(name: str, handedness: str = "right", lang: str = "pl") -> dict:
    name = name.strip()
    if not name:
        raise ValueError("Name cannot be empty")
    if db.player_name_exists(name):
        raise ValueError(f"Player '{name}' already exists")
    if handedness not in ("right", "left"):
        handedness = "right"
    return db.create_player(name, handedness, lang)


def update_player(player_id: int, name: str | None = None,
                  handedness: str | None = None, lang: str | None = None) -> dict | None:
    if name is not None:
        name = name.strip()
        if not name:
            raise ValueError("Name cannot be empty")
        if db.player_name_exists(name, exclude_id=player_id):
            raise ValueError(f"Player '{name}' already exists")
    if handedness is not None and handedness not in ("right", "left"):
        handedness = "right"
    return db.update_player(player_id, name=name, handedness=handedness, lang=lang)


def delete_player(player_id: int) -> bool:
    return db.delete_player(player_id)
