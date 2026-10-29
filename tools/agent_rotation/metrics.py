"""Provider-reported request metrics, with missing values kept unknown."""
import math
from pathlib import Path
import sqlite3
from .core import transaction


class Metrics:
    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with transaction(self.path) as db:
            db.execute('''CREATE TABLE IF NOT EXISTS request_metrics
                (task_id TEXT PRIMARY KEY, provider TEXT NOT NULL, outcome TEXT NOT NULL,
                 prompt_tokens INTEGER, completion_tokens INTEGER, reasoning_tokens INTEGER, cost REAL)''')
            columns = {row[1] for row in db.execute('PRAGMA table_info(request_metrics)')}
            if 'total_tokens' not in columns:
                db.execute('ALTER TABLE request_metrics ADD COLUMN total_tokens INTEGER')
            db.execute('''CREATE TABLE IF NOT EXISTS failure_diagnostics
                (task_id TEXT PRIMARY KEY, failure_stage TEXT NOT NULL, failure_code TEXT NOT NULL,
                 request_sent INTEGER, response_received INTEGER, model_verified INTEGER,
                 finish_reason_status TEXT NOT NULL, usage_available INTEGER NOT NULL)''')

    def record_failure(self, task_id, provider, failure):
        # Never persist provider-controlled strings or exception messages.
        codes = {'HTTP_FAILURE', 'NETWORK_FAILURE', 'REQUEST_TIMEOUT', 'RESPONSE_DECODING_FAILED',
                 'INVALID_PROVIDER_RESPONSE', 'UNEXPECTED_MODEL', 'INCOMPLETE_GENERATION',
                 'EMPTY_GENERATED_CONTENT', 'PYTHON_SYNTAX_INVALID', 'OUTPUT_STAGING_FAILED',
                 'INTERNAL_ADAPTER_ERROR', 'UNEXPECTED_COST', 'RESPONSE_TOO_LARGE', 'SAFETY_POLICY_REJECTED',
                 'HELPER_UNAVAILABLE', 'REQUEST_VALIDATION_FAILED', 'QUOTA_OR_DUPLICATE'}
        code = failure.failure_code if failure.failure_code in codes else 'INTERNAL_ADAPTER_ERROR'
        stage = failure.failure_stage if failure.failure_stage in {'preflight', 'transport', 'response', 'syntax', 'staging', 'internal'} else 'internal'
        finish = failure.finish_reason_status if failure.finish_reason_status in {'unknown', 'complete', 'incomplete'} else 'unknown'
        def tri(value):
            return int(value) if type(value) is bool else None
        usage = failure.usage
        with transaction(self.path) as db:
            db.execute('''INSERT OR IGNORE INTO request_metrics
                (task_id,provider,outcome,prompt_tokens,completion_tokens,reasoning_tokens,cost,total_tokens)
                VALUES (?,?,?,?,?,?,?,?)''', (task_id, provider, code, usage['prompt_tokens'],
                usage['completion_tokens'], usage['reasoning_tokens'], usage['cost'], usage['total_tokens']))
            db.execute('''INSERT OR IGNORE INTO failure_diagnostics VALUES (?,?,?,?,?,?,?,?)''',
                (task_id, stage, code, tri(failure.request_sent), tri(failure.response_received),
                 tri(failure.model_verified), finish, int(failure.usage_available)))

    def record(self, task_id, provider, outcome, prompt_tokens=None, completion_tokens=None,
               reasoning_tokens=None, cost=None, total_tokens=None):
        if not all(isinstance(x, str) and x.strip() for x in (task_id, provider, outcome)):
            raise ValueError('task, provider and outcome are required')
        for n in (prompt_tokens, completion_tokens, reasoning_tokens, total_tokens):
            if n is not None and (type(n) is not int or n < 0):
                raise ValueError('token counts must be nonnegative integers or unknown')
        if cost is not None and (isinstance(cost, bool) or not isinstance(cost, (int, float)) or not math.isfinite(cost) or cost < 0):
            raise ValueError('cost must be nonnegative and finite or unknown')
        with transaction(self.path) as db:
            try:
                db.execute('INSERT INTO request_metrics (task_id,provider,outcome,prompt_tokens,completion_tokens,reasoning_tokens,cost,total_tokens) VALUES (?,?,?,?,?,?,?,?)',
                           (task_id, provider, outcome, prompt_tokens, completion_tokens, reasoning_tokens, cost, total_tokens))
            except sqlite3.IntegrityError:
                raise ValueError('metrics already recorded for task') from None

    def has_record(self, task_id):
        with transaction(self.path) as db:
            return db.execute('SELECT 1 FROM request_metrics WHERE task_id=?', (task_id,)).fetchone() is not None

    def report(self):
        with transaction(self.path) as db:
            rows = db.execute('SELECT prompt_tokens,completion_tokens,reasoning_tokens,total_tokens,cost FROM request_metrics').fetchall()
        result = {'requests': len(rows)}
        for i, label in enumerate(('prompt', 'completion', 'reasoning', 'total', 'cost')):
            values = [row[i] for row in rows]
            key = 'known_cost' if label == 'cost' else f'known_{label}_tokens'
            result[key] = sum(v for v in values if v is not None)
            result[f'unknown_{label}_counts'] = sum(v is None for v in values)
        return result
