"""Offline checks that the Free-Agent-First policy is present, complete and installable."""
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CLAUDE = (ROOT / 'CLAUDE.md').read_text(encoding='utf-8')


class PolicyContentTests(unittest.TestCase):
    def test_section_is_present_and_existing_instructions_are_kept(self):
        self.assertIn('## FREE-AGENT-FIRST CODING POLICY', CLAUDE)
        self.assertIn('Ponytail lite is enabled locally', CLAUDE)
        self.assertIn('## Compact instructions', CLAUDE)
        self.assertLess(CLAUDE.index('## FREE-AGENT-FIRST CODING POLICY'), CLAUDE.index('## Compact instructions'))

    def test_required_rules_are_stated(self):
        required = [
            'coding manager',
            'tools.agent_rotation status',
            'providers',
            'Split large work',
            'Respect quotas, blocks and billing limits',
            'Never create accounts',
            'Record real token usage only',
            'Never invent quota or savings',
            'Standing policy is not authorisation for live requests',
            'typed approval at a terminal',
            'OpenRouter block in place',
            'Never run generated code without verified sandbox isolation',
            'Git worktrees are not a sandbox',
            'Keep Gemini and any unverified provider disabled',
            'never retry an uncertain request',
        ]
        for phrase in required:
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, CLAUDE)

    def test_policy_does_not_grant_live_request_authority(self):
        self.assertNotIn('authorised to send', CLAUDE.lower())
        self.assertNotIn('you may send live', CLAUDE.lower())


class UserInstallerTests(unittest.TestCase):
    def test_installer_is_idempotent_and_keeps_other_user_text(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / 'CLAUDE.md'
            target.write_text('My own note.\n', encoding='utf-8')
            env = dict(os.environ, CLAUDE_USER_DIR=tmp)
            script = str(ROOT / 'tools' / 'install_user_policy.sh')
            for _ in range(2):
                result = subprocess.run(['bash', script], env=env, capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stderr)
            text = target.read_text(encoding='utf-8')
            self.assertEqual(text.count('BEGIN free-agent-first policy'), 1)
            self.assertEqual(text.count('FREE-AGENT-FIRST CODING POLICY'), 1)
            self.assertIn('My own note.', text)


class CliDiscoveryTests(unittest.TestCase):
    def test_status_and_providers_show_openrouter_blocked_or_unverified(self):
        with tempfile.TemporaryDirectory() as tmp:
            state = Path(tmp) / 'state.db'
            for command in ('status', 'providers'):
                result = subprocess.run([sys.executable, '-m', 'tools.agent_rotation', '--state', str(state), command],
                                        cwd=ROOT, capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn('openrouter', result.stdout.lower())
                self.assertIn('gemini', result.stdout.lower())
                self.assertIn('kilo', result.stdout.lower())
            self.assertIn('DISABLED', subprocess.run([sys.executable, '-m', 'tools.agent_rotation', '--state', str(state),
                                                     'providers'], cwd=ROOT, capture_output=True, text=True).stdout)


if __name__ == '__main__':
    unittest.main()
