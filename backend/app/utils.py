from typing import List, Tuple

from sqlalchemy.orm import Session

from . import models

Pair = Tuple[int, int]


def generate_pairs(ids: List[int], target_coverage: int = 5) -> List[Tuple[int, int]]:
    pairs = []
    n = len(ids)
    for i in range(n):
        for j in range(i + 1, n):
            pairs.extend([(ids[i], ids[j])] * target_coverage)
    return pairs


def create_group_pairs(db: Session, assignment_id: int, criteria_id: int, group_ids: List[int]):
    pairs = generate_pairs(group_ids)
    for left_id, right_id in pairs:
        db_pair = models.Pair(
            assignment_id=assignment_id,
            criteria_id=criteria_id,
            left_group_id=left_id,
            right_group_id=right_id,
            pair_type="group",
        )
        db.add(db_pair)
    db.commit()


def create_individual_pairs(db: Session, assignment_id: int, criteria_id: int, student_ids: List[int]):
    pairs = generate_pairs(student_ids)
    for left_id, right_id in pairs:
        db_pair = models.Pair(
            assignment_id=assignment_id,
            criteria_id=criteria_id,
            left_id=left_id,
            right_id=right_id,
            pair_type="individual",
        )
        db.add(db_pair)
    db.commit()
