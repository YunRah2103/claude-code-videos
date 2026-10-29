"""Conservative, offline-only worker selection and persistent reservations."""
from dataclasses import dataclass
from pathlib import Path
import sqlite3


@dataclass(frozen=True)
class Worker:
    name: str
    capabilities: frozenset[str]
    enabled: bool
    automatic: bool
    free_verified: bool
    max_requests: int
    window_seconds: int

    def __post_init__(self):
        if not self.name or self.max_requests < 1 or self.window_seconds < 1:
            raise ValueError('worker name and positive quota limits required')


class Ledger:
    """SQLite reservations are permanent per task, including uncertain outcomes."""
    def __init__(self, path: Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as db:
            db.executescript('''CREATE TABLE IF NOT EXISTS reservations (
                task_id TEXT PRIMARY KEY, worker TEXT NOT NULL, created REAL NOT NULL);
                CREATE TABLE IF NOT EXISTS blocks (worker TEXT PRIMARY KEY, reason TEXT NOT NULL);''')

    def _connect(self):
        return sqlite3.connect(self.path, timeout=10)

    def block(self, worker, reason):
        with self._connect() as db:
            db.execute('INSERT OR REPLACE INTO blocks VALUES (?, ?)', (worker, reason))

    def available(self, worker, now):
        with self._connect() as db:
            blocked = db.execute('SELECT 1 FROM blocks WHERE worker=?', (worker.name,)).fetchone()
            count = db.execute('SELECT COUNT(*) FROM reservations WHERE worker=? AND created>?',
                               (worker.name, now - worker.window_seconds)).fetchone()[0]
            return not blocked and count < worker.max_requests

    def reserve(self, worker, task_id, now):
        if not task_id or not (worker.enabled and worker.automatic and worker.free_verified):
            return False
        with self._connect() as db:
            db.execute('BEGIN IMMEDIATE')
            if db.execute('SELECT 1 FROM blocks WHERE worker=?', (worker.name,)).fetchone():
                return False
            count = db.execute('SELECT COUNT(*) FROM reservations WHERE worker=? AND created>?',
                               (worker.name, now - worker.window_seconds)).fetchone()[0]
            if count >= worker.max_requests:
                return False
            try:
                db.execute('INSERT INTO reservations VALUES (?, ?, ?)', (task_id, worker.name, now))
            except sqlite3.IntegrityError:
                return False
            return True


class Registry:
    def __init__(self, workers):
        self.workers = tuple(workers)

    @classmethod
    def defaults(cls):
        # Historical results are not proof of current credentials or free eligibility.
        return cls([Worker('openrouter', frozenset({'code'}), False, True, False, 1, 86400),
                    Worker('gemini', frozenset({'code'}), False, True, False, 1, 86400),
                    Worker('claude', frozenset({'review'}), False, False, False, 1, 86400)])

    def select(self, capability, ledger, now):
        return next((w for w in self.workers if w.enabled and w.automatic and w.free_verified
                     and capability in w.capabilities and ledger.available(w, now)), None)
