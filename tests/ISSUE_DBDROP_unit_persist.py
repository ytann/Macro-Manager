import pytest
from app.services.database import DatabaseManager
from app.core.config import Config
import sqlite3


def test_foodbank_persists_across_restart(tmp_path, monkeypatch):
    """Demonstrates bug: _init_foodbank() drops and recreates the foods FTS5 table
    every time, losing all user-learned food data on server restart."""
    foodbank_path = str(tmp_path / "foodbank.db")
    macros_path = str(tmp_path / "macros.db")
    monkeypatch.setattr(Config, "FOODBANK_DB_PATH", foodbank_path)
    monkeypatch.setattr(Config, "MACROS_DB_PATH", macros_path)

    # First boot: DatabaseManager seeds default foods
    db1 = DatabaseManager()

    # Manually insert a user-learned food item
    with sqlite3.connect(foodbank_path) as conn:
        conn.execute(
            "INSERT INTO foods VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            ("TestFood", "test", 100, 10, 5, 3, 1, 0, 0, "user_learned"),
        )
        conn.commit()

    # Verify insertion succeeded
    with sqlite3.connect(foodbank_path) as conn:
        count_before = conn.execute(
            "SELECT COUNT(*) FROM foods WHERE name = 'TestFood'"
        ).fetchone()[0]
    assert count_before == 1

    # Simulate server restart: new DatabaseManager instance
    db2 = DatabaseManager()

    # Check if user-learned food survived
    with sqlite3.connect(foodbank_path) as conn:
        count_after = conn.execute(
            "SELECT COUNT(*) FROM foods WHERE name = 'TestFood'"
        ).fetchone()[0]

    assert count_after == 1, (
        f"BUG: User-learned food 'TestFood' lost after restart. "
        f"Expected count=1, got count={count_after}. "
        f"Root cause: _init_foodbank() calls DROP TABLE on every init."
    )