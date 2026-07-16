import uuid
from pathlib import Path

from app.application.ports.audit import AuditPort
from app.application.ports.resume_repository import ResumeRepositoryPort
from app.application.ports.storage import FileStoragePort
from app.application.services.resume_classifier import ResumeClassifier
from app.domain.enums import AuditAction, AuditActor, LABEL_TO_CATEGORY, StorageCategory
from app.infrastructure.db.models import MasterResume, ResumeVersion
from app.infrastructure.logging.setup import get_logger
from app.infrastructure.parsers.resume_parser import ResumeParser
from app.infrastructure.repositories.resume_repository import compute_content_hash

logger = get_logger(__name__)


class ResumeService:
    def __init__(
        self,
        resume_repo: ResumeRepositoryPort,
        storage: FileStoragePort,
        audit: AuditPort | None = None,
    ):
        self._repo = resume_repo
        self._storage = storage
        self._audit = audit
        self._parser = ResumeParser()
        self._classifier = ResumeClassifier()

    def list_labels(self) -> list[str]:
        from app.domain.enums import ResumeLabel

        return [label.value for label in ResumeLabel]

    def list_master_resumes(self, user_id: uuid.UUID) -> list[MasterResume]:
        return self._repo.list_masters(user_id)

    def get_master_resume(self, user_id: uuid.UUID, resume_id: uuid.UUID) -> MasterResume:
        resume = self._repo.get_master_by_id(resume_id, user_id)
        if not resume:
            raise ValueError("Resume not found")
        return resume

    def list_versions(self, user_id: uuid.UUID, resume_id: uuid.UUID) -> list[ResumeVersion]:
        resume = self.get_master_resume(user_id, resume_id)
        return self._repo.list_versions(resume.id)

    async def upload_master_resume(
        self,
        user_id: uuid.UUID,
        label: str,
        file_content: bytes,
        filename: str,
    ) -> MasterResume:
        label = self._classifier.validate_label(label)
        category = LABEL_TO_CATEGORY[label]
        content_hash = compute_content_hash(file_content)

        ext = Path(filename).suffix.lower()
        if ext not in ResumeParser.SUPPORTED_EXTENSIONS:
            raise ValueError(f"Unsupported file type: {ext}")

        existing = self._repo.get_master_by_label(user_id, label)
        resume_id = existing.id if existing else uuid.uuid4()
        storage_name = f"{resume_id}{ext}"
        file_path = self._storage.save(
            StorageCategory.MASTER_RESUME,
            storage_name,
            file_content,
            user_id=user_id,
        )

        parsed = self._parser.parse_file(file_path)
        classification = self._classifier.classify(label, parsed)

        if existing:
            self._archive_version(existing)
            existing.file_path = str(file_path)
            existing.original_filename = filename
            existing.parsed_content = parsed
            existing.role_families = classification["role_families"]
            existing.classification = classification
            existing.content_hash = content_hash
            existing.category = category.value
            existing.version += 1
            existing.is_active = True
            resume = self._repo.update_master(existing)
            action = "resume_replaced"
        else:
            resume = MasterResume(
                id=resume_id,
                user_id=user_id,
                label=label,
                category=category.value,
                file_path=str(file_path),
                original_filename=filename,
                parsed_content=parsed,
                role_families=classification["role_families"],
                classification=classification,
                content_hash=content_hash,
            )
            resume = self._repo.create_master(resume)
            action = "resume_uploaded"

        if self._audit:
            self._audit.record(
                action=AuditAction.SYSTEM_EVENT,
                entity_type="master_resume",
                entity_id=resume.id,
                actor=AuditActor.USER,
                details={
                    "event": action,
                    "label": label,
                    "category": category.value,
                    "version": resume.version,
                    "filename": filename,
                },
            )

        logger.info(
            "master_resume_saved",
            resume_id=str(resume.id),
            label=label,
            version=resume.version,
        )
        return resume

    def deactivate(self, user_id: uuid.UUID, resume_id: uuid.UUID) -> MasterResume:
        resume = self.get_master_resume(user_id, resume_id)
        resume.is_active = False
        resume = self._repo.update_master(resume)
        if self._audit:
            self._audit.record(
                action=AuditAction.SYSTEM_EVENT,
                entity_type="master_resume",
                entity_id=resume.id,
                actor=AuditActor.USER,
                details={"event": "resume_deactivated", "label": resume.label},
            )
        return resume

    def _archive_version(self, resume: MasterResume) -> None:
        version = ResumeVersion(
            master_resume_id=resume.id,
            version_number=resume.version,
            file_path=resume.file_path,
            original_filename=resume.original_filename,
            parsed_content=resume.parsed_content,
            content_hash=resume.content_hash,
            classification=resume.classification,
        )
        self._repo.create_version(version)
