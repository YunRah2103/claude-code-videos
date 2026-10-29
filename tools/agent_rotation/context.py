"""Explicit, size-bounded local context packaging; never sends data."""
from pathlib import Path, PurePosixPath


def pack_context(root: Path, paths: list[str], max_bytes: int) -> dict[str, str]:
    if not isinstance(max_bytes, int) or max_bytes < 1 or len(paths) > 100:
        raise ValueError('positive byte limit and at most 100 paths required')
    root = Path(root).resolve(strict=True)
    result = {}
    total = 0
    for name in paths:
        if not isinstance(name, str) or not name or '\\' in name:
            raise ValueError('invalid relative path')
        relative = PurePosixPath(name)
        if relative.is_absolute() or '..' in relative.parts or str(relative) in ('.', ''):
            raise ValueError('path must stay inside the project')
        current = root
        for part in relative.parts:
            current = current / part
            if current.is_symlink():
                raise ValueError('symlink paths are not supported')
        if not current.is_file():
            raise ValueError(f'not a regular file: {name}')
        with current.open('rb') as stream:
            data = stream.read(max_bytes - total + 1)
        total += len(data)
        if total > max_bytes:
            raise ValueError('context byte limit exceeded')
        try:
            value = data.decode('utf-8')
        except UnicodeDecodeError:
            raise ValueError(f'not UTF-8 text: {name}') from None
        if '\x00' in value:
            raise ValueError(f'binary content: {name}')
        key = str(relative)
        if key in result:
            raise ValueError(f'duplicate file: {name}')
        result[key] = value
    return result
