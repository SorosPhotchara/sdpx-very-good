class FakeUserRepo:
    def __init__(self, users=None):
        self._users = {u.id: u for u in (users or [])}

    def find_by_id(self, user_id):
        return self._users.get(user_id)

    def save(self, user):
        self._users[user.id] = user
        return user
