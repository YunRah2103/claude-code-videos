"""Durable task lifecycle; state transitions never start provider calls."""
import json
from pathlib import Path
import sqlite3
import time

TRANSITIONS = {'planned': {'ready', 'cancelled'}, 'ready': {'running', 'cancelled'},
               'running': {'review', 'failed', 'interrupted'},
               'interrupted': {'review', 'failed'}, 'review': {'complete', 'failed'},
               'failed': set(), 'complete': set(), 'cancelled': set()}


class TaskStore:
    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as db:
            db.executescript('''CREATE TABLE IF NOT EXISTS tasks
               (id TEXT PRIMARY KEY, goal TEXT NOT NULL, files TEXT NOT NULL, status TEXT NOT NULL);
               CREATE TABLE IF NOT EXISTS task_events
               (id INTEGER PRIMARY KEY, task_id TEXT NOT NULL, status TEXT NOT NULL, timestamp REAL NOT NULL);''')

    def connect(self):
        return sqlite3.connect(self.path, timeout=10)

    def create(self, task_id, goal, files):
        if not isinstance(task_id, str) or not task_id.strip() or not isinstance(goal, str) or not goal.strip():
            raise ValueError('nonempty task ID and goal required')
        if not isinstance(files, list) or not files or not all(isinstance(f, str) and f for f in files):
            raise ValueError('at least one file path is required')
        with self.connect() as db:
            try:
                db.execute('INSERT INTO tasks VALUES (?, ?, ?, ?)', (task_id, goal, json.dumps(files), 'planned'))
                db.execute('INSERT INTO task_events (task_id,status,timestamp) VALUES (?,?,?)', (task_id, 'planned', time.time()))
            except sqlite3.IntegrityError:
                raise ValueError('task ID already exists') from None

    def transition(self, task_id, status):
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            row = db.execute('SELECT status FROM tasks WHERE id=?', (task_id,)).fetchone()
            if row is None:
                raise KeyError(task_id)
            if status not in TRANSITIONS[row[0]]:
                raise ValueError(f'invalid transition: {row[0]} -> {status}')
            db.execute('UPDATE tasks SET status=? WHERE id=?', (status, task_id))
            db.execute('INSERT INTO task_events (task_id,status,timestamp) VALUES (?,?,?)', (task_id, status, time.time()))

    def get(self, task_id):
        with self.connect() as db:
            row = db.execute('SELECT id,goal,files,status FROM tasks WHERE id=?', (task_id,)).fetchone()
            if row is None:
                raise KeyError(task_id)
            history = db.execute('SELECT status,timestamp FROM task_events WHERE task_id=? ORDER BY id', (task_id,)).fetchall()
        return {'id': row[0], 'goal': row[1], 'files': json.loads(row[2]), 'status': row[3], 'history': history}
