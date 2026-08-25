import pytest
from datetime import datetime

from factories import make_booking, make_room, make_user


@pytest.fixture
def available_room():
    return make_room(is_available=True)


@pytest.fixture
def unavailable_room():
    return make_room(is_available=False)


@pytest.fixture
def student():
    return make_user(role="student")


@pytest.fixture
def other_student():
    return make_user(id=2, name="Jane", email="jane@uni.ac.th", role="student")


@pytest.fixture
def future_now():
    return datetime(2026, 8, 11, 10, 0)


@pytest.fixture
def past_now():
    return datetime(2026, 8, 11, 16, 0)
