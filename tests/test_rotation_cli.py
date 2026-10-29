"""Offline tests for the supervised CLI. The HTTP transport is mocked; no request leaves the process."""
import contextlib
import io
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tools import openrouter_task as helper  # noqa: E402
from tools.agent_rotation import cli  # noqa: E402

MODEL = cli.DEFAULT_MODEL
GOOD_CODE = 'def wheel_rotation_degrees(distance_pixels, wheel_radius_pixels):\n    return 0.0\n'
APPROVE = cli.APPROVAL_PREFIX + 'wheel'


def reply(content=None, finish='stop', model=MODEL, usage=None):
    body = {'model': model, 'choices': [{'finish_reason': finish,
                                         'message': {'content': content if content is not None
                                                     else '```python\n' + GOOD_CODE + '```'}}]}
    if usage is not False:
        body['usage'] = usage if usage is not None else {'prompt_tokens': 10, 'completion_tokens': 20,
                                                         'total_tokens': 30, 'cost': 0}
    return body


class _Stdin(io.StringIO):
    """Stand-in for a terminal: approval is only accepted when tty is True."""
    def __init__(self, text, tty):
        super().__init__(text)
        self._tty = tty

    def isatty(self):
        return self._tty


class CliCase(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.state = self.tmp / 'state' / 'state.db'
        self.repo = self.tmp / 'repo'
        self.repo.mkdir()
        git = ['git', '-c', 'user.email=t@t', '-c', 'user.name=t']
        subprocess.run(['git', 'init', '-q', str(self.repo)], check=True)
        (self.repo / 'README.md').write_text('x\n')
        subprocess.run(git + ['-C', str(self.repo), 'add', '.'], check=True)
        subprocess.run(git + ['-C', str(self.repo), 'commit', '-q', '-m', 'init'], check=True)
        self.patches = [mock.patch.object(cli, 'REPO_ROOT', self.repo),
                        mock.patch.object(cli, '_online_checks', return_value=[
                            ('zero-spend cap verified (read-only)', True, ''),
                            ('no management or provisioning key', True, ''),
                            ('model listed at zero price (read-only)', True, MODEL)])]
        for patch in self.patches:
            patch.start()
        self.sends = []
        self.responses = []
        self.send_patch = mock.patch.object(helper, 'send', side_effect=self._send)
        self.send_patch.start()

    def tearDown(self):
        self.send_patch.stop()
        for patch in self.patches:
            patch.stop()
        shutil.rmtree(cli.workspace_root(self.state), ignore_errors=True)
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _send(self, payload, *a, **k):
        self.sends.append(payload)
        outcome = self.responses.pop(0) if self.responses else reply()
        if isinstance(outcome, BaseException):
            raise outcome
        return 200, outcome

    def run_cli(self, *argv, stdin='', tty=True):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err), \
                mock.patch.object(sys, 'stdin', _Stdin(stdin, tty)):
            code = cli.main(['--state', str(self.state), *argv])
        return code, out.getvalue(), err.getvalue()

    def create_ready(self, task_id='wheel', goal='Write wheel_rotation_degrees.'):
        goal_file = self.tmp / 'goal.txt'
        goal_file.write_text(goal, encoding='utf-8')
        code, out, _ = self.run_cli('create', '--id', task_id, '--goal-file', str(goal_file), '--file', 'wheel.py')
        self.assertEqual(code, 0)
        return out


class ProviderAndCreateTests(CliCase):
    def test_providers_never_report_openrouter_operational(self):
        code, out, _ = self.run_cli('providers')
        self.assertEqual(code, 0)
        self.assertIn('UNAVAILABLE (not verified)', out)
        self.assertIn('gemini', out)
        self.assertIn('DISABLED', out)
        self.assertNotIn('READY', out)

    def test_create_from_file_marks_ready_and_hides_goal(self):
        out = self.create_ready(goal='PRIVATE_GOAL_TEXT')
        self.assertNotIn('PRIVATE_GOAL_TEXT', out)
        code, shown, _ = self.run_cli('show', '--id', 'wheel')
        self.assertEqual(code, 0)
        self.assertIn('"status": "ready"', shown)
        self.assertNotIn('PRIVATE_GOAL_TEXT', shown)

    def test_create_refuses_two_goal_sources_and_oversized_goal(self):
        goal_file = self.tmp / 'g.txt'
        goal_file.write_text('x')
        code, _, err = self.run_cli('create', '--id', 'a', '--goal-file', str(goal_file), '--goal', 'y', '--file', 'a.py')
        self.assertEqual(code, 2)
        goal_file.write_text('x' * (cli.MAX_GOAL_BYTES + 1))
        code, _, err = self.run_cli('create', '--id', 'b', '--goal-file', str(goal_file), '--file', 'b.py')
        self.assertEqual(code, 2)
        self.assertIn('exceeds', err)

    def test_template_creates_task_and_context_is_bounded(self):
        notes = self.repo / 'notes.txt'
        notes.write_text('context line\n')
        code, _, _ = self.run_cli('create', '--id', 'tpl', '--template', 'wheel-rotation', '--file', 'w.py')
        self.assertEqual(code, 0)
        with mock.patch.object(Path, 'cwd', return_value=self.repo):
            code, _, err = self.run_cli('create', '--id', 'ctx', '--template', 'wheel-rotation',
                                        '--context', str(notes), '--file', 'c.py')
        self.assertEqual(code, 0, err)
        from tools.agent_rotation.tasks import TaskStore
        self.assertIn('context line', TaskStore(self.state).get('ctx')['goal'])

    def test_templates_listed(self):
        code, out, _ = self.run_cli('templates')
        self.assertEqual(code, 0)
        for name in ('wheel-rotation', 'pixel-animation', 'ffmpeg-script', 'video-render-tool'):
            self.assertIn(name, out)


class PreflightAndRunGateTests(CliCase):
    def test_preflight_offline_is_read_only_and_refuses_unready_task(self):
        self.run_cli('create', '--id', 'x', '--goal', 'g', '--file', 'x.py')
        cli.open_state(self.state)
        code, out, _ = self.run_cli('preflight', '--id', 'x')
        self.assertEqual(code, 0)
        report = json.loads(out)
        self.assertFalse(report['request_sent'])
        self.assertFalse(report['can_run'])
        self.assertIn('online checks not run', report['reason'])

    def test_run_refused_without_fresh_online_verification(self):
        self.create_ready()
        with mock.patch.object(cli, '_online_checks', return_value=[('zero-spend cap verified (read-only)', False, '')]):
            code, _, err = self.run_cli('run', '--id', 'wheel', stdin=APPROVE + '\n')
        self.assertEqual(code, 3)
        self.assertEqual(self.sends, [])
        self.assertIn('no request was sent', err)

    def test_run_refused_for_paid_model_without_request(self):
        self.create_ready()
        code, _, err = self.run_cli('run', '--id', 'wheel', '--model', 'openai/gpt-4o', stdin=APPROVE + '\n')
        self.assertEqual(code, 3)
        self.assertEqual(self.sends, [])

    def test_run_refused_without_typed_approval(self):
        self.create_ready()
        code, _, err = self.run_cli('run', '--id', 'wheel', stdin='yes\n')
        self.assertEqual(code, 3)
        self.assertEqual(self.sends, [])
        self.assertIn('Not approved', err)

    def test_existing_provider_block_is_preserved_and_blocks_run(self):
        self.create_ready()
        from tools.agent_rotation.core import Ledger
        Ledger(self.state).block('openrouter', 'manual review required from earlier attempt')
        code, _, err = self.run_cli('run', '--id', 'wheel', stdin=APPROVE + '\n')
        self.assertEqual(code, 3)
        self.assertEqual(self.sends, [])
        code, out, _ = self.run_cli('preflight', '--id', 'wheel')
        self.assertIn('"provider_blocked": true', out)


class SupervisedRunTests(CliCase):
    def test_approved_run_sends_once_stages_and_reviews(self):
        self.create_ready()
        code, out, err = self.run_cli('run', '--id', 'wheel', stdin=APPROVE + '\n')
        self.assertEqual(code, 0, err)
        self.assertEqual(len(self.sends), 1)
        staged = cli.staged_path(self.state, 'wheel', 'wheel.py')
        self.assertTrue(staged.exists())
        self.assertFalse(str(staged).startswith(str(self.repo)))
        code, review, _ = self.run_cli('review', '--id', 'wheel')
        self.assertIn('Syntax: passed (not executed)', review)
        self.assertIn('Status: review', review)
        code, report, _ = self.run_cli('report')
        self.assertIn('"known_prompt_tokens": 10', report)
        self.assertIn('"known_cost": 0', report)

    def test_second_attempt_on_same_task_is_refused_without_request(self):
        self.create_ready()
        self.run_cli('run', '--id', 'wheel', stdin=APPROVE + '\n')
        code, _, err = self.run_cli('run', '--id', 'wheel', stdin=APPROVE + '\n')
        self.assertEqual(code, 3)
        self.assertEqual(len(self.sends), 1)

    def test_invalid_python_is_not_staged_and_not_retried(self):
        self.create_ready()
        self.responses = [reply(content='```python\ndef broken(:\n```')]
        code, _, err = self.run_cli('run', '--id', 'wheel', stdin=APPROVE + '\n')
        self.assertEqual(code, 1)
        self.assertEqual(len(self.sends), 1)
        self.assertFalse(cli.staged_path(self.state, 'wheel', 'wheel.py').exists())
        self.assertIn('PYTHON_SYNTAX_INVALID', err)

    def test_timeout_is_reported_and_never_retried(self):
        self.create_ready()
        self.responses = [TimeoutError()]
        code, _, err = self.run_cli('run', '--id', 'wheel', stdin=APPROVE + '\n')
        self.assertEqual(code, 1)
        self.assertEqual(len(self.sends), 1)
        self.assertIn('REQUEST_TIMEOUT', err)

    def test_rate_limit_is_reported_and_never_retried(self):
        self.create_ready()
        self.responses = [helper.TaskError('rate limited', code='HTTP_FAILURE', response_received=True)]
        code, _, err = self.run_cli('run', '--id', 'wheel', stdin=APPROVE + '\n')
        self.assertEqual(code, 1)
        self.assertEqual(len(self.sends), 1)

    def test_unexpected_model_blocks_provider(self):
        self.create_ready()
        self.responses = [reply(model='other/paid-model')]
        code, _, err = self.run_cli('run', '--id', 'wheel', stdin=APPROVE + '\n')
        self.assertEqual(code, 1)
        self.assertEqual(len(self.sends), 1)
        code, out, _ = self.run_cli('providers')
        self.assertIn('BLOCKED', out)

    def test_missing_usage_is_reported_as_unknown_not_zero(self):
        self.create_ready()
        self.responses = [reply(usage=False)]
        code, _, err = self.run_cli('run', '--id', 'wheel', stdin=APPROVE + '\n')
        self.assertIn(code, (0, 1))
        code, report, _ = self.run_cli('report')
        self.assertIn('"unknown_total_counts": 1', report)

    def test_review_approve_requires_review_status(self):
        self.create_ready()
        code, _, err = self.run_cli('review', '--id', 'wheel', '--approve')
        self.assertEqual(code, 3)
        self.run_cli('run', '--id', 'wheel', stdin=APPROVE + '\n')
        code, out, _ = self.run_cli('review', '--id', 'wheel', '--approve')
        self.assertEqual(code, 0)
        self.assertIn('Decision recorded: complete', out)

    def test_daily_quota_refuses_a_second_task_without_request(self):
        self.create_ready('first')
        self.create_ready('second')
        self.assertEqual(self.run_cli('run', '--id', 'first', stdin=cli.APPROVAL_PREFIX + 'first\n')[0], 0)
        code, _, err = self.run_cli('run', '--id', 'second', stdin=cli.APPROVAL_PREFIX + 'second\n')
        self.assertEqual(code, 3)
        self.assertEqual(len(self.sends), 1)
        self.assertIn('daily quota', err)

    def test_staging_failure_interrupts_task_and_blocks_provider(self):
        self.create_ready()
        with mock.patch('tools.agent_rotation.orchestrator.stage_python', side_effect=OSError('disk full')):
            code, _, err = self.run_cli('run', '--id', 'wheel', stdin=APPROVE + '\n')
        self.assertEqual(code, 1)
        self.assertEqual(len(self.sends), 1)
        code, out, _ = self.run_cli('providers')
        self.assertIn('BLOCKED', out)
        code, history, _ = self.run_cli('history', '--id', 'wheel')
        self.assertIn('interrupted', history)

    def test_run_requires_an_interactive_terminal(self):
        self.create_ready()
        code, _, err = self.run_cli('run', '--id', 'wheel', stdin=APPROVE + '\n', tty=False)
        self.assertEqual(code, 3)
        self.assertEqual(self.sends, [])
        self.assertIn('interactive terminal', err)


class ReviewSafeguardTests(CliCase):
    def _staged_run(self):
        self.create_ready()
        self.assertEqual(self.run_cli('run', '--id', 'wheel', stdin=APPROVE + '\n')[0], 0)
        return cli.staged_path(self.state, 'wheel', 'wheel.py')

    def test_approve_refuses_missing_staged_file(self):
        staged = self._staged_run()
        staged.unlink()
        code, _, err = self.run_cli('review', '--id', 'wheel', '--approve')
        self.assertEqual(code, 3)
        self.assertIn('missing', err)
        self.assertEqual(self.run_cli('history', '--id', 'wheel')[0], 0)
        self.assertIn('Status: review', self.run_cli('review', '--id', 'wheel')[1])

    def test_approve_refuses_altered_staged_file(self):
        staged = self._staged_run()
        staged.write_text(GOOD_CODE + '\n# edited after staging\n', encoding='utf-8')
        code, _, err = self.run_cli('review', '--id', 'wheel', '--approve')
        self.assertEqual(code, 3)
        self.assertIn('changed after staging', err)
        self.assertIn('Status: review', self.run_cli('review', '--id', 'wheel')[1])

    def test_approve_refuses_invalid_python_even_with_matching_digest(self):
        staged = self._staged_run()
        bad = 'def broken(:\n'
        staged.write_text(bad, encoding='utf-8')
        cli._record_stage(self.state, 'wheel', staged)
        code, _, err = self.run_cli('review', '--id', 'wheel', '--approve')
        self.assertEqual(code, 3)
        self.assertIn('not valid Python', err)

    def test_approve_refuses_when_no_staging_record_exists(self):
        self._staged_run()
        from tools.agent_rotation.core import transaction
        with transaction(self.state) as db:
            db.execute('DELETE FROM staged_outputs')
        code, _, err = self.run_cli('review', '--id', 'wheel', '--approve')
        self.assertEqual(code, 3)
        self.assertIn('no staging record', err)

    def test_history_shows_events_and_outcome(self):
        self.create_ready()
        self.run_cli('run', '--id', 'wheel', stdin=APPROVE + '\n')
        code, out, _ = self.run_cli('history', '--id', 'wheel')
        self.assertEqual(code, 0)
        for status in ('planned', 'ready', 'running', 'review'):
            self.assertIn(status, out)


class AccountCheckTests(unittest.TestCase):
    def test_spend_status_requires_zero_limit_and_remaining(self):
        body = {'data': {'limit': 0, 'limit_remaining': 0, 'is_free_tier': True,
                         'is_management_key': False, 'is_provisioning_key': False}}
        with mock.patch.object(helper, 'read_only_json', return_value=body):
            status = helper.account_spend_status()
        self.assertTrue(status['zero_spend_verified'])
        body['data']['limit'] = None
        with mock.patch.object(helper, 'read_only_json', return_value=body):
            self.assertFalse(helper.account_spend_status()['zero_spend_verified'])

    def test_model_must_be_listed_at_zero_price(self):
        body = {'data': [{'id': MODEL, 'pricing': {'prompt': '0', 'completion': '0'}}]}
        with mock.patch.object(helper, 'read_only_json', return_value=body):
            self.assertTrue(helper.model_is_listed_free(MODEL))
            self.assertFalse(helper.model_is_listed_free('other/model:free'))


if __name__ == '__main__':
    unittest.main()
