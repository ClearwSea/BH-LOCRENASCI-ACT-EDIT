import copy
import json
from pathlib import Path
import tempfile
import unittest
from save_editor import edit, parse, save, Editor


def fixture():
    return {'schema':1, 'main':{'nickname':'测试','self_desc':'Hello','scoin':10,'hcoin':100,'stamina':10,'friends_point':5}, 'avatar_list':[], 'unknown':{'preserve':[1,2,3]}, 'endless_runtime':{'begin':100,'end':200,'progress':9,'max_progress':10,'progress_time':120,'active':None,'group':7,'claimed_floors':[1,2,3]}}

class Tests(unittest.TestCase):
    def test_allowlist_and_preservation(self):
        before=fixture()
        after, changes=edit(before,{'scoin':'1000'})
        expected=copy.deepcopy(before);expected['main']['scoin']=1000
        self.assertEqual(after,expected)
        self.assertEqual(before,fixture())
        with self.assertRaises(ValueError):edit(before,{'uid':'20'})
    def test_native_utf16_limit(self):
        with self.assertRaises(ValueError):edit(fixture(),{'nickname':'😀'*5})
        self.assertEqual(edit(fixture(),{'nickname':'😀'*4})[0]['main']['nickname'],'😀'*4)
    def test_numeric_bounds(self):
        for value in ['-1','1.5','100000001','１２']:
            with self.assertRaises(ValueError):edit(fixture(),{'scoin':value})
    def test_template_scope(self):
        before=fixture();after,_=edit(before,{},31,150)
        expected=copy.deepcopy(before)
        expected['endless_runtime'].update(progress=31,max_progress=31,progress_time=150)
        self.assertEqual(after,expected)
    def test_template_guards(self):
        for now in [99,200]:
            with self.assertRaises(ValueError):edit(fixture(),{},31,now)
        data=fixture();data['endless_runtime']['active']={}
        with self.assertRaises(ValueError):edit(data,{},31,150)
    def test_bad_json(self):
        for raw in [b'{"schema":1,"schema":1}',b'{"main":NaN}',b'[]']:
            with self.assertRaises(ValueError):parse(raw)
    def test_backup_roundtrip_and_conflict(self):
        with tempfile.TemporaryDirectory() as d:
            source=Path(d)/'account.json';original=json.dumps(fixture()).encode();source.write_bytes(original)
            after,_=edit(fixture(),{'scoin':'999'})
            backup=save(source,original,source,after)
            self.assertEqual(backup.read_bytes(),original)
            self.assertEqual(parse(source.read_bytes()),after)
            with self.assertRaises(ValueError):save(source,original,source,fixture())
    def test_save_as_no_overwrite(self):
        with tempfile.TemporaryDirectory() as d:
            source=Path(d)/'account.json';raw=json.dumps(fixture()).encode();source.write_bytes(raw)
            target=Path(d)/'new.json';save(source,raw,target,fixture())
            self.assertEqual(source.read_bytes(),raw)
            with self.assertRaises(ValueError):save(source,raw,target,fixture())

class ProgressionTests(unittest.TestCase):
    def world(self):
        a=fixture();a['main']['level']=80
        a['openworld_data']={'cycle':3,'finish_story_id_list':list(range(101,112))+list(range(201,208)), 'cur_story_list':[], 'servant_level':3, 'quest_data':{'keep':True}, 'spawn_point':'castle'}
        a['openworld_runtime']={'schema':1,'active':None,'receipts':{'101':{'reward':1}},'cycle_receipts':{'1':{'reward':2}},'area_teams':[]}
        return a
    def test_fourth_cycle_start(self):
        before=self.world();after,_=edit(before,{},cycle=4)
        self.assertEqual(after['openworld_data']['cycle'],4)
        self.assertIn(308,after['openworld_data']['finish_story_id_list'])
        self.assertNotIn(401,after['openworld_data']['finish_story_id_list'])
        self.assertEqual(after['openworld_data']['cur_story_list'],[])
        self.assertEqual(after['main'],before['main'])
        self.assertEqual(after['openworld_runtime']['cycle_receipts'],before['openworld_runtime']['cycle_receipts'])
    def test_story_replay_receipt_removed(self):
        a=self.world();a['openworld_runtime']['receipts']['301']={'reward':99}
        after,_=edit(a,{},cycle=3)
        self.assertNotIn('301',after['openworld_runtime']['receipts'])
        self.assertIn('101',after['openworld_runtime']['receipts'])
    def test_cycle_guards(self):
        a=self.world();a['openworld_runtime']['active']={}
        with self.assertRaises(ValueError):edit(a,{},cycle=4)
        a=self.world();a['main']['level']=41
        with self.assertRaises(ValueError):edit(a,{},cycle=4)
        with self.assertRaises(ValueError):edit(self.world(),{},cycle=5)
    def test_only_32_option(self):
        with self.assertRaises(ValueError):edit(fixture(),{},32,150)

class FullClearTests(unittest.TestCase):
    def account(self):
        a=fixture();a['main']['level']=80
        a['stage_list']=[{'id':999999,'progress':0,'is_done':False}]
        a['stage_runtime']={'schema':1,'active':None,'settlements':[]}
        a['mission_data']={'mission_list':[{'mission_id':900000,'status':2}], 'daily_duty_point':15}
        return a
    def test_all_complete_preserve_wallet_and_other_stages(self):
        a=self.account();b,changes=edit(a,{},story=True,extra=True,now=150)
        self.assertEqual(len(b['stage_list']),251)
        self.assertEqual(len(b['mission_runtime']['claimed_ids']),146)
        self.assertEqual(len(b['extra_achievement_runtime']['claimed_ids']),52)
        self.assertEqual(b['main'],a['main'])
        self.assertEqual(b['stage_list'][0],a['stage_list'][0])
        self.assertEqual(b['mission_data'],a['mission_data'])
        self.assertEqual(len(changes),2)
        c,again=edit(b,{},story=True,extra=True,now=160)
        self.assertEqual(c,b);self.assertEqual(again,[])
    def test_scopes_independent(self):
        a=self.account();b,_=edit(a,{},story=True)
        self.assertEqual(len(b['stage_list']),190)
        self.assertNotIn('extra_achievement_runtime',b)
        b,_=edit(a,{},extra=True)
        self.assertEqual(len(b['stage_list']),62)
        self.assertNotIn('mission_runtime',b)
    def test_active_and_low_level_rejected(self):
        a=self.account();a['stage_runtime']['active']={}
        with self.assertRaises(ValueError):edit(a,{},story=True)
        a=self.account();a['main']['level']=1
        with self.assertRaises(ValueError):edit(a,{},story=True)
    def test_unknown_mission_rejected_not_overwritten(self):
        a=self.account();a['mission_runtime']={'schema':1,'source_policy':'other','claimed_ids':[999],'receipts':[]}
        before=copy.deepcopy(a)
        with self.assertRaises(ValueError):edit(a,{},story=True)
        self.assertEqual(a,before)
    def test_existing_reward_receipts_preserved(self):
        from progression import CATALOG
        a=self.account();receipt={'mission_id':10001,'keep':'existing'}
        a['mission_runtime']={'schema':1,'source_policy':CATALOG['mission_policy'],'claimed_ids':[10001],'receipts':[receipt]}
        b,_=edit(a,{},story=True)
        self.assertEqual(b['mission_runtime']['receipts'],[receipt])

class RankTests(unittest.TestCase):
    def account(self):
        a=fixture();a['main']['level']=80
        a['endless_runtime'].update(display_temperature=35000,climate_opponents=[{'goal':3}],best_floor33_seconds=50,last_end={'old':1},wars=[1],items={'70001':2})
        a['endless_rewards']=[{'claimed':True}]
        return a
    def test_all_seven_ranks(self):
        for rank in range(1,8):
            a=self.account();b,_=edit(a,{},rank=rank,now=150)
            self.assertEqual(b['endless_runtime']['group'],rank)
            self.assertEqual(b['endless_runtime']['progress'],9)
            self.assertEqual(b['endless_runtime']['claimed_floors'],[1,2,3])
            self.assertEqual(b['endless_rewards'],a['endless_rewards'])
            self.assertEqual(b['endless_runtime']['items'],a['endless_runtime']['items'])
            if rank!=7:
                self.assertNotIn('display_temperature',b['endless_runtime'])
                self.assertNotIn('climate_opponents',b['endless_runtime'])
    def test_same_rank_noop(self):
        a=self.account();b,changes=edit(a,{},rank=7,now=150)
        self.assertEqual(a,b);self.assertFalse(changes)
    def test_rank_and_floor(self):
        b,_=edit(self.account(),{},31,150,rank=6)
        self.assertEqual((b['endless_runtime']['group'],b['endless_runtime']['progress']),(6,31))
    def test_rank_guards(self):
        for rank in (0,8,True):
            with self.assertRaises(ValueError):edit(self.account(),{},rank=rank,now=150)
        with self.assertRaises(ValueError):edit(self.account(),{},rank=6,now=200)
        a=self.account();a['endless_runtime']['active']={}
        with self.assertRaises(ValueError):edit(a,{},rank=6,now=150)

class TemplateTests(unittest.TestCase):
    def load(self,kind):
        from save_editor import load_template
        return load_template(kind)
    def test_identity_and_clean_history(self):
        for kind in ['新号','满级体验号']:
            a=self.load(kind)
            self.assertEqual(a['main']['nickname'],'免费版本禁止倒卖')
            self.assertEqual(a['main']['self_desc'],'开源免费版本，仅供学习与技术交流，禁止倒卖，版权归米哈游所有')
            self.assertEqual(len(a['main']['self_desc'].encode('utf-16-le'))//2,30)
            for key in ['gacha_runtime','local_recharge_runtime','wallet_limit_audit','development_test_adjustments','endless_test_history','endless_climate','sdk_account_name','player_card']:
                self.assertNotIn(key,a)
    def test_starter(self):
        a=self.load('新号')
        self.assertEqual(a['main']['level'],1)
        self.assertEqual(a['main']['stamina'],80)
        self.assertEqual(len(a['avatar_list']),1)
        self.assertEqual(a['avatar_list'][0]['avatar_id'],101)
        self.assertTrue(all(x['level']==1 for x in a['avatar_list']+a['weapon_list']))
        self.assertEqual(a['stigmata_list'],[])
        self.assertFalse(any(x['is_done'] for x in a['stage_list']))
    def test_experience(self):
        a=self.load('满级体验号');m=a['main']
        self.assertEqual((m['level'],m['stamina'],m['scoin'],m['hcoin']),(80,160,100000,1000))
        self.assertEqual(len(a['avatar_list']),26)
        self.assertTrue(all(x['level']==80 and x['star']==5 and x['touch_goodfeel']==60750 for x in a['avatar_list']))
        self.assertEqual(len({i for x in a['avatar_list'] for i in x['dress_list']}),46)
        self.assertEqual(len(a['stage_list']),250)
        self.assertTrue(all(x['is_done'] and x['progress']==1 and len(x['challenge_index_list'])==3 for x in a['stage_list']))
        self.assertEqual(a['openworld_data']['cycle'],4)
        self.assertIn(308,a['openworld_data']['finish_story_id_list'])
        self.assertNotIn(401,a['openworld_data']['finish_story_id_list'])
        self.assertEqual(a['openworld_data']['cur_story_list'],[])
    def test_loadout_references(self):
        for kind in ['新号','满级体验号']:
            a=self.load(kind);weapons={r['unique_id'] for r in a['weapon_list']};stigs={r['unique_id'] for r in a['stigmata_list']}
            self.assertEqual(len(weapons),len(a['weapon_list']))
            self.assertEqual(len(stigs),len(a['stigmata_list']))
            self.assertFalse(weapons&stigs)
            for av in a['avatar_list']:
                self.assertIn(av['weapon_unique_id'],weapons)
                for k in ('stigmata_unique_id_1','stigmata_unique_id_2','stigmata_unique_id_3'):
                    self.assertIn(av[k],stigs|{0})
    def test_templates_are_independent_and_export_safe(self):
        from save_editor import save_new
        a=self.load('新号');a['main']['nickname']='变化'
        self.assertNotEqual(self.load('新号')['main']['nickname'],'变化')
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'account.json';save_new(p,a);raw=p.read_bytes()
            with self.assertRaises(FileExistsError):save_new(p,self.load('满级体验号'))
            self.assertEqual(p.read_bytes(),raw)

class IdentityLockTests(unittest.TestCase):
    def test_template_identity_rejected_resources_allowed(self):
        from save_editor import load_template
        for kind in ['新号','满级体验号']:
            a=load_template(kind)
            for key in ['nickname','self_desc']:
                with self.assertRaisesRegex(ValueError,'不可'):edit(a,{key:'修改'})
            b,_=edit(a,{'nickname':a['main']['nickname'],'self_desc':a['main']['self_desc'],'scoin':'123'})
            self.assertEqual(b['main']['scoin'],123)
    def test_game_renamed_identity_preserved(self):
        from save_editor import load_template
        a=load_template('新号');a['main'].update(nickname='游戏改名',self_desc='游戏签名')
        b,_=edit(a,{'nickname':'游戏改名','self_desc':'游戏签名','scoin':'42'})
        self.assertEqual(b['main']['nickname'],'游戏改名')
        self.assertEqual(b['main']['self_desc'],'游戏签名')
    def test_normal_identity_editable(self):
        b,_=edit(fixture(),{'nickname':'改名','self_desc':'新签名'})
        self.assertEqual(b['main']['nickname'],'改名')
    def test_save_rejects_identity_change_before_writing(self):
        from save_editor import load_template
        a=load_template('新号');raw=json.dumps(a,ensure_ascii=False).encode('utf-8')
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'account.json';p.write_bytes(raw)
            a['main']['nickname']='修改'
            with self.assertRaisesRegex(ValueError,'不可'):save(p,raw,p,a)
            self.assertEqual(p.read_bytes(),raw)
            self.assertEqual(len(list(Path(d).iterdir())),1)

class CaptainLevelTests(unittest.TestCase):
    def account(self):
        a=fixture();a['main'].update(level=20,exp=123);return a
    def test_level_boundaries_and_scope(self):
        for level in [1,80]:
            a=self.account();b,_=edit(a,{'level':str(level)})
            expected=copy.deepcopy(a);expected['main'].update(level=level,exp=0)
            self.assertEqual(b,expected)
    def test_invalid_levels(self):
        for value in ['0','81','-1','1.5','abc']:
            with self.assertRaises(ValueError):edit(self.account(),{'level':value})
    def test_unchanged_level_preserves_exp(self):
        a=self.account();b,changes=edit(a,{'level':'20'})
        self.assertEqual(a,b);self.assertFalse(changes)
    def test_incompatible_exp_rejected(self):
        a=self.account();del a['main']['exp']
        with self.assertRaises(ValueError):edit(a,{'level':'80'})
    def test_template_level_and_progression(self):
        from save_editor import load_template
        a=load_template('新号');b,_=edit(a,{'level':'80'},story=True,extra=True)
        self.assertEqual(b['main']['level'],80)
        self.assertEqual(len(b['stage_list']),250)
        self.assertEqual(b['avatar_list'],a['avatar_list'])

if __name__=='__main__':unittest.main()
