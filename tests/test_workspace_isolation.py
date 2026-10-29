import subprocess
import tempfile
import unittest
from pathlib import Path
from tools.agent_rotation.isolation import create_workspace

class WorkspaceTests(unittest.TestCase):
    def test_detached_worktree_leaves_source_unchanged(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / 'source'; root.mkdir()
            def git(*args): return subprocess.run(['git', '-C', str(root), *args], check=True, capture_output=True, text=True)
            git('init', '-q')
            git('config', 'user.email', 'test@example.invalid')
            git('config', 'user.name', 'Test')
            (root / 'file.py').write_text('original')
            git('add', 'file.py'); git('commit', '-qm', 'initial')
            work = create_workspace(root, Path(tmp) / 'out', 'task1')
            (work / 'file.py').write_text('changed')
            self.assertEqual((root / 'file.py').read_text(), 'original')
            self.assertEqual(git('status', '--porcelain').stdout, '')
            with self.assertRaises(ValueError): create_workspace(root, Path(tmp) / 'out', 'task1')

    def test_invalid_task_ids_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            for value in ('../x', '', '/tmp/evil', 'a/b', '..'):
                with self.assertRaises(ValueError): create_workspace(Path(tmp), Path(tmp) / 'out', value)
