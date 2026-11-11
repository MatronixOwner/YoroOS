import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'desktop'))
from yoroapps import fileops, trashutil


class FileOperationsTest(unittest.TestCase):
    def test_copy_move_and_collision(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            src, dst = root / 'source', root / 'destination'
            src.mkdir(); dst.mkdir()
            (src / 'a.txt').write_text('original')
            self.assertEqual(fileops.copy_or_move([str(src / 'a.txt')], str(dst)), [])
            self.assertEqual((dst / 'a.txt').read_text(), 'original')
            (src / 'a.txt').write_text('changed')
            self.assertTrue(fileops.copy_or_move([str(src / 'a.txt')], str(dst), True))
            self.assertEqual((dst / 'a.txt').read_text(), 'original')
            self.assertTrue((src / 'a.txt').exists())
            (dst / 'a.txt').unlink()
            self.assertEqual(fileops.copy_or_move([str(src / 'a.txt')], str(dst), True), [])
            self.assertFalse((src / 'a.txt').exists())

    def test_nested_directory_and_rename_guards(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); folder = root / 'a'; folder.mkdir(); (folder / 'b').mkdir()
            self.assertTrue(fileops.copy_or_move([str(folder)], str(folder / 'b')))
            (root / 'existing').write_text('do not overwrite')
            with self.assertRaises(FileExistsError): fileops.rename(str(folder), 'existing')
            with self.assertRaises(ValueError): fileops.rename(str(folder), '../bad')
            self.assertTrue(folder.exists())

    def test_symlink_copied_as_symlink(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); (root / 'd').mkdir(); (root / 'target').write_text('x')
            (root / 'link').symlink_to('target')
            self.assertEqual(fileops.copy_or_move([str(root / 'link')], str(root / 'd')), [])
            self.assertTrue((root / 'd/link').is_symlink())

    def test_trash_round_trip(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); data = root / 'data'; data.mkdir(); source = root / 'hello.txt'; source.write_text('text')
            old = os.environ.get('XDG_DATA_HOME'); os.environ['XDG_DATA_HOME'] = str(data)
            try:
                trashutil.move_to_trash(str(source))
                items = trashutil.list_trash(); self.assertEqual(len(items), 1)
                trashutil.restore(items[0]); self.assertEqual(source.read_text(), 'text')
            finally:
                if old is None: os.environ.pop('XDG_DATA_HOME', None)
                else: os.environ['XDG_DATA_HOME'] = old

if __name__ == '__main__': unittest.main()
