"""Integration checks for PC editor working copies and safe persistence."""
import json
from pathlib import Path
import tempfile
import tkinter as tk
import unittest

import editor_engine
from save_editor import Editor, IDENTITY_FIELDS, load_template, parse, save


class EditorIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='bh3-pc-editor-check-')
        self.path = Path(self.tmp.name) / 'account.json'
        data = load_template('新号')
        self.original = (json.dumps(data, ensure_ascii=False) + '\n').encode('utf-8')
        self.path.write_bytes(self.original)
        self.root = tk.Tk()
        self.root.withdraw()
        self.app = Editor(self.root)
        self.app.load(self.path)
        self.root.update()

    def tearDown(self):
        self.root.destroy()
        self.tmp.cleanup()

    def test_basic_and_deep_edits_are_merged_without_writing_until_save(self):
        self.app.variables['scoin'].set('12345')
        pending = self.app._working_snapshot()
        updated = editor_engine.apply(pending, self.app._get_editor_catalog(),
                                      {'op': 'captain', 'friends_point': 37})
        self.app._replace_working_snapshot(updated)
        result, changes = self.app.candidate()
        self.assertTrue(changes)
        self.assertTrue(any('金币：0 → 12345' in change for change in changes))
        self.assertTrue(any('友情点：0 → 37' in change for change in changes))
        self.assertTrue(self.app.dirty())
        self.assertEqual(result['main']['scoin'], 12345)
        self.assertEqual(result['main']['friends_point'], 37)
        self.assertEqual(self.path.read_bytes(), self.original)
        backup = save(self.path, self.original, self.path, result)
        self.assertEqual(backup.read_bytes(), self.original)
        self.assertEqual(parse(self.path.read_bytes()), result)
        self.app.load(self.path)
        self.assertFalse(self.app.dirty())

    def test_identity_readonly_and_external_conflict_prevents_overwrite(self):
        self.assertTrue(all(str(self.app.entries[k]['state']) == 'readonly' for k in IDENTITY_FIELDS))
        self.app.variables['scoin'].set('123')
        result, _ = self.app.candidate()
        externally_modified = self.original + b' '
        self.path.write_bytes(externally_modified)
        with self.assertRaisesRegex(ValueError, '其他程序修改'):
            save(self.path, self.original, self.path, result)
        self.assertEqual(self.path.read_bytes(), externally_modified)
        self.assertEqual(list(self.path.parent.glob('*.bak')), [])

    def test_bulk_and_individual_costume_edits_share_one_working_state(self):
        catalog = self.app._get_editor_catalog()
        self.app.costumes.set('全部解锁')
        all_owned, _ = self.app.candidate()
        expected = editor_engine.apply(parse(self.original), catalog,
                                       {'op': 'costume_all', 'owned': True})
        self.assertEqual(all_owned, expected)
        selected = next(row['dressID'] for row in catalog['dressdata']
                        if row.get('dressType') == 1 and row.get('avatarIDList'))
        one_locked = editor_engine.apply(all_owned, catalog,
                                        {'op': 'costume', 'dress_id': selected, 'owned': False})
        self.app._replace_working_snapshot(one_locked)
        actual, _ = self.app.candidate()
        self.assertEqual(self.app.costumes.get(), '保持不变')
        self.assertEqual(actual, one_locked)
        self.assertNotIn(selected, actual.get('has_got_item_id_list', []))


if __name__ == '__main__':
    unittest.main()
