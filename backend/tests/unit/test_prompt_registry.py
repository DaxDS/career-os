import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.config import Settings, resolve_paths
from app.domain.enums import PromptName
from app.infrastructure.db.base import Base
from app.infrastructure.prompts.registry import PromptRegistry


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


@pytest.fixture
def registry(db_session, tmp_path):
    prompts_dir = tmp_path / "prompts"
    prompts_dir.mkdir()
    manifest = """
prompts:
  resume_selection:
    file: resume_selection.md
    capability: resume_selection
"""
    (prompts_dir / "manifest.yaml").write_text(manifest)
    (prompts_dir / "resume_selection.md").write_text("# Resume Selection\n{{job_title}}")
    settings = Settings(storage_path=tmp_path / "storage", prompts_path=prompts_dir)
    return PromptRegistry(settings, db_session)


def test_prompts_root(registry, tmp_path):
    root = registry.get_prompts_root()
    assert root == tmp_path / "prompts"


def test_get_prompt_path(registry):
    path = registry.get_prompt_path(PromptName.RESUME_SELECTION)
    assert path.name == "resume_selection.md"
    assert path.exists()


def test_list_registered_prompts(registry):
    prompts = registry.list_registered_prompts()
    assert len(prompts) == 1
    assert prompts[0]["name"] == "resume_selection"
    assert prompts[0]["file_exists"] is True
    assert prompts[0]["active_version"] is None


def test_register_version(registry):
    content = "# Resume Selection\n{{job_title}}"
    path = str(registry.get_prompt_path("resume_selection"))
    content_hash = PromptRegistry.compute_hash(content)
    version = registry.register_version("resume_selection", content, path, content_hash)
    assert version["version"] == 1
    assert version["is_active"] is True

    active = registry.get_active_version("resume_selection")
    assert active is not None
    assert active["version"] == 1


def test_register_version_idempotent(registry):
    content = "# Resume Selection\n{{job_title}}"
    path = str(registry.get_prompt_path("resume_selection"))
    content_hash = PromptRegistry.compute_hash(content)
    v1 = registry.register_version("resume_selection", content, path, content_hash)
    v2 = registry.register_version("resume_selection", content, path, content_hash)
    assert v1["version"] == v2["version"]


def test_register_new_version_deactivates_old(registry):
    path = str(registry.get_prompt_path("resume_selection"))
    registry.register_version("resume_selection", "v1 content", path, PromptRegistry.compute_hash("v1 content"))
    v2 = registry.register_version("resume_selection", "v2 content", path, PromptRegistry.compute_hash("v2 content"))
    assert v2["version"] == 2


def test_project_prompts_manifest_exists():
    from pathlib import Path

    project_root = Path(__file__).resolve().parents[3]
    settings = resolve_paths(Settings(), project_root)
    manifest_path = settings.prompts_path / "manifest.yaml"
    assert manifest_path.exists(), "prompts/manifest.yaml must exist at project root"
    prompts_dir = settings.prompts_path
    for filename in [
        "resume_selection.md",
        "resume_tailoring.md",
        "cover_letter.md",
        "email_generation.md",
        "ats_analysis.md",
        "job_scoring.md",
        "job_classification.md",
        "immigration_scoring.md",
    ]:
        assert (prompts_dir / filename).exists(), f"Missing prompt file: {filename}"
