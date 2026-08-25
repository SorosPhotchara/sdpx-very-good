class FakeRoomRepo:
    def __init__(self, rooms=None):
        self._rooms = {r.id: r for r in (rooms or [])}

    def find_by_id(self, room_id):
        return self._rooms.get(room_id)

    def find_available(self, start_time, end_time):
        return [r for r in self._rooms.values() if r.is_available]

    def save(self, room):
        self._rooms[room.id] = room
        return room
