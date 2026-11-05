"""Behavior of the optional Codex journal reminder hook."""

import subprocess
from pathlib import Path


def test_reminder_is_model_visible_and_does_not_write(tmp_path: Path) -> None:
    hook = Path(__file__).resolve().parents[1] / "codex" / "hooks" / "journal-reminder.sh"
    result = subprocess.run(
        ["bash", str(hook)], input='{"hook_event_name":"UserPromptSubmit"}',
        text=True, capture_output=True, cwd=tmp_path, check=True,
    )
    assert "journal" in result.stdout.lower()
    assert "nothing new" in result.stdout.lower()
    assert not list(tmp_path.iterdir())
