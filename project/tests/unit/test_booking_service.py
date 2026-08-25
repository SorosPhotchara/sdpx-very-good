import pytest

from exceptions import (
    ConflictError,
    ForbiddenError,
    InvalidTimeRangeError,
    NotFoundError,
    RoomNotAvailableError,
    UserNotFoundError,
)
from fakes import FakeBookingRepo, FakeRoomRepo, FakeUserRepo
from services import BookingService
from factories import make_booking


def _service(*, rooms=None, users=None, bookings=None):
    return BookingService(
        room_repo=FakeRoomRepo(rooms or []),
        user_repo=FakeUserRepo(users or []),
        booking_repo=FakeBookingRepo(bookings or []),
    )


def test_create_booking_confirms_when_room_is_available(
    available_room, student, future_now
):
    service = _service(rooms=[available_room], users=[student])

    result = service.create_booking(
        room_id=available_room.id,
        user_id=student.id,
        start="13:00",
        end="15:00",
        now=future_now,
    )

    assert result.status == "confirmed"
    assert result.room_id == available_room.id


def test_create_booking_raises_room_not_available_error_when_room_is_unavailable(
    unavailable_room, student, future_now
):
    service = _service(rooms=[unavailable_room], users=[student])

    with pytest.raises(RoomNotAvailableError):
        service.create_booking(
            room_id=unavailable_room.id,
            user_id=student.id,
            start="13:00",
            end="15:00",
            now=future_now,
        )


def test_create_booking_raises_conflict_error_when_time_overlaps(
    available_room, student, future_now
):
    existing = make_booking(
        room_id=available_room.id,
        user_id=student.id,
        start="14:00",
        end="16:00",
    )
    service = _service(rooms=[available_room], users=[student], bookings=[existing])

    with pytest.raises(ConflictError):
        service.create_booking(
            room_id=available_room.id,
            user_id=student.id,
            start="13:00",
            end="15:00",
            now=future_now,
        )


def test_create_booking_raises_user_not_found_error_when_user_does_not_exist(
    available_room, future_now
):
    service = _service(rooms=[available_room], users=[])

    with pytest.raises(UserNotFoundError):
        service.create_booking(
            room_id=available_room.id,
            user_id=999,
            start="13:00",
            end="15:00",
            now=future_now,
        )


def test_create_booking_raises_invalid_time_range_error_when_booking_in_past(
    available_room, student, past_now
):
    service = _service(rooms=[available_room], users=[student])

    with pytest.raises(InvalidTimeRangeError):
        service.create_booking(
            room_id=available_room.id,
            user_id=student.id,
            start="13:00",
            end="15:00",
            now=past_now,
        )


def test_cancel_booking_sets_status_cancelled_when_booking_exists_and_belongs_to_user(
    student, available_room
):
    booking = make_booking(room_id=available_room.id, user_id=student.id)
    service = _service(rooms=[available_room], users=[student], bookings=[booking])

    result = service.cancel_booking(booking_id=booking.id, user_id=student.id)

    assert result.status == "cancelled"


def test_cancel_booking_raises_forbidden_error_when_booking_belongs_to_other_user(
    student, other_student, available_room
):
    booking = make_booking(room_id=available_room.id, user_id=student.id)
    service = _service(
        rooms=[available_room],
        users=[student, other_student],
        bookings=[booking],
    )

    with pytest.raises(ForbiddenError):
        service.cancel_booking(booking_id=booking.id, user_id=other_student.id)


def test_cancel_booking_raises_not_found_error_when_booking_does_not_exist(
    student, available_room
):
    service = _service(rooms=[available_room], users=[student])

    with pytest.raises(NotFoundError):
        service.cancel_booking(booking_id=999, user_id=student.id)
