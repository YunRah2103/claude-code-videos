"""Static Python syntax validation and exclusive staging, without execution."""
import ast
import os
from pathlib import Path, PurePosixPath


def validate_python(code: str) -> None:
    if not isinstance(code, str) or not code.strip() or len(code.encode('utf-8')) > 1_000_000:
        raise ValueError('code must be nonempty UTF-8 text under 1 MB')
    try:
        ast.parse(code)
    except (SyntaxError, ValueError) as exc:
        raise ValueError('invalid Python syntax') from exc


def stage_python(root: Path, relative: str, code: str) -> Path:
    validate_python(code)
    if not isinstance(relative, str) or '\\' in relative:
        raise ValueError('invalid output path')
    path = PurePosixPath(relative)
    if path.is_absolute() or not path.parts or '..' in path.parts or path.suffix != '.py':
        raise ValueError('output must be a relative Python file')
    root = Path(root).resolve(strict=True)
    current = root
    for part in path.parts[:-1]:
        current = current / part
        if current.is_symlink() or not current.is_dir():
            raise ValueError('output parent must exist and cannot be a symlink')
    target = current / path.name
    try:
        fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, 'O_NOFOLLOW', 0), 0o600)
    except FileExistsError:
        raise ValueError('output already exists; inspect before retrying') from None
    with os.fdopen(fd, 'w', encoding='utf-8') as out:
        out.write(code)
    return target
