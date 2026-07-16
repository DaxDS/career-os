import uuid

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.application.services.user_service import AuthService, ProfileService
from app.config import Settings
from app.domain.enums import JobCategory, RemotePreference, WorkAuthorization
from app.infrastructure.audit.sqlalchemy_audit import SQLAlchemyAuditLog
from app.infrastructure.auth.jwt import create_access_token, hash_password, verify_password
from app.infrastructure.db import models  # noqa: F401
from app.infrastructure.db.base import Base
from app.infrastructure.db.models import User, UserProfile
from app.infrastructure.repositories.user_repository import SQLAlchemyUserRepository


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


@pytest.fixture
def settings():
    return Settings(single_user_mode=True, default_user_email="test@example.com")


@pytest.fixture
def user_repo(db_session):
    return SQLAlchemyUserRepository(db_session)


@pytest.fixture
def auth_service(user_repo, settings, db_session):
    return AuthService(user_repo, settings, SQLAlchemyAuditLog(db_session))


@pytest.fixture
def profile_service(user_repo, db_session):
    return ProfileService(user_repo, SQLAlchemyAuditLog(db_session))


def test_hash_and_verify_password():
    hashed = hash_password("secretpassword")
    assert verify_password("secretpassword", hashed)
    assert not verify_password("wrong", hashed)


def test_register_creates_user_and_profile(auth_service, user_repo):
    user, token = auth_service.register("user@example.com", "password123")
    assert user.email == "user@example.com"
    assert token
    profile = user_repo.get_profile(user.id)
    assert profile is not None
    assert profile.legal_name == "user"


def test_single_user_mode_blocks_second_registration(auth_service):
    auth_service.register("first@example.com", "password123")
    with pytest.raises(ValueError, match="Single-user mode"):
        auth_service.register("second@example.com", "password456")


def test_login_success(auth_service):
    auth_service.register("user@example.com", "password123")
    user, token = auth_service.login("user@example.com", "password123")
    assert user.email == "user@example.com"
    assert token


def test_login_invalid_credentials(auth_service):
    auth_service.register("user@example.com", "password123")
    with pytest.raises(ValueError, match="Invalid credentials"):
        auth_service.login("user@example.com", "wrongpassword")


def test_bootstrap_single_user(auth_service, user_repo, settings):
    user = auth_service.bootstrap_single_user()
    assert user is not None
    assert user.email == settings.default_user_email
    assert user_repo.count_users() == 1
    assert auth_service.bootstrap_single_user() is None


def test_update_profile(profile_service, auth_service):
    user, _ = auth_service.register("user@example.com", "password123")
    updated = profile_service.update_profile(
        user.id,
        {
            "legal_name": "Jane Doe",
            "location_city": "Charlottetown",
            "location_province": "PE",
            "work_authorization": WorkAuthorization.PGWP,
            "remote_preference": RemotePreference.HYBRID,
            "preferred_provinces": ["PE", "ON"],
            "preferred_job_categories": [JobCategory.PRODUCTION, JobCategory.IT],
            "skills": ["Python", "Manufacturing"],
            "salary_min_cad": 50000,
            "salary_max_cad": 80000,
            "languages": {"english": "fluent", "french": "basic"},
            "immigration_goals": {
                "express_entry": True,
                "pei_pnp": True,
                "target_noc_codes": ["22301", "21232"],
            },
        },
    )
    assert updated.legal_name == "Jane Doe"
    assert updated.location_city == "Charlottetown"
    assert updated.work_authorization == WorkAuthorization.PGWP.value
    assert updated.preferred_provinces == ["PE", "ON"]
    assert updated.preferred_job_categories == ["production", "it"]
    assert updated.salary_min_cad == 50000
    assert updated.salary_max_cad == 80000
    assert updated.languages == {"english": "fluent", "french": "basic"}
    assert updated.immigration_goals["pei_pnp"] is True


def test_create_access_token(settings):
    user_id = uuid.uuid4()
    token = create_access_token(user_id, settings)
    assert isinstance(token, str)
    assert len(token) > 20
