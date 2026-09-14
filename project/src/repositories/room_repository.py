class Room:
    def __init__(self, id, name, capacity, is_available=True):
        self.id = id
        self.name = name
        self.capacity = capacity
        self.is_available = is_available
