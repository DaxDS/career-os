"""File storage port — abstracts blob persistence for all document types."""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import BinaryIO
from uuid import UUID

from app.domain.enums import StorageCategory


class FileStoragePort(ABC):
    @abstractmethod
    def resolve_directory(
        self,
        category: StorageCategory,
        user_id: UUID | None = None,
        job_id: UUID | None = None,
        application_id: UUID | None = None,
    ) -> Path:
        """Return the directory for a storage category. Creates it if needed."""

    @abstractmethod
    def save(
        self,
        category: StorageCategory,
        filename: str,
        content: bytes,
        user_id: UUID | None = None,
        job_id: UUID | None = None,
        application_id: UUID | None = None,
    ) -> Path:
        """Save bytes and return the absolute file path."""

    @abstractmethod
    def save_text(
        self,
        category: StorageCategory,
        filename: str,
        content: str,
        user_id: UUID | None = None,
        job_id: UUID | None = None,
        application_id: UUID | None = None,
    ) -> Path: ...

    @abstractmethod
    def read(self, path: Path) -> bytes: ...

    @abstractmethod
    def read_text(self, path: Path, encoding: str = "utf-8") -> str: ...

    @abstractmethod
    def exists(self, path: Path) -> bool: ...

    @abstractmethod
    def delete(self, path: Path) -> None: ...

    @abstractmethod
    def open(self, path: Path) -> BinaryIO: ...
