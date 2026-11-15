"""Event lifecycle state machine.

DRAFT -> SUBMITTED -> PUBLISHED -> IN_PROGRESS -> COMPLETED, and CANCELLED from
any non-final state. Organizers may submit a draft for review (or withdraw it);
every other transition needs an organization admin (or super admin).
"""

from app.models.models import EventStatus, OrgRole

S = EventStatus

ALLOWED_TRANSITIONS: dict[EventStatus, frozenset[EventStatus]] = {
    S.DRAFT: frozenset({S.SUBMITTED, S.PUBLISHED, S.CANCELLED}),
    S.SUBMITTED: frozenset({S.DRAFT, S.PUBLISHED, S.CANCELLED}),
    S.PUBLISHED: frozenset({S.IN_PROGRESS, S.CANCELLED}),
    S.IN_PROGRESS: frozenset({S.COMPLETED, S.CANCELLED}),
    S.COMPLETED: frozenset(),
    S.CANCELLED: frozenset(),
}

# Transitions an ORGANIZER may perform; ORG_ADMIN may perform all allowed ones.
ORGANIZER_TRANSITIONS: frozenset[tuple[EventStatus, EventStatus]] = frozenset(
    {(S.DRAFT, S.SUBMITTED), (S.SUBMITTED, S.DRAFT)}
)

FINAL_STATUSES: frozenset[EventStatus] = frozenset({S.COMPLETED, S.CANCELLED})


def is_transition_allowed(current: EventStatus, target: EventStatus) -> bool:
    return target in ALLOWED_TRANSITIONS[current]


def roles_for_transition(current: EventStatus, target: EventStatus) -> tuple[OrgRole, ...]:
    if (current, target) in ORGANIZER_TRANSITIONS:
        return (OrgRole.ADMIN, OrgRole.ORGANIZER)
    return (OrgRole.ADMIN,)
