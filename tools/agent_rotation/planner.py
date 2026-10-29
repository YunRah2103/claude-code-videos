"""Offline dependency planning; never launches or merges workers."""
from dataclasses import dataclass
from pathlib import PurePosixPath


@dataclass(frozen=True)
class Task:
    id: str
    files: tuple[str, ...]
    dependencies: tuple[str, ...]


def ready_batch(tasks: list[Task], completed: set[str]) -> list[Task]:
    by_id = {t.id: t for t in tasks}
    if len(by_id) != len(tasks) or any(not t.id for t in tasks):
        raise ValueError('task IDs must be unique and nonempty')
    for t in tasks:
        if not t.files or any(not p or PurePosixPath(p).is_absolute() or '..' in PurePosixPath(p).parts
                              or '\\' in p for p in t.files):
            raise ValueError('tasks require safe repository-relative file paths')
        if any(dep not in by_id for dep in t.dependencies):
            raise ValueError('unknown dependency')
    visiting, visited = set(), set()
    def visit(task_id):
        if task_id in visiting:
            raise ValueError('cyclic dependencies')
        if task_id in visited:
            return
        visiting.add(task_id)
        for dep in by_id[task_id].dependencies:
            visit(dep)
        visiting.remove(task_id)
        visited.add(task_id)
    for task_id in by_id:
        visit(task_id)
    result, used = [], set()
    for task in tasks:
        paths = {str(PurePosixPath(p)) for p in task.files}
        conflict = any(a == b or a.startswith(b + '/') or b.startswith(a + '/') for a in paths for b in used)
        if task.id not in completed and set(task.dependencies) <= completed and not conflict:
            result.append(task)
            used.update(paths)
    return result
