from datetime import datetime
from unittest.mock import MagicMock

from models.models import User
from services.users import get_user, upsert_user, get_all_users


def test_get_all_users():
    db = MagicMock()
    users_list = [User(user_id="1"), User(user_id="2")]
    db.query.return_value.all.return_value = users_list

    result = get_all_users(db)
    assert len(result) == 2
    assert result[0].user_id == "1"
    assert result[1].user_id == "2"


def test_upsert_user_creates_new_user():
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = None

    user = upsert_user(db, "u-new", "alice", "teams")

    assert user.user_id == "u-new"
    assert user.username == "alice"
    db.add.assert_called_once()
    db.commit.assert_called_once()
    db.refresh.assert_called_once_with(user)


def test_upsert_user_updates_existing_user():
    db = MagicMock()
    existing = User(user_id="u1", username="old")
    existing.last_seen = datetime(2024, 1, 1)
    db.query.return_value.filter.return_value.first.return_value = existing

    user = upsert_user(db, "u1", "new-name")

    assert user is existing
    assert user.last_seen >= datetime(2024, 1, 1)
    db.add.assert_not_called()
    db.commit.assert_called_once()
    db.refresh.assert_called_once_with(existing)


def test_get_user_returns_none_when_missing():
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = None

    assert get_user(db, "missing") is None
