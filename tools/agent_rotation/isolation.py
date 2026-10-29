"""Create detached Git worktrees; these isolate edits, not hostile code."""
from pathlib import Path
import re
import subprocess


def create_workspace(source: Path, workspace_root: Path, task_id: str) -> Path:
    if not isinstance(task_id, str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{0,63}', task_id):
        raise ValueError('task ID must use letters, digits, underscore or hyphen')
    source = Path(source).resolve(strict=True)
    workspace_root = Path(workspace_root).resolve()
    if workspace_root == source or source in workspace_root.parents:
        raise ValueError('workspace root must be outside the source checkout')
    workspace_root.mkdir(parents=True, exist_ok=True)
    destination = workspace_root / task_id
    if destination.exists() or destination.is_symlink():
        raise ValueError('workspace already exists; inspect it before recovery')
    try:
        subprocess.run(['git', '-C', str(source), 'worktree', 'add', '--detach',
                        str(destination), 'HEAD'], check=True, capture_output=True,
                       text=True, timeout=60)
    except (subprocess.SubprocessError, OSError) as exc:
        raise RuntimeError('could not create detached worktree; inspect Git state before retrying') from exc
    return destination
