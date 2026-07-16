from pathlib import Path

from app.cli import EXPECTED_MIGRATION_HEAD


def test_migration_chain_is_linear():
    versions_dir = Path(__file__).resolve().parents[2] / "alembic" / "versions"
    revisions: dict[str, str | None] = {}
    for path in versions_dir.glob("*.py"):
        text = path.read_text(encoding="utf-8")
        rev = _extract_assignment(text, "revision")
        down = _extract_assignment(text, "down_revision")
        if rev:
            revisions[rev] = down

    referenced_as_parent = {down for down in revisions.values() if down}
    heads = [rev for rev in revisions if rev not in referenced_as_parent]
    assert heads == [EXPECTED_MIGRATION_HEAD]

    roots = [rev for rev, down in revisions.items() if down is None]
    assert roots == ["001_layer0_foundation"]

    # Walk from head to root
    current: str | None = EXPECTED_MIGRATION_HEAD
    visited: set[str] = set()
    while current:
        assert current not in visited
        visited.add(current)
        current = revisions[current]
    assert len(visited) == len(revisions)


def _extract_assignment(text: str, name: str) -> str | None:
    for line in text.splitlines():
        if line.strip().startswith(f"{name}:") or line.strip().startswith(f"{name} ="):
            _, value = line.split("=", 1)
            value = value.strip().strip('"').strip("'")
            if value in {"None", "null"}:
                return None
            return value
    return None
