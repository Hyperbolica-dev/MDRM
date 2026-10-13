import os
from pathlib import Path
import shutil
import subprocess

import pytest


ROOT = Path(__file__).parents[1]


def git(path, *args):
    return subprocess.run(["git", "-C", str(path), *args], check=True, capture_output=True, text=True).stdout.strip()


@pytest.fixture
def installation(tmp_path):
    source = tmp_path / "source"
    source.mkdir()
    (source / "scripts").mkdir()
    shutil.copy(ROOT / "scripts/start_mrdm.sh", source / "scripts/start_mrdm.sh")
    (source / "environment.yaml").write_text("name: mrdm\ndependencies: [python]\n")
    git(source, "init", "-b", "main")
    git(source, "add", "scripts/start_mrdm.sh", "environment.yaml")
    git(source, "-c", "user.name=Test", "-c", "user.email=test@example.invalid", "commit", "-m", "fixture")
    binaries = tmp_path / "bin"
    binaries.mkdir()
    for command in ("git", "bash", "awk", "dirname"):
        (binaries / command).symlink_to(shutil.which(command))
    environment = {**os.environ, "PATH": str(binaries), "MRDM_REPOSITORY_URL": str(source), "MRDM_DIR": str(tmp_path / "installed"), "MRDM_ENVIRONMENT": "custom-rhythm", "CALL_LOG": str(tmp_path / "calls")}
    return source, binaries, environment


@pytest.mark.parametrize("manager", ["conda", "mamba"])
@pytest.mark.parametrize("exists", [False, True])
def test_install_uses_selected_manager_and_custom_environment(installation, manager, exists):
    source, binaries, environment = installation
    executable = binaries / manager
    executable.write_text(
        '#!/bin/bash\nset -eu\nprintf "%s\\n" "$*" >> "$CALL_LOG"\n'
        'if [[ "$*" == "env list" && "${EXISTING_ENV:-}" == yes ]]; then printf "custom-rhythm /tmp/env\\n"; fi\n'
        'if [[ "$0" == */mamba && "$*" == *--no-capture-output* ]]; then exit 40; fi\n'
        'if [[ "$0" == */conda && "$*" == "env update"* && "$*" == *--yes* ]]; then exit 41; fi\n'
    )
    executable.chmod(0o755)
    environment["EXISTING_ENV"] = "yes" if exists else "no"
    result = subprocess.run(["/bin/bash", str(ROOT / "scripts/install_mrdm.sh")], env=environment, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    calls = Path(environment["CALL_LOG"]).read_text()
    assert f"env {'update' if exists else 'create'} --name custom-rhythm" in calls
    assert "--name custom-rhythm python -m streamlit" in calls
    assert "--server.address=127.0.0.1" in calls
    installed = Path(environment["MRDM_DIR"])
    assert git(installed, "rev-parse", "HEAD") == git(source, "rev-parse", "HEAD")
    Path(environment["CALL_LOG"]).write_text("")
    second = subprocess.run(["/bin/bash", str(ROOT / "scripts/install_mrdm.sh")], env=environment, capture_output=True, text=True)
    assert second.returncode == 0, second.stderr
    (installed / "environment.yaml").write_text("user changes\n")
    Path(environment["CALL_LOG"]).write_text("")
    refused = subprocess.run(["/bin/bash", str(ROOT / "scripts/install_mrdm.sh")], env=environment, capture_output=True, text=True)
    assert refused.returncode == 2
    assert (installed / "environment.yaml").read_text() == "user changes\n"
    assert not Path(environment["CALL_LOG"]).read_text()
