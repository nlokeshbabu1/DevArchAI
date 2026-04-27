"""Unit tests for organization auto-provisioning."""

import uuid
from types import SimpleNamespace

import pytest

from app.models.organization import MembershipRole, Organization, OrganizationMember
from app.services.organization_provisioning import (
    _build_personal_org_name,
    _slugify_org_name,
    ensure_user_organization_membership,
)


class _Result:
    def __init__(self, value):
        self._value = value

    def scalar_one_or_none(self):
        return self._value


class _FakeSession:
    def __init__(self, execute_results):
        self._execute_results = list(execute_results)
        self.added = []
        self.flush_calls = 0

    async def execute(self, _statement):
        if not self._execute_results:
            raise AssertionError("Unexpected execute() call")
        return self._execute_results.pop(0)

    def add(self, obj):
        self.added.append(obj)
        if getattr(obj, "id", None) is None:
            obj.id = uuid.uuid4()

    async def flush(self):
        self.flush_calls += 1


def test_slugify_org_name_normalizes_input():
    assert _slugify_org_name("Jane Doe's Workspace!") == "jane-doe-s-workspace"
    assert _slugify_org_name("   ") == "workspace"


def test_build_personal_org_name_prefers_full_name():
    user = SimpleNamespace(full_name="Jane Doe", username="jane")
    assert _build_personal_org_name(user) == "Jane Doe's Workspace"


@pytest.mark.asyncio
async def test_ensure_user_organization_membership_creates_personal_workspace():
    user = SimpleNamespace(
        id=uuid.uuid4(),
        current_org_id=None,
        full_name="Jane Doe",
        username="jane",
    )
    db = _FakeSession([
        _Result(None),  # existing membership lookup
        _Result(None),  # slug uniqueness check
    ])

    membership = await ensure_user_organization_membership(db, user)

    assert membership.organization_id == user.current_org_id
    assert membership.user_id == user.id
    assert membership.role == MembershipRole.OWNER
    assert any(isinstance(obj, Organization) for obj in db.added)
    assert any(isinstance(obj, OrganizationMember) for obj in db.added)
    assert db.flush_calls >= 2


@pytest.mark.asyncio
async def test_ensure_user_organization_membership_reuses_existing_membership():
    user_id = uuid.uuid4()
    organization_id = uuid.uuid4()
    user = SimpleNamespace(
        id=user_id,
        current_org_id=None,
        full_name=None,
        username="jane",
    )
    existing_membership = OrganizationMember(
        organization_id=organization_id,
        user_id=user_id,
        role=MembershipRole.ADMIN,
    )
    db = _FakeSession([
        _Result(existing_membership),
    ])

    membership = await ensure_user_organization_membership(db, user)

    assert membership is existing_membership
    assert user.current_org_id == organization_id
    assert db.flush_calls == 1
    assert db.added == []
