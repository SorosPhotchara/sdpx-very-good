from datetime import datetime, time

from exceptions import (
    ConflictError,
    ForbiddenError,
    InvalidTimeRangeError,
    NotFoundError,
    RoomNotAvailableError,
    UserNotFoundError,
)
from models.booking import Booking


def _parse_time(value):
    if isinstance(value, time):
        return value
    return datetime.strptime(value, "%H:%M").time()


def _times_overlap(start_a, end_a, start_b, end_b):
    return start_a < end_b and start_b < end_a


class BookingService:
    def __init__(self, room_repo, user_repo=None, booking_repo=None):
        self._room_repo = room_repo
        self._user_repo = user_repo
        self._booking_repo = booking_repo

    def create_booking(self, room_id, user_id, start, end, *, now=None):
        start_time = _parse_time(start)
        end_time = _parse_time(end)

        if end_time <= start_time:
            raise InvalidTimeRangeError("End time must be after start time")

        current = now or datetime.now()
        booking_start = datetime.combine(current.date(), start_time)
        if booking_start < current:
            raise InvalidTimeRangeError("Cannot book in the past")

        if self._user_repo and not self._user_repo.find_by_id(user_id):
            raise UserNotFoundError(f"User {user_id} not found")

        room = self._room_repo.find_by_id(room_id)
        if room is None or not room.is_available:
            raise RoomNotAvailableError(f"Room {room_id} is not available")

        if self._booking_repo:
            for existing in self._booking_repo.find_by_room(room_id):
                if existing.status == "cancelled":
                    continue
                if _times_overlap(
                    start_time,
                    end_time,
                    _parse_time(existing.start),
                    _parse_time(existing.end),
                ):
                    raise ConflictError(
                        f"Room {room_id} has a conflicting booking"
                    )

        booking = Booking(
            id=None,
            room_id=room_id,
            user_id=user_id,
            start=start,
            end=end,
            status="confirmed",
        )

        if self._booking_repo:
            booking = self._booking_repo.save(booking)

        return booking

    def cancel_booking(self, booking_id, user_id):
        if not self._booking_repo:
            raise NotFoundError(f"Booking {booking_id} not found")

        booking = self._booking_repo.find_by_id(booking_id)
        if booking is None:
            raise NotFoundError(f"Booking {booking_id} not found")

        if booking.user_id != user_id:
            raise ForbiddenError("You cannot cancel another user's booking")

        booking.status = "cancelled"
        self._booking_repo.save(booking)
        return booking
