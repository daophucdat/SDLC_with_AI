from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest

from chatdocs.domain.access.permissions import Action, advertised_permissions, can
from chatdocs.domain.access.role_mapping import RoleGroups, role_from_groups
from chatdocs.domain.access.user import Role, User
from chatdocs.domain.documents.document import Document, DocumentStatus
from chatdocs.domain.documents.upload_policy import UploadPolicy
from chatdocs.domain.errors import FileNotPdf, FileTooLarge, InvalidState
from chatdocs.domain.ids import uuid7
from chatdocs.domain.jobs import JobType, next_run_after

GROUPS = RoleGroups(member="grp-bd-member", lead="grp-bd-lead", manager="grp-bd-manager")


@pytest.mark.parametrize(
    ("groups", "role"),
    [
        (["grp-bd-member"], Role.BD_MEMBER),
        (["/grp-bd-member"], Role.BD_MEMBER),  # Keycloak group path
        (["/org/bd/GRP-BD-LEAD"], Role.BD_LEAD),  # nested path, different case
        (["grp-bd-member", "grp-bd-lead"], Role.BD_LEAD),  # highest wins
        (["grp-bd-member", "grp-bd-manager"], Role.MANAGER),
        (["grp-ke-toan"], None),
        ([], None),
        (["", "  "], None),
    ],
)
def test_role_from_groups(groups, role):
    assert role_from_groups(groups, GROUPS) == role


def user(role: Role, active: bool = True) -> User:
    return User(uuid4(), "a@b.vn", "A", role, active)


def test_permissions_remove_rule_pd02():
    member, lead = user(Role.BD_MEMBER), user(Role.BD_LEAD)
    assert can(member, Action.DOCUMENTS_REMOVE, owner_id=member.id)
    assert not can(member, Action.DOCUMENTS_REMOVE, owner_id=uuid4())
    assert not can(member, Action.DOCUMENTS_REMOVE, owner_id=None)
    assert can(lead, Action.DOCUMENTS_REMOVE, owner_id=uuid4())


def test_permissions_by_role_and_inactive_users():
    assert can(user(Role.MANAGER), Action.METRICS_VIEW)
    assert not can(user(Role.BD_MEMBER), Action.METRICS_VIEW)
    assert can(user(Role.BD_LEAD), Action.EVALUATION_RUN)
    assert not can(user(Role.MANAGER), Action.EVALUATION_RUN)
    assert not can(user(Role.BD_LEAD, active=False), Action.DOCUMENTS_READ)
    assert advertised_permissions(user(Role.BD_MEMBER)) == []
    assert advertised_permissions(user(Role.BD_LEAD)) == ["documents:remove_any", "metrics:view", "evaluation:run"]


def test_upload_policy_size_and_magic():
    p = UploadPolicy(max_size_mb=50)
    p.check_size(50 * 1024 * 1024)
    with pytest.raises(FileTooLarge):
        p.check_size(50 * 1024 * 1024 + 1)
    with pytest.raises(FileNotPdf):
        p.check_size(0)
    p.check_head(b"%PDF-1.7\n...")
    p.check_head(b"\xef\xbb\xbf junk %PDF-1.4")  # header within the first KB is accepted
    with pytest.raises(FileNotPdf):
        p.check_head(b"\x89PNG\r\n\x1a\n")  # a PNG renamed to .pdf (EC-07)


@pytest.mark.parametrize(
    ("raw", "clean"),
    [
        ("Hop_dong_X.pdf", "Hop_dong_X.pdf"),
        ("C:\\Users\\a\\Bao gia.pdf", "Bao gia.pdf"),
        ("../../etc/passwd.pdf", "passwd.pdf"),
        ("bad\x00name.pdf", "badname.pdf"),
        ("", "tai-lieu.pdf"),
        (None, "tai-lieu.pdf"),
        ("Hợp đồng.pdf", "Hợp đồng.pdf"),
    ],
)
def test_clean_file_name(raw, clean):
    assert UploadPolicy.clean_file_name(raw) == clean


def test_clean_file_name_truncates_but_keeps_extension():
    name = UploadPolicy.clean_file_name("a" * 400 + ".pdf")
    assert len(name) == 255 and name.endswith(".pdf")


def _doc(status: DocumentStatus) -> Document:
    return Document(uuid7(), uuid7(), "f.pdf", 10, b"h", status, "k", uuid7(), datetime.now(timezone.utc))


def test_document_retry_only_from_error():
    assert _doc(DocumentStatus.ERROR).retried().status is DocumentStatus.PROCESSING
    for st in (DocumentStatus.READY, DocumentStatus.PROCESSING, DocumentStatus.NO_TEXT):
        with pytest.raises(InvalidState):
            _doc(st).retried()


def test_uuid7_is_time_ordered_and_versioned():
    ids = [uuid7() for _ in range(2000)]
    assert ids == sorted(ids)
    assert len(set(ids)) == len(ids)
    assert all(i.version == 7 for i in ids[:10])


def test_job_retry_schedule_process_document():
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    assert next_run_after(JobType.PROCESS_DOCUMENT, 1, now) == now + timedelta(seconds=30)
    assert next_run_after(JobType.PROCESS_DOCUMENT, 2, now) == now + timedelta(minutes=2)
    assert next_run_after(JobType.PROCESS_DOCUMENT, 3, now) == now + timedelta(minutes=10)
    assert next_run_after(JobType.PROCESS_DOCUMENT, 4, now) is None  # 1 attempt + 3 retries, then ERROR
    assert next_run_after(JobType.RUN_EVALUATION, 1, now) is None
