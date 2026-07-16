import uuid

from sqlalchemy.orm import Session, joinedload

from app.application.ports.user_repository import UserRepositoryPort
from app.infrastructure.db.models import User, UserProfile


class SQLAlchemyUserRepository(UserRepositoryPort):
    def __init__(self, db: Session):
        self._db = db

    def count_users(self) -> int:
        return self._db.query(User).count()

    def get_by_id(self, user_id: uuid.UUID) -> User | None:
        return (
            self._db.query(User)
            .options(joinedload(User.profile))
            .filter(User.id == user_id)
            .first()
        )

    def get_by_email(self, email: str) -> User | None:
        return (
            self._db.query(User)
            .options(joinedload(User.profile))
            .filter(User.email == email)
            .first()
        )

    def create_user(self, user: User) -> User:
        self._db.add(user)
        self._db.commit()
        self._db.refresh(user)
        return user

    def get_profile(self, user_id: uuid.UUID) -> UserProfile | None:
        return self._db.query(UserProfile).filter(UserProfile.user_id == user_id).first()

    def create_profile(self, profile: UserProfile) -> UserProfile:
        self._db.add(profile)
        self._db.commit()
        self._db.refresh(profile)
        return profile

    def update_profile(self, profile: UserProfile) -> UserProfile:
        self._db.commit()
        self._db.refresh(profile)
        return profile
