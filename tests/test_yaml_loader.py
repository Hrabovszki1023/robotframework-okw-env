"""Tests for YAML component loader."""

import tempfile
from pathlib import Path

import pytest

from okw_env.yaml_loader import load_component


@pytest.fixture
def tmp_dir():
    with tempfile.TemporaryDirectory() as d:
        yield Path(d)


def test_load_component():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False, encoding="utf-8") as f:
        f.write("PostgresDB:\n  image: postgres\n  version: '17'\n  port: 5432\n")
        f.flush()
        data = load_component(f.name)

    assert "PostgresDB" in data
    assert data["PostgresDB"]["image"] == "postgres"
    assert data["PostgresDB"]["version"] == "17"
    assert data["PostgresDB"]["port"] == 5432


def test_load_component_with_env():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False, encoding="utf-8") as f:
        f.write("Redis:\n  image: redis\n  env:\n    REDIS_PASSWORD: secret\n")
        f.flush()
        data = load_component(f.name)

    assert data["Redis"]["env"]["REDIS_PASSWORD"] == "secret"


def test_load_component_file_not_found():
    with pytest.raises(FileNotFoundError):
        load_component("/nonexistent/path.yaml")


def test_load_component_path_object():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False, encoding="utf-8") as f:
        f.write("Test:\n  image: test\n")
        f.flush()
        data = load_component(Path(f.name))

    assert "Test" in data


def test_extends_basic(tmp_dir):
    (tmp_dir / "PostgresBase.yaml").write_text(
        "PostgresBase:\n"
        "  provider: docker\n"
        "  docker_host: tcp://10.0.0.1:2375\n"
        "  image: postgres\n"
        "  version: '16'\n"
        "  healthcheck: 'pg_isready -U postgres'\n"
        "  timeout: 30s\n",
        encoding="utf-8",
    )
    (tmp_dir / "PostgresTest.yaml").write_text(
        "PostgresTest:\n"
        "  extends: PostgresBase\n"
        "  port: 5432\n"
        "  env:\n"
        "    POSTGRES_DB: testdb\n",
        encoding="utf-8",
    )

    data = load_component(tmp_dir / "PostgresTest.yaml")
    comp = data["PostgresTest"]

    assert comp["image"] == "postgres"
    assert comp["version"] == "16"
    assert comp["docker_host"] == "tcp://10.0.0.1:2375"
    assert comp["healthcheck"] == "pg_isready -U postgres"
    assert comp["port"] == 5432
    assert comp["env"]["POSTGRES_DB"] == "testdb"
    assert "extends" not in comp


def test_extends_child_overrides_base(tmp_dir):
    (tmp_dir / "PostgresBase.yaml").write_text(
        "PostgresBase:\n"
        "  image: postgres\n"
        "  version: '16'\n",
        encoding="utf-8",
    )
    (tmp_dir / "PostgresNew.yaml").write_text(
        "PostgresNew:\n"
        "  extends: PostgresBase\n"
        "  version: '17'\n",
        encoding="utf-8",
    )

    data = load_component(tmp_dir / "PostgresNew.yaml")
    assert data["PostgresNew"]["version"] == "17"
    assert data["PostgresNew"]["image"] == "postgres"


def test_extends_merges_dicts(tmp_dir):
    (tmp_dir / "Base.yaml").write_text(
        "Base:\n"
        "  image: myapp\n"
        "  env:\n"
        "    DB_HOST: localhost\n"
        "    DB_PORT: '5432'\n",
        encoding="utf-8",
    )
    (tmp_dir / "Child.yaml").write_text(
        "Child:\n"
        "  extends: Base\n"
        "  env:\n"
        "    DB_NAME: testdb\n"
        "    DB_PORT: '3306'\n",
        encoding="utf-8",
    )

    data = load_component(tmp_dir / "Child.yaml")
    env = data["Child"]["env"]
    assert env["DB_HOST"] == "localhost"
    assert env["DB_NAME"] == "testdb"
    assert env["DB_PORT"] == "3306"


def test_extends_with_file_colon_syntax(tmp_dir):
    (tmp_dir / "bases.yaml").write_text(
        "PgBase:\n"
        "  image: postgres\n"
        "  version: '16'\n"
        "OtherBase:\n"
        "  image: redis\n",
        encoding="utf-8",
    )
    (tmp_dir / "MyPg.yaml").write_text(
        "MyPg:\n"
        "  extends: bases.yaml:PgBase\n"
        "  port: 5432\n",
        encoding="utf-8",
    )

    data = load_component(tmp_dir / "MyPg.yaml")
    assert data["MyPg"]["image"] == "postgres"
    assert data["MyPg"]["port"] == 5432


def test_extends_chain(tmp_dir):
    (tmp_dir / "Level1.yaml").write_text(
        "Level1:\n"
        "  image: postgres\n"
        "  version: '16'\n",
        encoding="utf-8",
    )
    (tmp_dir / "Level2.yaml").write_text(
        "Level2:\n"
        "  extends: Level1\n"
        "  port: 5432\n",
        encoding="utf-8",
    )
    (tmp_dir / "Level3.yaml").write_text(
        "Level3:\n"
        "  extends: Level2\n"
        "  env:\n"
        "    POSTGRES_DB: test\n",
        encoding="utf-8",
    )

    data = load_component(tmp_dir / "Level3.yaml")
    comp = data["Level3"]
    assert comp["image"] == "postgres"
    assert comp["port"] == 5432
    assert comp["env"]["POSTGRES_DB"] == "test"


def test_extends_base_not_found(tmp_dir):
    (tmp_dir / "Child.yaml").write_text(
        "Child:\n"
        "  extends: NonExistent\n"
        "  port: 1234\n",
        encoding="utf-8",
    )

    with pytest.raises(FileNotFoundError, match="NonExistent"):
        load_component(tmp_dir / "Child.yaml")


def test_extends_base_component_not_in_file(tmp_dir):
    (tmp_dir / "Other.yaml").write_text(
        "Other:\n"
        "  image: redis\n",
        encoding="utf-8",
    )
    (tmp_dir / "Child.yaml").write_text(
        "Child:\n"
        "  extends: Other.yaml:WrongName\n"
        "  port: 1234\n",
        encoding="utf-8",
    )

    with pytest.raises(KeyError, match="WrongName"):
        load_component(tmp_dir / "Child.yaml")
