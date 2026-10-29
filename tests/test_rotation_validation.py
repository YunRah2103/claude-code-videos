import tempfile
import unittest
from pathlib import Path
from tools.agent_rotation.validation import validate_python, stage_python

class ValidationTests(unittest.TestCase):
    def test_broken_and_empty_code_rejected(self):
        for code in ('', 'def broken(:\n pass', '\x00'):
            with self.assertRaises(ValueError): validate_python(code)

    def test_valid_code_staged_without_overwriting(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = stage_python(root, 'result.py', 'def square(x):\n    return x * x\n')
            self.assertEqual(path.read_text(), 'def square(x):\n    return x * x\n')
            with self.assertRaises(ValueError): stage_python(root, 'result.py', 'pass')
            with self.assertRaises(ValueError): stage_python(root, '../outside.py', 'pass')

    def test_symlink_path_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / 'stage'; root.mkdir()
            (root / 'link').symlink_to(Path(tmp), target_is_directory=True)
            with self.assertRaises(ValueError): stage_python(root, 'link/escape.py', 'pass')
