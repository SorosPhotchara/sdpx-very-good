class FakeBookingRepo:
    def __init__(self, bookings=None):
        self._bookings = {}
        self._next_id = 1
        for booking in bookings or []:
            self.save(booking)

    def find_by_id(self, booking_id):
        return self._bookings.get(booking_id)

    def find_by_room(self, room_id):
        return [b for b in self._bookings.values() if b.room_id == room_id]

    def save(self, booking):
        if booking.id is None:
            booking.id = self._next_id
            self._next_id += 1
        self._bookings[booking.id] = booking
        return booking
