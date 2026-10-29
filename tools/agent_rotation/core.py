"""Conservative, offline-only worker selection and persistent reservations."""
from dataclasses import dataclass
from datetime import datetime, timezone
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
    daily_limit: int | None = None
    monthly_limit: int | None = None

    def __post_init__(self):
        if (not self.name or self.max_requests < 1 or self.window_seconds < 1
            or any(v is not None and v < 1 for v in (self.daily_limit, self.monthly_limit))):
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

    @staticmethod
    def _has_capacity(db, worker, now):
        if db.execute('SELECT 1 FROM blocks WHERE worker=?', (worker.name,)).fetchone():
            return False
        def count(start, inclusive):
            op = '>=' if inclusive else '>'
            return db.execute(f'SELECT COUNT(*) FROM reservations WHERE worker=? AND created{op}?',
                              (worker.name, start)).fetchone()[0]
        if count(now - worker.window_seconds, False) >= worker.max_requests:
            return False
        current = datetime.fromtimestamp(now, timezone.utc)
        day_start = current.replace(hour=0, minute=0, second=0, microsecond=0).timestamp()
        month_start = current.replace(day=1, hour=0, minute=0, second=0, microsecond=0).timestamp()
        return not ((worker.daily_limit is not None and count(day_start, True) >= worker.daily_limit)
                    or (worker.monthly_limit is not None and count(month_start, True) >= worker.monthly_limit))

    def available(self, worker, now):
        with self._connect() as db:
            return self._has_capacity(db, worker, now)

    def reserve(self, worker, task_id, now):
        if not task_id or not (worker.enabled and worker.automatic and worker.free_verified):
            return False
        with self._connect() as db:
            db.execute('BEGIN IMMEDIATE')
            if not self._has_capacity(db, worker, now):
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
