import uuid
from abc import ABC, abstractmethod

from app.infrastructure.db.models import User, UserProfile


class UserRepositoryPort(ABC):
    @abstractmethod
    def count_users(self) -> int: ...

    @abstractmethod
    def get_by_id(self, user_id: uuid.UUID) -> User | None: ...

    @abstractmethod
    def get_by_email(self, email: str) -> User | None: ...

    @abstractmethod
    def create_user(self, user: User) -> User: ...

    @abstractmethod
    def get_profile(self, user_id: uuid.UUID) -> UserProfile | None: ...

    @abstractmethod
    def create_profile(self, profile: UserProfile) -> UserProfile: ...

    @abstractmethod
    def update_profile(self, profile: UserProfile) -> UserProfile: ...
