"""Non-destructive Tkinter smoke tests for the detailed editor tab."""
import copy
import tkinter as tk
from tkinter import ttk
import unittest
from unittest.mock import patch

from advanced_editor import create_tab
from catalog_loader import load_catalog
from save_editor import load_template


class AdvancedEditorGuiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            cls.root = tk.Tk()
        except tk.TclError as exc:
            raise unittest.SkipTest('Tk display unavailable: ' + str(exc))
        cls.root.withdraw()
        cls.catalog = load_catalog()
        cls.template = load_template('满级体验号')

    @classmethod
    def tearDownClass(cls):
        cls.root.destroy()

    def setUp(self):
        self.account = copy.deepcopy(self.template)
        self.original = copy.deepcopy(self.account)
        self.errors = []
        self.error_patch = patch('advanced_editor.messagebox.showerror', side_effect=lambda *args, **kwargs: self.errors.append(args))
        self.error_patch.start()
        self.notebook = ttk.Notebook(self.root)
        self.panel = create_tab(self.notebook, lambda: self.account, self.set_account, lambda: self.catalog)
        self.root.update_idletasks()

    def tearDown(self):
        self.notebook.destroy()
        self.error_patch.stop()

    def set_account(self, account):
        self.account = account

    def test_initial_state_and_filters_reflect_loaded_account(self):
        self.assertEqual(len(self.panel.pages.tabs()), 8)
        self.assertEqual(len(self.panel.avatar_tree.get_children()), len(self.catalog['avatardata']))
        self.assertTrue(self.panel._story_stages)
        self.assertIn(self.account['main']['nickname'], self.panel.captain_identity.get())
        self.panel.material_query.set('1001')
        self.assertIn('1001', self.panel.material_tree.get_children())
        self.panel.equipment_kind.set('圣痕上'); self.panel._refresh_equipment()
        self.assertTrue(self.panel.equipment_tree.get_children())
        self.assertTrue(all(self.panel.equipment_tree.item(i,'values')[3] == '圣痕上'
                            for i in self.panel.equipment_tree.get_children()))
        self.assertEqual(self.panel._label({'name':'missing'}, 'name', 12345), 'missing')
        self.assertEqual(self.panel._label({'name':'123456'}, 'name', 12345), 'ID 12345')
        self.assertEqual(self.account, self.original)

    def test_initial_tab_allows_no_open_account(self):
        def no_account():
            raise ValueError('请先打开存档。')
        empty_notebook = ttk.Notebook(self.root)
        try:
            panel = create_tab(empty_notebook, no_account, self.set_account, lambda: self.catalog)
            self.assertEqual(panel._account(), {})
            self.assertEqual(panel.avatar_tree.get_children(), ())
            self.assertEqual(panel.captain_tree.get_children(), ())
        finally:
            empty_notebook.destroy()

    def test_captain_and_material_edits_only_update_working_copy(self):
        self.panel.captain_tree.selection_set('scoin')
        before = self.account
        with patch('advanced_editor.simpledialog.askinteger', return_value=542422):
            self.panel._captain_edit()
        self.assertEqual(self.account['main']['scoin'], 542422)
        self.assertEqual(before, self.original)
        self.panel.material_query.set('1001')
        self.panel.material_tree.selection_set('1001')
        with patch('advanced_editor.simpledialog.askinteger', return_value=2):
            self.panel._material_edit()
        self.assertEqual(next(x['num'] for x in self.account['material_list'] if x['id'] == 1001), 2)
        self.assertEqual(self.errors, [])

    def test_skill_selection_updates_matching_character(self):
        self.panel.avatar_tree.selection_set('101'); self.panel._refresh_skills()
        key = self.panel.skill_tree.get_children()[0]
        sid, subid = map(int, key.split(':'))
        self.panel.skill_tree.selection_set(key)
        with patch('advanced_editor.simpledialog.askinteger', return_value=1):
            self.panel._skill_edit()
        avatar = next(x for x in self.account['avatar_list'] if x['avatar_id'] == 101)
        skill = next(x for x in avatar['skill_list'] if x['skill_id'] == sid)
        self.assertEqual(next(x['level'] for x in skill['sub_skill_list'] if x['sub_skill_id'] == subid), 1)
        self.assertEqual(self.errors, [])

    def test_costume_and_equipment_views_apply_to_selected_instances(self):
        dress = self.panel.costume_tree.get_children()[0]
        identity = int(dress)
        previously_owned = identity in self.account.get('has_got_item_id_list', [])
        self.panel.costume_tree.selection_set(dress)
        self.panel._costume_toggle()
        self.assertEqual(identity in self.account.get('has_got_item_id_list', []), not previously_owned)
        if previously_owned:
            for avatar in self.account.get('avatar_list', []):
                self.assertNotEqual(avatar.get('dress_id'), identity)
        uid = self.panel.equipment_tree.get_children()[0]
        _, item = self.panel._equipment_item(int(uid))
        previous = item.get('is_protected', False)
        self.panel.equipment_tree.selection_set(uid)
        self.panel._equipment_lock()
        _, changed = self.panel._equipment_item(int(uid))
        self.assertEqual(changed.get('is_protected'), not previous)
        self.assertEqual(self.errors, [])

    def test_story_selection_changes_status_without_creating_records(self):
        before = copy.deepcopy(self.account)
        self.panel.story_kind.set('外传')
        self.panel._refresh_story(reset=1)
        self.assertTrue(self.panel._story_stages)
        self.assertIn(self.panel.story_stage.get(), self.panel._story_stages)
        self.assertEqual(self.account, before)
        self.assertEqual(self.errors, [])

    def test_missing_cabin_and_authorized_stage_stars_are_not_misrepresented(self):
        self.account['cabin_list'] = [row for row in self.account.get('cabin_list', []) if row.get('type') != 4]
        stage_id = next(iter(self.panel._story_stages.values()))
        stage_config = next(row for row in self.catalog['stages'] if row['id'] == stage_id)
        saved = next((row for row in self.account.get('stage_list', []) if row.get('id') == stage_id), None)
        if saved is None:
            saved = {'id': stage_id}
            self.account.setdefault('stage_list', []).append(saved)
        saved.update({'progress': 0, 'is_done': False, 'challenge_index_list': [0, 1, 2]})
        self.account['stage_editor_stars'] = {str(stage_id): [0]}
        self.account['stage_runtime'] = {'schema': 1, 'active': None, 'settlements': []}
        self.panel.refresh()
        self.assertEqual(self.panel.cabin_tree.item('4', 'values')[1:3], ('未解锁', '—'))
        self.assertIn('记录星级：3', self.panel.story_current.get())
        self.assertIn('已确认星级：1', self.panel.story_current.get())
        saved.update({'progress': stage_config['maxProgress'], 'is_done': True})
        self.account['stage_runtime']['settlements'].append({'stage_id': stage_id, 'end_status': 1,
                                                            'response': {'retcode': 0, 'progress': 1}})
        self.panel.refresh()
        self.assertIn('已确认星级：3', self.panel.story_current.get())

    def test_failed_all_stars_keeps_previous_working_copy(self):
        prior = copy.deepcopy(self.account)
        with patch('advanced_editor.messagebox.askyesno', return_value=True), \
             patch('editor_engine.apply', side_effect=[copy.deepcopy(prior), ValueError('test failure')]):
            self.panel._story_all_stars()
        self.assertEqual(self.account, prior)
        self.assertEqual(len(self.errors), 1)


if __name__ == '__main__':
    unittest.main()
