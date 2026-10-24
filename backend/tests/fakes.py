"""In-memory implementations of every port, used by unit and API tests (no PostgreSQL / MinIO / IdP needed)."""

from __future__ import annotations

import hashlib
import math
import shutil
from dataclasses import dataclass, field, replace
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from uuid import UUID

from chatdocs.adapters.analytics.postgres_sink import MemoryEventWriter
from chatdocs.adapters.db.qa_repository import LocalStopBus
from chatdocs.adapters.http.container import Container, make_gate, qa_config, retrieval_config, role_groups
from chatdocs.adapters.llm.fake import FakeAnswerGenerator
from chatdocs.adapters.llm.resilient import ResilientGenerator
from chatdocs.application.access_service import AccessService
from chatdocs.application.analytics_service import AnalyticsService
from chatdocs.application.document_service import DocumentService
from chatdocs.application.insights_service import EvaluationService, MetricsService
from chatdocs.application.qa_service import QuestionAnsweringService
from chatdocs.application.retrieval_service import RetrievalService
from chatdocs.domain.access.user import Role, User
from chatdocs.domain.documents.chunking import Chunk
from chatdocs.domain.documents.document import Document, DocumentStatus, ProcessingErrorCode
from chatdocs.domain.documents.upload_policy import UploadPolicy
from chatdocs.domain.errors import IdentityProviderError, InvalidState
from chatdocs.domain.evaluation.test_set import TestCase
from chatdocs.domain.ids import uuid7
from chatdocs.domain.jobs import TIMEOUTS, Job, JobStatus, JobType
from chatdocs.domain.qa.question import AnswerStatus, NotFoundReason, Question, Turn
from chatdocs.domain.retrieval.rrf import Candidate
from chatdocs.platform.config import Settings
from chatdocs.platform.rate_limit import RateLimiter
from chatdocs.ports.identity import IdTokenClaims
from chatdocs.ports.insights import EvaluationResult, EvaluationRun
from chatdocs.ports.qa import AnswerRecord, Conversation
from chatdocs.ports.repositories import DocumentPage, DocumentRow, SessionRecord


class FixedClock:
    def __init__(self, start: datetime | None = None) -> None:
        self.t = start or datetime(2026, 11, 9, 8, 0, tzinfo=timezone.utc)

    def now(self) -> datetime:
        return self.t

    def advance(self, **kw) -> None:
        self.t += timedelta(**kw)


# ---------------------------------------------------------------- identity
class FakeIdp:
    """`code` selects the identity: 'member', 'lead', 'manager', 'outsider', or 'broken' (IdP error)."""

    USERS = {
        "member": IdTokenClaims("s-1", "thu.ha@congty.vn", "Trần Thu Hà", ["/grp-bd-member"]),
        "member2": IdTokenClaims("s-4", "minh.anh@congty.vn", "Nguyễn Minh Anh", ["grp-bd-member"]),
        "lead": IdTokenClaims("s-2", "quoc.bao@congty.vn", "Lê Quốc Bảo", ["grp-bd-lead", "grp-bd-member"]),
        "manager": IdTokenClaims("s-3", "giam.doc@congty.vn", "Phạm Giám Đốc", ["grp-bd-manager"]),
        "outsider": IdTokenClaims("s-9", "nguyen.van.a@congty.vn", "Nguyễn Văn A", ["grp-ke-toan"]),
    }

    def __init__(self) -> None:
        self.last_nonce: str | None = None
        self.down = False

    async def authorization_url(self, *, state: str, nonce: str, code_challenge: str, redirect_uri: str) -> str:
        if self.down:
            raise IdentityProviderError("down")
        self.last_nonce = nonce
        return f"https://idp.test/auth?state={state}&nonce={nonce}&code_challenge={code_challenge}"

    async def exchange_code(self, *, code: str, code_verifier: str, redirect_uri: str, nonce: str) -> IdTokenClaims:
        if code == "broken" or nonce != self.last_nonce or not code_verifier:
            raise IdentityProviderError("bad code")
        return self.USERS[code]


# ---------------------------------------------------------------- repositories
class MemUsers:
    def __init__(self) -> None:
        self.by_email: dict[str, User] = {}

    async def upsert_login(self, *, email: str, display_name: str, role: Role, now: datetime) -> tuple[User, bool]:
        key = email.lower()
        old = self.by_email.get(key)
        user = User(old.id if old else uuid7(), email, display_name, role, old.active if old else True)
        self.by_email[key] = user
        return user, old is None

    async def get(self, user_id: UUID) -> User | None:
        return next((u for u in self.by_email.values() if u.id == user_id), None)

    def by_name(self, name: str) -> User:
        return next(u for u in self.by_email.values() if u.display_name == name)


class MemSessions:
    def __init__(self, users: MemUsers) -> None:
        self.users, self.rows = users, {}
        self.touches = 0

    async def create(self, *, id_hash: bytes, user_id: UUID, csrf_secret: bytes, now: datetime) -> None:
        self.rows[id_hash] = {"user_id": user_id, "csrf": csrf_secret, "created": now, "last": now}

    async def get(self, id_hash: bytes) -> SessionRecord | None:
        r = self.rows.get(id_hash)
        if not r:
            return None
        return SessionRecord(id_hash, await self.users.get(r["user_id"]), r["csrf"], r["created"], r["last"])

    async def touch(self, id_hash: bytes, now: datetime) -> None:
        self.touches += 1
        self.rows[id_hash]["last"] = now

    async def delete(self, id_hash: bytes) -> None:
        self.rows.pop(id_hash, None)

    async def delete_idle(self, before: datetime) -> int:
        old = [h for h, r in self.rows.items() if r["last"] < before]
        for h in old:
            del self.rows[h]
        return len(old)


class MemAudit:
    def __init__(self) -> None:
        self.events: list[dict] = []

    async def record(self, **kw) -> None:
        self.events.append(kw)

    def actions(self) -> list[str]:
        return [e["action"] for e in self.events]


class MemJobQueue:
    def __init__(self) -> None:
        self.jobs: dict[UUID, Job] = {}
        self.locked_at: dict[UUID, datetime] = {}
        self.errors: dict[UUID, str] = {}
        self.notified: list[str] = []

    def add(self, job: Job, now: datetime | None = None) -> None:
        self.jobs[job.id] = replace(job, run_after=now or datetime(2000, 1, 1, tzinfo=timezone.utc))
        self.notified.append(job.type.value)

    async def claim(self, worker_id: str, types: list[JobType], now: datetime) -> Job | None:
        ready = [
            j for j in self.jobs.values() if j.status is JobStatus.QUEUED and j.type in types and j.run_after <= now
        ]
        if not ready:
            return None
        job = min(ready, key=lambda j: j.run_after)
        job = replace(job, status=JobStatus.RUNNING, attempts=job.attempts + 1)
        self.jobs[job.id], self.locked_at[job.id] = job, now
        return job

    async def complete(self, job_id: UUID) -> None:
        self.jobs[job_id] = replace(self.jobs[job_id], status=JobStatus.DONE)

    async def retry_later(self, job_id: UUID, error: str, run_after: datetime) -> None:
        self.jobs[job_id] = replace(self.jobs[job_id], status=JobStatus.QUEUED, run_after=run_after)
        self.errors[job_id] = error

    async def fail(self, job_id: UUID, error: str) -> None:
        self.jobs[job_id] = replace(self.jobs[job_id], status=JobStatus.FAILED)
        self.errors[job_id] = error

    async def enqueue(self, job: Job) -> None:
        self.add(job)

    async def enqueue_once(self, job: Job, slot: str) -> bool:
        if any(j.type is job.type and j.payload.get("slot") == slot for j in self.jobs.values()):
            return False
        self.add(replace(job, payload={**job.payload, "slot": slot}))
        return True

    async def queued_stats(self) -> dict[str, tuple[int, float]]:
        out: dict[str, tuple[int, float]] = {}
        for j in self.jobs.values():
            if j.status is JobStatus.QUEUED:
                n, _ = out.get(j.type.value, (0, 0.0))
                out[j.type.value] = (n + 1, 0.0)
        return out

    async def requeue_stale(self, now: datetime) -> int:
        n = 0
        for jid, job in list(self.jobs.items()):
            if job.status is JobStatus.RUNNING and self.locked_at.get(jid, now) < now - TIMEOUTS[job.type]:
                self.jobs[jid] = replace(job, status=JobStatus.QUEUED)
                n += 1
        return n


class MemDocuments:
    def __init__(self, users: MemUsers, jobs: MemJobQueue) -> None:
        self.users, self.jobqueue = users, jobs
        self.docs: dict[UUID, Document] = {}
        self.removed_by: dict[UUID, UUID] = {}
        self.purged_at: dict[UUID, datetime] = {}

    async def find_active_by_hash(self, library_id: UUID, content_hash: bytes) -> Document | None:
        hits = [d for d in self.docs.values() if d.content_hash == content_hash and d.removed_at is None]
        return min(hits, key=lambda d: d.uploaded_at) if hits else None

    async def create_with_job(self, document: Document, job: Job) -> None:
        self.docs[document.id] = document
        self.jobqueue.add(job)

    async def get(self, document_id: UUID) -> Document | None:
        return self.docs.get(document_id)

    async def list(self, library_id, *, name_query, statuses, cursor, limit) -> DocumentPage:
        rows = [d for d in self.docs.values() if d.removed_at is None]
        if name_query:
            rows = [d for d in rows if name_query.lower() in d.file_name.lower()]
        if statuses:
            rows = [d for d in rows if d.status in statuses]
        rows.sort(key=lambda d: (d.uploaded_at, str(d.id)), reverse=True)
        if cursor:
            idx = next((i for i, d in enumerate(rows) if str(d.id) == cursor), -1)
            rows = rows[idx + 1 :]
        page = rows[:limit]
        nxt = str(page[-1].id) if len(rows) > limit else None
        names = {u.id: u.display_name for u in self.users.by_email.values()}
        return DocumentPage([DocumentRow(d, names.get(d.uploaded_by, "?")) for d in page], nxt)

    async def mark_processing_with_job(self, document_id: UUID, job: Job) -> None:
        d = self.docs[document_id]
        if d.status is not DocumentStatus.ERROR:
            raise InvalidState()
        self.docs[document_id] = replace(d, status=DocumentStatus.PROCESSING, error_code=None)
        self.jobqueue.add(job)

    def _set(self, doc_id: UUID, **kw) -> None:
        d = self.docs[doc_id]
        if d.status is DocumentStatus.PROCESSING:
            self.docs[doc_id] = replace(d, **kw)

    async def mark_ready(self, document_id: UUID, page_count: int) -> None:
        self._set(document_id, status=DocumentStatus.READY, page_count=page_count)

    async def mark_no_text(self, document_id: UUID, page_count: int) -> None:
        self._set(document_id, status=DocumentStatus.NO_TEXT, page_count=page_count)

    async def mark_error(self, document_id: UUID, code: ProcessingErrorCode) -> None:
        self._set(document_id, status=DocumentStatus.ERROR, error_code=code)

    async def ready_documents(self, library_id: UUID) -> dict[UUID, str]:
        return {d.id: d.file_name for d in self.docs.values() if d.is_queryable()}

    async def processing_count(self, library_id: UUID) -> int:
        busy = (DocumentStatus.PROCESSING, DocumentStatus.UPLOADING)
        return sum(1 for d in self.docs.values() if d.status in busy and d.removed_at is None)

    async def removed_ids(self, document_ids: list[UUID]) -> set[UUID]:
        return {i for i in document_ids if i in self.docs and self.docs[i].removed_at is not None}

    async def mark_removed_with_job(self, document_id: UUID, removed_by: UUID, now: datetime, job: Job) -> bool:
        d = self.docs.get(document_id)
        if d is None or d.removed_at is not None:
            return False
        self.docs[document_id] = replace(d, status=DocumentStatus.REMOVED, removed_at=now)
        self.removed_by[document_id] = removed_by
        self.jobqueue.add(job)
        return True

    async def mark_purged(self, document_id: UUID, now: datetime) -> None:
        self.purged_at[document_id] = now

    async def count_purge_overdue(self, before: datetime) -> int:
        return sum(
            1
            for d in self.docs.values()
            if d.removed_at is not None and d.removed_at < before and d.id not in self.purged_at
        )

    def seed(self, doc: Document) -> Document:
        self.docs[doc.id] = doc
        return doc


# ---------------------------------------------------------------- storage, embedder, index
class MemStorage:
    def __init__(self) -> None:
        self.objects: dict[str, bytes] = {}
        self.healthy = True

    async def put_file(self, key: str, local_path: str, size_bytes: int) -> None:
        with open(local_path, "rb") as f:
            self.objects[key] = f.read()

    async def download_to(self, key: str, local_path: str) -> None:
        with open(local_path, "wb") as f:
            f.write(self.objects[key])

    async def delete(self, key: str) -> None:
        self.objects.pop(key, None)

    async def size(self, key: str) -> int | None:
        data = self.objects.get(key)
        return None if data is None else len(data)

    async def read_range(self, key: str, start: int, end: int):
        data = self.objects[key][start : end + 1]
        for i in range(0, len(data), 4096):
            yield data[i : i + 4096]

    async def health(self) -> bool:
        return self.healthy


def text_vector(text: str, dim: int = 256) -> list[float]:
    """Deterministic bag-of-words vector: texts sharing words get a high cosine."""
    v = [0.0] * dim
    for word in text.lower().split():
        v[int(hashlib.md5(word.encode()).hexdigest(), 16) % dim] += 1.0  # noqa: S324 — test hashing only
    n = math.sqrt(sum(x * x for x in v)) or 1.0
    return [x / n for x in v]


class FakeEmbedder:
    def __init__(self, dim: int = 256, fail_times: int = 0) -> None:
        self.dimension, self.calls, self.fail_times = dim, 0, fail_times

    async def embed(self, texts: list[str]) -> list[list[float]]:
        self.calls += 1
        if self.fail_times > 0:
            self.fail_times -= 1
            raise RuntimeError("embedder down")
        return [text_vector(t, self.dimension) for t in texts]

    async def health(self) -> bool:
        return True


@dataclass
class MemChunkIndex:
    pages: dict[UUID, list[str]] = field(default_factory=dict)
    chunks: dict[UUID, list[tuple[UUID, Chunk, list[float]]]] = field(default_factory=dict)
    replace_calls: int = 0

    async def replace_document(self, document_id, pages, chunks, vectors) -> None:
        self.replace_calls += 1
        self.pages[document_id] = list(pages)
        self.chunks[document_id] = [(uuid7(), c, v) for c, v in zip(chunks, vectors, strict=True)]

    def _all(self, doc_ids):
        for did in doc_ids:
            for cid, ch, vec in self.chunks.get(did, []):
                yield did, cid, ch, vec

    async def vector_search(self, query_vector, document_ids, k) -> list[Candidate]:
        scored = []
        for did, cid, ch, vec in self._all(document_ids):
            cos = sum(a * b for a, b in zip(query_vector, vec, strict=True))
            scored.append(Candidate(cid, did, ch.page_number, ch.content, ch.char_start, ch.char_end, cosine=cos))
        return sorted(scored, key=lambda c: -c.cosine)[:k]

    async def fts_search(self, query_text, document_ids, k) -> list[Candidate]:
        words = {w for w in query_text.lower().split() if len(w) > 2}
        hits = []
        for did, cid, ch, _ in self._all(document_ids):
            n = sum(1 for w in words if w in ch.content.lower())
            if n:
                hits.append(Candidate(cid, did, ch.page_number, ch.content, ch.char_start, ch.char_end, fts_rank=n))
        return sorted(hits, key=lambda c: -c.fts_rank)[:k]


def copy_file(src: str, dst: str) -> None:
    shutil.copyfile(src, dst)


class MemQa:
    def __init__(self) -> None:
        self.conversations: dict[UUID, Conversation] = {}
        self.questions: dict[UUID, Question] = {}
        self.answers: dict[UUID, dict] = {}  # answer_id → {question_id, status, text, citations, ...}
        self.feedback: dict[UUID, tuple[str, str | None]] = {}

    async def create_conversation(self, conversation: Conversation, now: datetime) -> None:
        self.conversations[conversation.id] = conversation

    async def get_conversation(self, conversation_id: UUID) -> Conversation | None:
        return self.conversations.get(conversation_id)

    async def save_question_and_answer(self, question: Question, answer_id: UUID) -> None:
        self.questions[question.id] = question
        self.answers[answer_id] = {
            "question_id": question.id,
            "status": AnswerStatus.STREAMING,
            "text": "",
            "citations": [],
        }

    def _finish(self, answer_id: UUID, status: AnswerStatus, **kw) -> None:
        a = self.answers[answer_id]
        if a["status"] is AnswerStatus.STREAMING:
            a.update(status=status, **kw)

    async def complete(self, answer_id, *, text, citations, latency_ms, first_token_ms, model_id, now) -> None:
        self._finish(
            answer_id,
            AnswerStatus.COMPLETED,
            text=text,
            citations=list(citations),
            latency_ms=latency_ms,
            first_token_ms=first_token_ms,
            model_id=model_id,
        )

    async def mark_not_found(self, answer_id, reason: NotFoundReason, *, latency_ms, first_token_ms, now) -> None:
        self._finish(answer_id, AnswerStatus.NOT_FOUND, text="", reason=reason, latency_ms=latency_ms)

    async def mark_failed(self, answer_id, *, latency_ms, now) -> None:
        self._finish(answer_id, AnswerStatus.FAILED, latency_ms=latency_ms)

    async def mark_stopped(self, answer_id, *, partial_text, latency_ms, now) -> None:
        self._finish(answer_id, AnswerStatus.STOPPED, text=partial_text, latency_ms=latency_ms)

    async def get_answer(self, answer_id: UUID) -> AnswerRecord | None:
        a = self.answers.get(answer_id)
        if a is None:
            return None
        q = self.questions[a["question_id"]]
        conv = self.conversations[q.conversation_id]
        return AnswerRecord(answer_id, q.id, conv.id, conv.user_id, conv.session_id_hash, a["status"])

    async def turns(self, conversation_id: UUID, limit: int | None = None) -> list[Turn]:
        out = []
        for aid, a in self.answers.items():
            q = self.questions[a["question_id"]]
            if q.conversation_id == conversation_id:
                fb = self.feedback.get(aid)
                out.append(Turn(q.id, q.text, aid, a["text"], a["status"], a["citations"], fb[0] if fb else None))
        return out[-limit:] if limit else out

    async def save_feedback(self, answer_id, value, reason, now) -> bool:
        if answer_id in self.feedback:
            return False
        self.feedback[answer_id] = (value, reason)
        return True


class MemMetrics:
    def __init__(self) -> None:
        self.days: dict = {}
        self.wau: dict = {}
        self.accounts = 30
        self.computed: dict = {}

    async def compute_day(self, day):
        return self.computed.get(day, {"questions": 0.0})

    async def save_day(self, day, values) -> None:
        self.days[day] = dict(values)

    async def daily(self, since):
        return {d: v for d, v in self.days.items() if d >= since}

    async def weekly_active_users(self, since):
        return {d: n for d, n in self.wau.items() if d >= since}

    async def active_accounts(self) -> int:
        return self.accounts

    async def ensure_partitions(self, today, months_ahead, keep_months):
        return [f"created ahead {months_ahead}"]


class MemEvaluations:
    def __init__(self) -> None:
        self.runs: dict[UUID, dict] = {}

    async def create_run(self, run_id, name, cases: list[TestCase], created_by) -> None:
        self.runs[run_id] = {
            "status": "queued",
            "cases": [(uuid7(), c) for c in cases],
            "results": {},
            "by": created_by,
        }

    async def get_run(self, run_id) -> EvaluationRun | None:
        r = self.runs.get(run_id)
        if not r:
            return None
        return EvaluationRun(run_id, r["status"], len(r["results"]), len(r["cases"]), r["by"])

    async def cases(self, run_id):
        return list(self.runs[run_id]["cases"])

    async def done_case_ids(self, run_id):
        return set(self.runs[run_id]["results"])

    async def save_result(self, run_id, case_id, result: EvaluationResult) -> None:
        self.runs[run_id]["results"][case_id] = result

    async def set_status(self, run_id, status, now) -> None:
        self.runs[run_id]["status"] = status

    async def results(self, run_id):
        r = self.runs[run_id]
        return [r["results"].get(cid, EvaluationResult(c, "", "NOT_RUN", [], 0)) for cid, c in r["cases"]]


# ---------------------------------------------------------------- container
def make_settings(**overrides) -> Settings:
    base = {
        "app_secret": "test-secret-0123456789",
        "cookie_secure": True,
        "log_level": "WARNING",
        "max_upload_mb": 1,
        "environment": "test",
        "llm_first_token_timeout_s": 0.5,
        "llm_total_timeout_s": 2,
        "llm_queue_wait_s": 0.2,
    }
    base.update(overrides)
    return Settings(**base)


def make_container(**setting_overrides) -> tuple[Container, SimpleNamespace]:
    settings = make_settings(**setting_overrides)
    clock = FixedClock()
    users = MemUsers()
    f = SimpleNamespace(
        clock=clock,
        idp=FakeIdp(),
        users=users,
        sessions=MemSessions(users),
        audit=MemAudit(),
        jobs=MemJobQueue(),
        storage=MemStorage(),
        events=MemoryEventWriter(),
        qa_repo=MemQa(),
        index=MemChunkIndex(),
        embedder=FakeEmbedder(),
        llm=FakeAnswerGenerator(),
        stop_bus=LocalStopBus(),
        metrics_repo=MemMetrics(),
        eval_repo=MemEvaluations(),
    )
    f.documents = MemDocuments(users, f.jobs)
    analytics = AnalyticsService(
        writer=f.events,
        hmac_key=settings.analytics_hmac_key.encode(),
        app_version=settings.app_version,
        clock=clock,
        rate_limiter=RateLimiter(capacity=settings.rate_events_per_min, per_seconds=60),
    )
    f.analytics = analytics
    policy = UploadPolicy(settings.max_upload_mb)
    access = AccessService(
        idp=f.idp,
        users=users,
        sessions=f.sessions,
        audit=f.audit,
        role_groups=role_groups(settings),
        idle_hours=settings.session_idle_hours,
        redirect_uri=settings.oidc_redirect_uri,
        clock=clock,
        analytics=analytics,
    )
    docs = DocumentService(
        documents=f.documents,
        storage=f.storage,
        audit=f.audit,
        policy=policy,
        library_id=settings.library_id,
        clock=clock,
        analytics=analytics,
        upload_limiter=RateLimiter(capacity=settings.rate_uploads_per_hour, per_seconds=3600),
        index=f.index,
    )
    f.gate = make_gate(settings)
    qa = QuestionAnsweringService(
        qa=f.qa_repo,
        documents=f.documents,
        retrieval=RetrievalService(embedder=f.embedder, index=f.index, config=retrieval_config(settings)),
        llm=ResilientGenerator(
            f.llm,
            first_token_timeout_s=settings.llm_first_token_timeout_s,
            total_timeout_s=settings.llm_total_timeout_s,
            retry_backoff_s=0.01,
        ),
        gate=f.gate,
        analytics=analytics,
        stop_bus=f.stop_bus,
        rate_limiter=RateLimiter(capacity=settings.rate_questions_per_min, per_seconds=60),
        library_id=settings.library_id,
        clock=clock,
        config=qa_config(settings),
    )
    f.qa = qa

    async def ok() -> bool:
        return True

    container = Container(
        settings=settings,
        access=access,
        documents=docs,
        upload_policy=policy,
        clock=clock,
        qa=qa,
        analytics=analytics,
        metrics=MetricsService(repo=f.metrics_repo, clock=clock),
        evaluation=EvaluationService(repo=f.eval_repo, jobs=f.jobs, qa=qa, audit=f.audit, clock=clock),
        health_checks={"database": ok, "storage": f.storage.health},
    )
    return container, f


async def seed_ready_document(f, file_name: str, pages: list[str], uploader: User | None = None) -> Document:
    """A READY document whose chunks are indexed with the fake embedder (no worker needed)."""
    from chatdocs.domain.documents.chunking import chunk_document
    from chatdocs.platform.config import DEFAULT_LIBRARY_ID

    owner = uploader or next(iter(f.users.by_email.values()), None)
    if owner is None:
        owner, _ = await f.users.upsert_login(
            email="seed@congty.vn", display_name="Seed", role=Role.BD_MEMBER, now=f.clock.now()
        )
    doc_id = uuid7()
    doc = f.documents.seed(
        Document(
            id=doc_id,
            library_id=DEFAULT_LIBRARY_ID,
            file_name=file_name,
            size_bytes=1000,
            content_hash=hashlib.sha256(file_name.encode()).digest(),
            status=DocumentStatus.READY,
            storage_key=Document.storage_key_for(DEFAULT_LIBRARY_ID, doc_id),
            uploaded_by=owner.id,
            uploaded_at=f.clock.now(),
            page_count=len(pages),
        )
    )
    f.storage.objects[doc.storage_key] = b"%PDF-1.7 " + file_name.encode() + b" " * 2000
    chunks = chunk_document(pages, 500, 80)
    await f.index.replace_document(doc_id, pages, chunks, await f.embedder.embed([c.content for c in chunks]))
    return doc
