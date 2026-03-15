import uuid


def generate_user_payload():
    key = uuid.uuid4().hex[:8]
    return {
        "user_id": f"user_{key}",
        "username": f"user_{key}",
        "channel_id": "test-channel",
    }
