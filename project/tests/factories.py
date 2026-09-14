from repositories import Room, User
from models.booking import Booking


def make_room(**overrides):
    defaults = {"id": 1, "name": "A101", "capacity": 10, "is_available": True}
    return Room(**{**defaults, **overrides})


def make_user(**overrides):
    defaults = {"id": 1, "name": "John", "email": "john@uni.ac.th", "role": "student"}
    return User(**{**defaults, **overrides})


def make_booking(**overrides):
    defaults = {
        "id": 1,
        "room_id": 1,
        "user_id": 1,
        "start": "13:00",
        "end": "15:00",
        "status": "confirmed",
    }
    return Booking(**{**defaults, **overrides})
