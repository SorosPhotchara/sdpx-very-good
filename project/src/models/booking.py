class Booking:
    def __init__(self, id, room_id, user_id, start, end, status="confirmed"):
        self.id = id
        self.room_id = room_id
        self.user_id = user_id
        self.start = start
        self.end = end
        self.status = status
