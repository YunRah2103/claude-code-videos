"""Provider-reported request metrics, with missing values kept unknown."""
import math
from pathlib import Path
import sqlite3


class Metrics:
    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.path) as db:
            db.execute('''CREATE TABLE IF NOT EXISTS request_metrics
                (task_id TEXT PRIMARY KEY, provider TEXT NOT NULL, outcome TEXT NOT NULL,
                 prompt_tokens INTEGER, completion_tokens INTEGER, reasoning_tokens INTEGER, cost REAL)''')
            columns = {row[1] for row in db.execute('PRAGMA table_info(request_metrics)')}
            if 'total_tokens' not in columns:
                db.execute('ALTER TABLE request_metrics ADD COLUMN total_tokens INTEGER')

    def record(self, task_id, provider, outcome, prompt_tokens=None, completion_tokens=None,
               reasoning_tokens=None, cost=None, total_tokens=None):
        if not all(isinstance(x, str) and x.strip() for x in (task_id, provider, outcome)):
            raise ValueError('task, provider and outcome are required')
        for n in (prompt_tokens, completion_tokens, reasoning_tokens, total_tokens):
            if n is not None and (type(n) is not int or n < 0):
                raise ValueError('token counts must be nonnegative integers or unknown')
        if cost is not None and (isinstance(cost, bool) or not isinstance(cost, (int, float)) or not math.isfinite(cost) or cost < 0):
            raise ValueError('cost must be nonnegative and finite or unknown')
        with sqlite3.connect(self.path) as db:
            try:
                db.execute('INSERT INTO request_metrics (task_id,provider,outcome,prompt_tokens,completion_tokens,reasoning_tokens,cost,total_tokens) VALUES (?,?,?,?,?,?,?,?)',
                           (task_id, provider, outcome, prompt_tokens, completion_tokens, reasoning_tokens, cost, total_tokens))
            except sqlite3.IntegrityError:
                raise ValueError('metrics already recorded for task') from None

    def report(self):
        with sqlite3.connect(self.path) as db:
            rows = db.execute('SELECT prompt_tokens,completion_tokens,reasoning_tokens,total_tokens,cost FROM request_metrics').fetchall()
        result = {'requests': len(rows)}
        for i, label in enumerate(('prompt', 'completion', 'reasoning', 'total', 'cost')):
            values = [row[i] for row in rows]
            key = 'known_cost' if label == 'cost' else f'known_{label}_tokens'
            result[key] = sum(v for v in values if v is not None)
            result[f'unknown_{label}_counts'] = sum(v is None for v in values)
        return result
