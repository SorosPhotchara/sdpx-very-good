"""Property-based tests for the pairing engine (NFR-MAINT-02, INV-1 … INV-5).

The example-based tests in ``test_pairing.py`` cover the two classroom shapes
the PRD happens to describe. These cover the shapes nobody thought to write
down — which is where pairing bugs live.
"""

from __future__ import annotations

from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from app.pairing import (
    check_invariants,
    coverage_by_pair,
    generate_group_pairs,
    generate_individual_pairs,
    individual_plan,
    solve_group_feasibility,
)
from tests.factories import make_classroom, make_config, make_criterion
from app.domain import Side

# Kept inside the PRD's stated envelope: 3–8 members per group (A2/A3).
# Group counts start at 3, because with only two groups every student sits
# inside the single pair and nobody is eligible to judge it — that case is
# refused outright, and ``test_pairing.py`` covers it separately (OQ-8).
group_counts = st.integers(min_value=3, max_value=8)
group_sizes = st.integers(min_value=3, max_value=8)
coverages = st.integers(min_value=1, max_value=6)
seeds = st.integers(min_value=0, max_value=10**6)

SLOW = settings(
    max_examples=40,
    deadline=None,
    suppress_health_check=[HealthCheck.too_slow],
)


@SLOW
@given(num_groups=group_counts, group_size=group_sizes, coverage=coverages, seed=seeds)
def test_group_pairing_upholds_every_invariant(num_groups, group_size, coverage, seed):
    students = make_classroom(num_groups=num_groups, group_size=group_size)
    config = make_config(target_coverage=coverage, pairing_seed=seed)

    pairs = generate_group_pairs(students, make_criterion(), config, "a1")

    check_invariants(pairs, {s.id: s.group_id for s in students})


@SLOW
@given(num_groups=group_counts, group_size=group_sizes, coverage=coverages, seed=seeds)
def test_group_pairing_is_reproducible_from_its_seed(
    num_groups, group_size, coverage, seed
):
    """INV-5 / FR-PAIR-09."""
    students = make_classroom(num_groups=num_groups, group_size=group_size)
    config = make_config(target_coverage=coverage, pairing_seed=seed)

    first = generate_group_pairs(students, make_criterion(), config, "a1")
    second = generate_group_pairs(students, make_criterion(), config, "a1")

    assert first == second


@SLOW
@given(num_groups=group_counts, group_size=group_sizes, coverage=coverages)
def test_delivered_coverage_never_exceeds_what_feasibility_promised(
    num_groups, group_size, coverage
):
    students = make_classroom(num_groups=num_groups, group_size=group_size)
    config = make_config(target_coverage=coverage)

    feasibility = solve_group_feasibility(
        {f"g{n + 1}": group_size for n in range(num_groups)}, config
    )
    pairs = generate_group_pairs(students, make_criterion(), config, "a1")

    assert max(coverage_by_pair(pairs).values()) <= feasibility.coverage
    assert feasibility.coverage <= coverage


@SLOW
@given(group_size=st.integers(min_value=0, max_value=12))
def test_individual_plan_never_promises_more_coverage_than_members_allow(group_size):
    """§8.3 — a pair inside a group of m can be judged by at most m − 2 people."""
    plan = individual_plan(group_size, make_config(max_workload=30))

    assert plan.coverage <= max(0, group_size - 2)
    if group_size <= 2:
        assert plan.enabled is False


@SLOW
@given(group_size=st.integers(min_value=3, max_value=8), seed=seeds)
def test_individual_pairing_upholds_every_invariant(group_size, seed):
    members = make_classroom(num_groups=1, group_size=group_size)
    config = make_config(pairing_seed=seed, max_workload=30)

    pairs = generate_individual_pairs(
        members, make_criterion(side=Side.INDIVIDUAL), config, "a1"
    )

    check_invariants(pairs, {member.id: member.id for member in members})
