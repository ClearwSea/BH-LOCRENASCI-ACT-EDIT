import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

import catalog_loader


class CatalogTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.catalog = catalog_loader.load_catalog()

    def test_reads_independently_and_returns_fresh_data(self):
        first = catalog_loader.load_catalog()
        second = catalog_loader.load_catalog()
        first['avatardata'].clear()
        self.assertTrue(second['avatardata'])
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'editor_catalog.json'
            path.write_text(json.dumps({'format_version': 1, 'catalog': {'independent': True}}),
                            encoding='utf-8')
            with patch.object(sys, '_MEIPASS', directory, create=True):
                self.assertEqual(catalog_loader.load_catalog(), {'independent': True})

    def test_identity_and_lookups(self):
        c = self.catalog
        keys = {'avatardata': 'avatarID', 'avatarsubskilldata': 'avatarSubSkillId',
                'dressdata': 'dressID', 'weapondata': 'ID', 'stigmatadata': 'ID',
                'materialdata': 'ID', 'avatarfragmentdata': 'ID', 'stages': 'id',
                'equipmentleveldata': 'level', 'avatarleveldata': 'level',
                'playerleveldata': 'level', 'textmap': 'ID'}
        for name, key in keys.items():
            ids = [row[key] for row in c[name]]
            self.assertTrue(ids, name)
            self.assertEqual(len(ids), len(set(ids)), name)
        texts = {row['ID']: row['Text'] for row in c['textmap']}
        self.assertEqual(texts['Avatar_Name_101'], '领域装·白练')
        weapons = {row['ID'] for row in c['weapondata']}
        fragments = {row['ID'] for row in c['avatarfragmentdata']}
        for row in c['avatardata']:
            self.assertIn(row['initialWeapon'], weapons)
            self.assertIn(row['avatarFragmentID'], fragments)
            self.assertIn(row['fullName'], texts)

    def test_story_prerequisites_and_sakura(self):
        rows = self.catalog['stages']
        self.assertEqual(len(rows), 582)
        ids = {r['id'] for r in rows}
        self.assertEqual({r['kind'] for r in rows}, {'story', 'extra'})
        for row in rows:
            self.assertTrue(row['display_name'])
            self.assertTrue(set(row['preLevelID']) <= ids | {0})
            for key in ('chapterId', 'difficulty', 'unlockPlayerLevel', 'unlockStarNum', 'maxProgress'):
                self.assertIs(type(row[key]), int)
            self.assertIsInstance(row['challengeList'], list)
        sakura = self.catalog['sakura']
        stories = sakura['stories']
        self.assertEqual(len(stories), 37)
        self.assertEqual(len(stories), len({r['StoryID'] for r in stories}))
        for key in ('cycle', 'second_cycle', 'third_cycle', 'fourth_cycle'):
            self.assertGreater(sakura[key]['level'], 0)
        self.assertEqual(self.catalog['abyss_floors'], 33)

    def test_material_presets_and_cabins_have_constraints(self):
        c = self.catalog
        materials = {r['ID']: r for r in c['materialdata']}
        for preset in c['material_presets']:
            self.assertTrue(preset['items'])
            for item in preset['items']:
                self.assertIn(item['id'], materials)
                self.assertGreater(item['num'], 0)
                self.assertLess(item['num'], materials[item['id']]['quantityLimit'])
        self.assertEqual({r['cabinType'] for r in c['cabinleveldata']}, {3, 4, 5})
        self.assertEqual({r['cabinType'] for r in c['cabinextendgradedata']}, {3, 4, 5})
        self.assertTrue(all(r['Cabin'] in (3, 4, 5) for r in c['cabintechtreedata']))


if __name__ == '__main__':
    unittest.main()
