from __future__ import annotations

from app.domain.roster import RosterRow

_GROUP_NAMES = ["Aurora", "Nova", "Orion", "Vega", "Lyra", "Atlas", "Halley", "Cygnus"]


def make_roster_row(**overrides: str) -> RosterRow:
    defaults = {"email": "student@uni.ac.th", "group_name": "Aurora"}
    defaults.update(overrides)
    return RosterRow(email=defaults["email"], group_name=defaults["group_name"])


def make_roster_csv(rows: list[RosterRow]) -> str:
    lines = ["email,group_name"]
    lines.extend(f"{row.email},{row.group_name}" for row in rows)
    return "\n".join(lines)


def make_roster(group_sizes: list[int]) -> list[RosterRow]:
    rows: list[RosterRow] = []
    for group_index, size in enumerate(group_sizes):
        group_name = (
            _GROUP_NAMES[group_index]
            if group_index < len(_GROUP_NAMES)
            else f"Group{group_index}"
        )
        for member_index in range(size):
            email = f"{group_name.lower()}{member_index}@uni.ac.th"
            rows.append(RosterRow(email=email, group_name=group_name))
    return rows
