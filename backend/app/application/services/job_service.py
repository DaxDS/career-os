import uuid
from datetime import datetime, timezone
from typing import Any, Literal

from app.application.ports.audit import AuditPort
from app.application.ports.job_repository import JobRepositoryPort
from app.application.ports.classifier import JobClassifierPort
from app.application.services.job_classifier import RuleBasedJobClassifier
from app.application.services.job_source_seeder import JobSourceSeeder
from app.domain.enums import AuditAction, AuditActor, JobSourcePreset, JobSourceType, JobStatus
from app.domain.job_source_presets import (
    JOB_SOURCE_PRESET_DEFINITIONS,
    get_preset_definition,
    is_reserved_source_name,
)
from app.infrastructure.db.models import JobPosting, JobSource
from app.infrastructure.jobs.dedup import (
    compute_dedup_key,
    compute_description_hash,
    normalize_url,
)
from app.infrastructure.logging.setup import get_logger

logger = get_logger(__name__)

MIN_JOB_DESCRIPTION_CHARS = 80

ImportStatus = Literal["created", "duplicate"]


class JobService:
    def __init__(
        self,
        job_repo: JobRepositoryPort,
        audit: AuditPort | None = None,
        classifier: JobClassifierPort | None = None,
    ):
        self._repo = job_repo
        self._audit = audit
        self._classifier = classifier or RuleBasedJobClassifier()
        self._seeder = JobSourceSeeder(job_repo)

    def list_preset_definitions(self) -> list[dict[str, Any]]:
        return [
            {
                "preset_key": definition.preset_key.value,
                "name": definition.name,
                "source_type": definition.source_type.value,
                "connector_key": definition.connector_key,
                "config": definition.config,
            }
            for definition in JOB_SOURCE_PRESET_DEFINITIONS.values()
        ]

    def seed_builtin_sources(self, user_id: uuid.UUID) -> list[JobSource]:
        return self._seeder.seed_builtin_sources(user_id)

    def list_sources(self, user_id: uuid.UUID) -> list[JobSource]:
        self.seed_builtin_sources(user_id)
        return self._repo.list_sources(user_id)

    def get_source_by_preset(self, user_id: uuid.UUID, preset_key: str) -> JobSource:
        self.seed_builtin_sources(user_id)
        source = self._repo.get_source_by_preset_key(user_id, preset_key)
        if not source:
            raise ValueError(f"Built-in source not found for preset_key: {preset_key}")
        return source

    def create_source(
        self,
        user_id: uuid.UUID,
        name: str,
        source_type: str,
        config: dict | None = None,
    ) -> JobSource:
        if is_reserved_source_name(name):
            raise ValueError(
                f"Source name '{name}' is reserved for a built-in preset. "
                "Use the seeded preset instead."
            )
        source_type = self._validate_source_type(source_type)
        existing = self._repo.get_source_by_name(user_id, name)
        if existing:
            raise ValueError(f"Source '{name}' already exists")
        source = JobSource(
            user_id=user_id,
            name=name,
            source_type=source_type,
            config=config or {},
            is_builtin=False,
        )
        source = self._repo.create_source(source)
        self._audit_event("job_source_created", source.id, {"name": name, "source_type": source_type})
        return source

    def update_source(
        self,
        user_id: uuid.UUID,
        source_id: uuid.UUID,
        *,
        name: str | None = None,
        config: dict | None = None,
        is_active: bool | None = None,
    ) -> JobSource:
        source = self._get_source(user_id, source_id)
        if source.is_builtin:
            if name is not None and name != source.name:
                raise ValueError("Built-in source names cannot be changed")
        elif name is not None and name != source.name:
            if is_reserved_source_name(name):
                raise ValueError(f"Source name '{name}' is reserved for a built-in preset")
            conflict = self._repo.get_source_by_name(user_id, name)
            if conflict and conflict.id != source.id:
                raise ValueError(f"Source '{name}' already exists")
            source.name = name
        if config is not None:
            source.config = {**source.config, **config}
        if is_active is not None:
            source.is_active = is_active
        source = self._repo.update_source(source)
        self._audit_event("job_source_updated", source.id, {"name": source.name})
        return source

    def list_jobs(
        self,
        user_id: uuid.UUID,
        *,
        province: str | None = None,
        role_family: str | None = None,
        status: str | None = None,
        source_id: uuid.UUID | None = None,
    ) -> list[JobPosting]:
        return self._repo.list_postings(
            user_id,
            province=province,
            role_family=role_family,
            status=status,
            source_id=source_id,
        )

    def get_job(self, user_id: uuid.UUID, job_id: uuid.UUID) -> JobPosting:
        job = self._repo.get_posting_by_id(job_id, user_id)
        if not job:
            raise ValueError("Job not found")
        return job

    def import_jobs(
        self,
        user_id: uuid.UUID,
        jobs: list[dict[str, Any]],
        source_id: uuid.UUID | None = None,
        source_preset_key: str | None = None,
    ) -> list[dict[str, Any]]:
        source = self._resolve_source(user_id, source_id, source_preset_key)
        results: list[dict[str, Any]] = []
        now = datetime.now(timezone.utc)

        for payload in jobs:
            result = self._import_single(user_id, source, payload)
            results.append(result)

        if source:
            self._repo.touch_source_sync(source.id, now)

        created = sum(1 for r in results if r["import_status"] == "created")
        duplicates = sum(1 for r in results if r["import_status"] == "duplicate")
        logger.info(
            "jobs_imported",
            user_id=str(user_id),
            source_id=str(source.id) if source else None,
            preset_key=source.preset_key if source else None,
            created=created,
            duplicates=duplicates,
        )
        return results

    def archive_job(self, user_id: uuid.UUID, job_id: uuid.UUID) -> JobPosting:
        job = self.get_job(user_id, job_id)
        job.status = JobStatus.ARCHIVED.value
        job = self._repo.update_posting(job)
        self._audit_event("job_archived", job.id, {"title": job.title, "company": job.company})
        return job

    def update_job(
        self,
        user_id: uuid.UUID,
        job_id: uuid.UUID,
        *,
        status: str | None = None,
        role_family: str | None = None,
    ) -> JobPosting:
        job = self.get_job(user_id, job_id)
        if status is not None:
            self._validate_status(status)
            job.status = status
        if role_family is not None:
            job.role_family = role_family
        job = self._repo.update_posting(job)
        return job

    def enrich_description(self, user_id: uuid.UUID, job_id: uuid.UUID) -> JobPosting:
        """Re-fetch posting text when live import returned an empty description."""
        job = self.get_job(user_id, job_id)
        if len((job.description or "").strip()) >= MIN_JOB_DESCRIPTION_CHARS:
            return job

        external_id = job.external_id
        raw = job.raw_payload if isinstance(job.raw_payload, dict) else {}
        if not external_id and raw:
            external_id = raw.get("job_id") or raw.get("jk")

        source = self._repo.get_source_by_id(job.source_id, user_id) if job.source_id else None
        preset_key = source.preset_key if source else raw.get("source")

        description = ""
        if external_id and preset_key == "job_bank_canada":
            from app.infrastructure.jobs.search.live_adapters import JobBankCanadaSearchAdapter

            description = JobBankCanadaSearchAdapter().fetch_description(str(external_id))

        if len(description.strip()) < MIN_JOB_DESCRIPTION_CHARS:
            return job

        job.description = description.strip()
        job.description_hash = compute_description_hash(job.description)
        classification = self._classifier.classify(
            job.title,
            job.description,
            job.remote_type,
            company=job.company,
            location=f"{job.location_city}, {job.location_province}".strip(", "),
        )
        role_family = classification.get("role_family") or job.role_family or "general"
        if role_family == "other":
            role_family = "general"
        job.classification = classification
        job.role_family = role_family
        job = self._repo.update_posting(job)
        logger.info(
            "job_description_enriched",
            job_id=str(job.id),
            description_length=len(job.description),
            preset_key=preset_key,
        )
        return job

    def has_scorable_description(self, job: JobPosting) -> bool:
        return len((job.description or "").strip()) >= MIN_JOB_DESCRIPTION_CHARS

    def _import_single(
        self,
        user_id: uuid.UUID,
        source: JobSource | None,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        title = (payload.get("title") or "").strip()
        company = (payload.get("company") or "").strip()
        if not title or not company:
            raise ValueError("Each job requires title and company")

        description = payload.get("description") or ""
        province = (payload.get("location_province") or "").strip().upper()
        city = (payload.get("location_city") or "").strip()
        source_url = payload.get("source_url") or ""
        external_id = payload.get("external_id")
        normalized = normalize_url(source_url)
        desc_hash = compute_description_hash(description)
        dedup_key = compute_dedup_key(company, title, province, city)

        existing, match_reason = self._find_duplicate(
            user_id,
            source,
            external_id,
            normalized,
            dedup_key,
            desc_hash,
        )
        if existing:
            self._audit_event(
                "job_dedup",
                existing.id,
                {
                    "match_reason": match_reason,
                    "title": title,
                    "company": company,
                    "incoming_external_id": external_id,
                },
            )
            return {"import_status": "duplicate", "match_reason": match_reason, "job": existing}

        remote_type = payload.get("remote_type")
        classification = self._classifier.classify(
            title,
            description,
            remote_type,
            company=company,
            location=f"{city}, {province}".strip(", "),
        )
        role_family = classification.get("role_family") or "general"
        if role_family == "other":
            role_family = "general"

        posting = JobPosting(
            user_id=user_id,
            source_id=source.id if source else None,
            external_id=external_id,
            source_url=source_url,
            normalized_url=normalized,
            title=title,
            company=company,
            location_city=city,
            location_province=province,
            remote_type=remote_type or classification.get("remote_type"),
            description=description,
            description_hash=desc_hash,
            dedup_key=dedup_key,
            role_family=role_family,
            classification=classification,
            raw_payload=payload.get("raw_payload") or payload,
            status=JobStatus.NEW.value,
            date_posted=payload.get("date_posted"),
            salary_min_cad=payload.get("salary_min_cad"),
            salary_max_cad=payload.get("salary_max_cad"),
        )
        posting = self._repo.create_posting(posting)
        self._audit_event(
            "job_imported",
            posting.id,
            {
                "title": title,
                "company": company,
                "role_family": role_family,
                "source": source.name if source else None,
                "preset_key": source.preset_key if source else None,
            },
        )
        return {"import_status": "created", "match_reason": None, "job": posting}

    def _find_duplicate(
        self,
        user_id: uuid.UUID,
        source: JobSource | None,
        external_id: str | None,
        normalized_url: str,
        dedup_key: str,
        description_hash: str,
    ) -> tuple[JobPosting | None, str | None]:
        if source and external_id:
            found = self._repo.find_by_external_id(user_id, source.id, external_id)
            if found:
                return found, "external_id"

        if normalized_url:
            found = self._repo.find_by_normalized_url(user_id, normalized_url)
            if found:
                return found, "source_url"

        found = self._repo.find_by_dedup_key(user_id, dedup_key)
        if found:
            return found, "dedup_key"

        found = self._repo.find_by_description_hash(user_id, description_hash)
        if found:
            return found, "description_hash"

        return None, None

    def _resolve_source(
        self,
        user_id: uuid.UUID,
        source_id: uuid.UUID | None,
        source_preset_key: str | None,
    ) -> JobSource:
        self.seed_builtin_sources(user_id)

        if source_id:
            return self._get_source(user_id, source_id)

        if source_preset_key:
            get_preset_definition(source_preset_key)
            return self.get_source_by_preset(user_id, source_preset_key)

        return self.get_source_by_preset(user_id, JobSourcePreset.MANUAL_URL_IMPORT.value)

    def _get_source(self, user_id: uuid.UUID, source_id: uuid.UUID) -> JobSource:
        source = self._repo.get_source_by_id(source_id, user_id)
        if not source:
            raise ValueError("Job source not found")
        return source

    @staticmethod
    def _validate_source_type(source_type: str) -> str:
        valid = {t.value for t in JobSourceType}
        if source_type not in valid:
            raise ValueError(f"Invalid source_type. Must be one of: {sorted(valid)}")
        return source_type

    @staticmethod
    def _validate_status(status: str) -> str:
        valid = {s.value for s in JobStatus}
        if status not in valid:
            raise ValueError(f"Invalid status. Must be one of: {sorted(valid)}")
        return status

    def _audit_event(self, event: str, entity_id: uuid.UUID, details: dict) -> None:
        if not self._audit:
            return
        self._audit.record(
            action=AuditAction.SYSTEM_EVENT,
            entity_type="job",
            entity_id=entity_id,
            actor=AuditActor.USER,
            details={"event": event, **details},
        )

