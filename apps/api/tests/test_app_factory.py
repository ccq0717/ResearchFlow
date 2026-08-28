import os
import subprocess
import sys
from pathlib import Path


def test_importing_app_factory_does_not_read_cwd_env(tmp_path: Path) -> None:
    (tmp_path / ".env").write_text(
        "RESEARCHFLOW_WORKFLOW_MODE=research\n",
        encoding="utf-8",
    )
    environment = {
        key: value for key, value in os.environ.items() if not key.startswith("RESEARCHFLOW_")
    }

    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "from researchflow.app_factory import create_app; print('factory-ok')",
        ],
        cwd=tmp_path,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "factory-ok"
