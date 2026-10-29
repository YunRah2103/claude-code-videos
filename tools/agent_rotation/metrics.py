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

    def record(self, task_id, provider, outcome, prompt_tokens=None, completion_tokens=None,
               reasoning_tokens=None, cost=None):
        if not all(isinstance(x, str) and x.strip() for x in (task_id, provider, outcome)):
            raise ValueError('task, provider and outcome are required')
        for n in (prompt_tokens, completion_tokens, reasoning_tokens):
            if n is not None and (type(n) is not int or n < 0):
                raise ValueError('token counts must be nonnegative integers or unknown')
        if cost is not None and (isinstance(cost, bool) or not isinstance(cost, (int, float)) or not math.isfinite(cost) or cost < 0):
            raise ValueError('cost must be nonnegative and finite or unknown')
        with sqlite3.connect(self.path) as db:
            try:
                db.execute('INSERT INTO request_metrics VALUES (?,?,?,?,?,?,?)',
                           (task_id, provider, outcome, prompt_tokens, completion_tokens, reasoning_tokens, cost))
            except sqlite3.IntegrityError:
                raise ValueError('metrics already recorded for task') from None

    def report(self):
        with sqlite3.connect(self.path) as db:
            row = db.execute('''SELECT COUNT(*), COALESCE(SUM(prompt_tokens),0),
                SUM(CASE WHEN completion_tokens IS NULL THEN 1 ELSE 0 END),
                SUM(CASE WHEN cost IS NULL THEN 1 ELSE 0 END) FROM request_metrics''').fetchone()
        return {'requests': row[0], 'known_prompt_tokens': row[1],
                'unknown_completion_counts': row[2] or 0, 'unknown_cost_counts': row[3] or 0}
