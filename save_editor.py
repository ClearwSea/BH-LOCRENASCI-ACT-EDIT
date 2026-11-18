"""BH3 V1.9 offline save editor."""
import copy
import datetime
import json
import os
from pathlib import Path
import tempfile
import time
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

FIELDS = {
    'nickname': ('昵称', 8), 'self_desc': ('签名', 30),
    'level': ('舰长等级', 80),
    'scoin': ('金币', 100_000_000), 'hcoin': ('水晶', 0xffffffff),
    'stamina': ('体力', 999), 'friends_point': ('友情点', 100_000),
    'equipment_size_limit': ('装备仓库上限', 0xffffffff),
}
TEMPLATES = {'保持不变': None, '到达32关': 31}
from progression import CYCLES, RANKS, set_rank
from costumes import CHOICES as COSTUMES
from avatars import (
    AVATAR_CATALOG, AVATAR_META, LABEL_TO_STAR, MIN_CAPTAIN_LEVEL,
    STAR_LABELS, apply_avatar_edits, current_avatar_states,
)

EDITOR_VERSION = 'v0.8.4'


def expected_equipment_size_limit(level):
    return 500 + (max(1, int(level)) - 1) * 20


def equipment_count(account):
    weapons = account.get('weapon_list', [])
    stigmata = account.get('stigmata_list', [])
    return (len(weapons) if isinstance(weapons, list) else 0) + (
        len(stigmata) if isinstance(stigmata, list) else 0
    )


def min_equipment_size_limit(account):
    level = account.get('main', {}).get('level', 1)
    if type(level) is not int or level < 1:
        level = 1
    return max(expected_equipment_size_limit(level), equipment_count(account))


def parse(raw):
    def pairs(items):
        obj = {}
        for k, v in items:
            if k in obj:
                raise ValueError('JSON 有重复字段：' + k)
            obj[k] = v
        return obj
    def invalid(value):
        raise ValueError('不支持非有限数字：' + value)
    data = json.loads(raw.decode('utf-8-sig'), object_pairs_hook=pairs, parse_constant=invalid)
    if not isinstance(data, dict) or data.get('schema') != 1 or not isinstance(data.get('main'), dict):
        raise ValueError('需要 schema=1 且包含 main 对象的 account.json。')
    if not isinstance(data.get('avatar_list'), list):
        raise ValueError('缺少角色列表，无法识别为当前存档。')
    return data


IDENTITY_FIELDS = ('nickname', 'self_desc')

def identity_locked(data):
    return data.get('account_mode') in ('starter-template', 'experience-template')


def check_identity(original, result):
    if any(original['main'].get(k) != result['main'].get(k) for k in IDENTITY_FIELDS):
        raise ValueError('昵称和签名请在游戏内修改。')


def describe_working_changes(original, result):
    """Summarize actual changes to the in-memory copy before saving."""
    labels = {key: value[0] for key, value in FIELDS.items()}
    labels.update({'exp': '舰长经验', 'skill_point': '技能点', 'skill_point_limit': '技能点上限'})
    before, after = original.get('main', {}), result.get('main', {})
    lines = [f'{labels.get(key, key)}：{before.get(key, "—")} → {after.get(key, "—")}'
             for key in sorted(set(before) | set(after))
             if before.get(key) != after.get(key)]
    groups = {
        'avatar_list': ('女武神', 'avatar_id'),
        'weapon_list': ('武器', 'unique_id'),
        'stigmata_list': ('圣痕', 'unique_id'),
        'material_list': ('材料', 'id'),
        'cabin_list': ('家园舱室', 'type'),
        'stage_list': ('关卡记录', 'id'),
    }
    for key, (name, identity) in groups.items():
        old, new = original.get(key, []), result.get(key, [])
        if old == new:
            continue
        if not isinstance(old, list) or not isinstance(new, list):
            lines.append(f'{name}：数据已调整')
            continue
        old_rows = {row[identity]: row for row in old if isinstance(row, dict) and type(row.get(identity)) is int}
        new_rows = {row[identity]: row for row in new if isinstance(row, dict) and type(row.get(identity)) is int}
        added, removed = set(new_rows) - set(old_rows), set(old_rows) - set(new_rows)
        changed = {i for i in old_rows.keys() & new_rows.keys() if old_rows[i] != new_rows[i]}
        lines.append(f'{name}：新增 {len(added)}、修改 {len(changed)}、移除 {len(removed)}')
        if key == 'material_list':
            for item in sorted(added | removed | changed)[:8]:
                lines.append(f'  材料 {item}：{old_rows.get(item, {}).get("num", 0)} → {new_rows.get(item, {}).get("num", 0)}')
    other_labels = {'stage_editor_stars': '关卡满星授权', 'openworld_data': '樱色轮回',
                    'openworld_editor_skipped': '轮回跳过记录', 'endless_runtime': '深渊进度',
                    'has_got_item_id_list': '已获得物品', 'skill_point_runtime': '技能点恢复状态',
                    'is_first_login': '首次登录状态'}
    for key, label in other_labels.items():
        if original.get(key) != result.get(key):
            lines.append(label + '：已调整')
    handled = {'main', *groups, *other_labels}
    extra = sorted(key for key in (set(original) | set(result)) - handled
                   if original.get(key) != result.get(key))
    if extra:
        lines.append('其他存档字段已调整：' + '、'.join(extra))
    return lines


def edit(data, values, template=None, now=None, *, cycle=None, story=False, extra=False, rank=None, costumes=None, avatar_edits=None):
    if cycle is not None or story or extra:
        raise ValueError('请在深度编辑中修改剧情、外传和樱色轮回。')
    changes = []
    edited_equip_limit = False
    captain_edits = {}
    for key, text in values.items():
        if key not in FIELDS or key not in data['main']:
            raise ValueError('不允许添加或编辑字段：' + key)
        label, limit = FIELDS[key]
        old = data['main'][key]
        if str(old) == text:
            continue  # Preserve out-of-range legacy values unless explicitly edited.
        if key in IDENTITY_FIELDS:
            raise ValueError('昵称和签名请在游戏内修改。')
        if type(old) is not int or not isinstance(text, str) or not text.isascii() or not text.isdecimal():
            raise ValueError(label + '须为非负整数。')
        new = int(text)
        minimum = 1 if key == 'level' else 0
        if not minimum <= new <= limit:
            raise ValueError(f'{label}编辑范围为 {minimum}–{limit:,}。')
        if old != new:
            captain_edits[key] = new
            if key == 'equipment_size_limit':
                edited_equip_limit = True
            changes.append(f'{label}：{old} → {new}')
            if key == 'level':
                exp = data['main'].get('exp')
                if type(exp) is not int or exp < 0:
                    raise ValueError('舰长经验字段不兼容，不能修改等级。')
                changes.append(f'舰长当前等级经验：{exp} → 0（不补发升级奖励）')
    if captain_edits:
        from catalog_loader import load_catalog
        from editor_engine import apply as apply_deep
        result = apply_deep(data, load_catalog(), {'op': 'captain', **captain_edits})
        if 'equipment_size_limit' not in data['main'] and 'equipment_size_limit' not in captain_edits:
            result['main'].pop('equipment_size_limit', None)
    else:
        result = copy.deepcopy(data)
    if avatar_edits:
        changes.extend(apply_avatar_edits(result, avatar_edits))
    if 'equipment_size_limit' in result['main']:
        cur_limit = result['main']['equipment_size_limit']
        min_limit = min_equipment_size_limit(result)
        max_limit = FIELDS['equipment_size_limit'][1]
        if min_limit > max_limit:
            raise ValueError(f'已有或新增装备总数超过系统上限 {max_limit:,}，无法保存。')
        if type(cur_limit) is int and cur_limit < min_limit:
            tier_floor = expected_equipment_size_limit(result['main'].get('level', 1))
            owned = equipment_count(result)
            if edited_equip_limit:
                raise ValueError(
                    f'装备仓库上限不能小于 {min_limit}（当前等级档位至少 {tier_floor}，已有装备 {owned} 件）。'
                )
            result['main']['equipment_size_limit'] = min_limit
            changes.append(f'装备仓库上限：{cur_limit} → {min_limit}（自动校准至当前最低要求）')
    if template is not None:
        if template != 31:
            raise ValueError('不支持的深渊模板。')
        state = result.get('endless_runtime')
        required = ('begin', 'end', 'progress', 'max_progress', 'progress_time')
        if not isinstance(state, dict) or any(type(state.get(k)) is not int for k in required):
            raise ValueError('深渊结构不兼容，不能应用模板。')
        now = int(time.time() if now is None else now)
        if not state['begin'] <= now < state['end']:
            raise ValueError('深渊周期已过期或尚未开始。请先在游戏中进入当前深渊，再关闭游戏并重新拷出存档。')
        if 'active' not in state or state['active'] is not None:
            raise ValueError('仍有深渊战斗状态，请先在游戏中结束战斗。')
        if not 0 <= state['progress'] <= 33 or not 0 <= state['max_progress'] <= 33:
            raise ValueError('深渊进度超出已知范围。')
        old = state['progress']
        state.update(progress=template, max_progress=max(template, state['max_progress']), progress_time=now)
        changes.append('深渊：到达32关（第32关可挑战）')
    if rank is not None:
        change = set_rank(result, rank, now)
        if change: changes.append(change)
    if costumes is not None:
        from catalog_loader import load_catalog
        from editor_engine import apply as apply_deep
        catalog = load_catalog()
        before = result
        if costumes:
            result = apply_deep(result, catalog, {'op': 'costume_all', 'owned': True})
        else:
            for dress in catalog.get('dressdata', []):
                if dress.get('dressType') == 1 and dress.get('avatarIDList'):
                    result = apply_deep(result, catalog, {'op': 'costume',
                                        'dress_id': dress['dressID'], 'owned': False})
        if result != before:
            changes.append('服装：' + ('解锁全部支持的服装' if costumes else '锁定全部支持的服装'))
    return result, changes


def save(source, original, target, result):
    check_identity(parse(original), result)
    source, target = Path(source), Path(target)
    if source.read_bytes() != original:
        raise ValueError('原文件已被其他程序修改，请重新打开；未写入。')
    raw = (json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False) + '\n').encode('utf-8')
    parse(raw)
    same = source.resolve() == target.resolve() or (target.exists() and os.path.samefile(source, target))
    if target.exists() and not same:
        raise ValueError('另存目标已存在，请选择新文件名，避免覆盖其他存档。')
    stamp = datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    backup = source.with_name(source.name + '.' + stamp + '.bak')
    with backup.open('xb') as f:
        f.write(original)
        f.flush()
        os.fsync(f.fileno())
    if backup.read_bytes() != original:
        raise OSError('备份校验失败，未写入目标。')
    if same:
        fd, name = tempfile.mkstemp(prefix='.account-editor-', suffix='.tmp', dir=target.parent)
        try:
            with os.fdopen(fd, 'wb') as f:
                f.write(raw)
                f.flush()
                os.fsync(f.fileno())
            if source.read_bytes() != original:
                raise ValueError('原文件在保存期间发生变化，已停止。')
            os.replace(name, target)
        finally:
            if os.path.exists(name):
                os.unlink(name)
    else:
        with target.open('xb') as f:
            f.write(raw)
            f.flush()
            os.fsync(f.fileno())
    if target.read_bytes() != raw:
        raise OSError('写入回读不一致，请保留备份并检查存储设备。')
    return backup


TEMPLATE_FILES = {'新号': 'starter.json', '满级体验号': 'experience.json'}


def load_template(kind):
    if kind not in TEMPLATE_FILES: raise ValueError('请选择账号模板。')
    # The old experience.json contains synthetic battle receipts. Build the
    # user-facing templates with the same rules as the V0.2.0 in-game editor.
    from catalog_loader import load_catalog
    from editor_core.templates import create
    catalog = load_catalog()
    result = create(catalog, 'starter' if kind == '新号' else 'full_level', uid=1024)
    result['main']['nickname'] = '免费版本禁止倒卖'
    result['main']['self_desc'] = '开源免费版本，仅供学习与技术交流，禁止倒卖，版权归米哈游所有'
    if kind == '满级体验号':
        from avatars import enrich_experience_template
        result = enrich_experience_template(result, catalog)
        result['main']['scoin'], result['main']['hcoin'] = 100000, 1000
    result['main']['equipment_size_limit'] = max(
        result['main'].get('equipment_size_limit', 0), min_equipment_size_limit(result))
    return result


def save_new(target, result):
    target = Path(target)
    raw = (json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False)+'\n').encode('utf-8')
    parse(raw)
    # Creating a template must never replace an existing account.
    with target.open('xb') as f:
        f.write(raw); f.flush(); os.fsync(f.fileno())
    if target.read_bytes()!=raw: raise OSError('保存校验失败，请检查存储设备。')


class Editor:
    def __init__(self, root):
        self.root, self.source, self.original, self.data = root, None, None, None
        self._loaded_data = None
        self._editor_catalog = None
        self.avatar_base, self.avatar_edits, self._selected_avatar_id = {}, {}, None
        self._syncing_avatar_form = False
        root.title(f'BH3 V1.9存档修改器 {EDITOR_VERSION}')
        root.geometry('920x780');root.minsize(840,700)
        style=ttk.Style(root)
        if 'vista' in style.theme_names():style.theme_use('vista')
        outer=ttk.Frame(root,padding=16);outer.pack(fill='both',expand=True)
        ttk.Label(outer,text=f'BH3 V1.9存档修改器 {EDITOR_VERSION}',font=('Microsoft YaHei UI',16,'bold')).pack(anchor='w')
        ttk.Label(outer,text='打开存档，选择需要修改的内容，然后保存。').pack(anchor='w',pady=(2,10))
        toolbar=ttk.Frame(outer);toolbar.pack(fill='x')
        ttk.Button(toolbar,text='打开存档…',command=self.open).pack(side='left')
        self.new_kind=tk.StringVar(value='新号')
        ttk.Combobox(toolbar,textvariable=self.new_kind,values=list(TEMPLATE_FILES),state='readonly',width=16).pack(side='left',padx=(24,8))
        ttk.Button(toolbar,text='使用模板新建',command=self.new).pack(side='left')
        self.first_login=tk.BooleanVar(value=False)
        self.first_login_switch=ttk.Checkbutton(outer,text='首次登录（播放开场CG并自动进入第一关；仅新建且舰长等级=1可选）',variable=self.first_login,state='disabled')
        self.first_login_switch.pack(anchor='w',pady=(6,0))
        self.template_name=None
        self.info=tk.StringVar(value='尚未打开存档')
        ttk.Label(outer,textvariable=self.info,wraplength=860).pack(anchor='w',pady=8)

        notebook=ttk.Notebook(outer);notebook.pack(fill='both',expand=True)
        self.notebook=notebook
        tab_basic=ttk.Frame(notebook,padding=10)
        tab_avatars=ttk.Frame(notebook,padding=10)
        notebook.add(tab_basic,text='基础与关卡')
        notebook.add(tab_avatars,text='女武神调整')

        form=ttk.LabelFrame(tab_basic,text='基本信息与资源',padding=10);form.pack(fill='x')
        self.variables={};self.entries={};self.field_hints={}
        for row,(key,(label,limit)) in enumerate(FIELDS.items()):
            ttk.Label(form,text=label,width=12).grid(row=row,column=0,sticky='w',pady=3)
            var=tk.StringVar();entry=ttk.Entry(form,textvariable=var,width=28,state='disabled')
            entry.grid(row=row,column=1,sticky='ew',padx=8)
            hint='在游戏内修改' if key in ('nickname','self_desc') else ('1–80；修改后经验归零' if key == 'level' else ('请先打开存档' if key == 'equipment_size_limit' else f'0–{limit:,}'))
            hint_var=tk.StringVar(value=hint)
            ttk.Label(form,textvariable=hint_var).grid(row=row,column=2,sticky='w')
            self.variables[key],self.entries[key],self.field_hints[key]=var,entry,hint_var
        self.variables['level'].trace_add('write', self._on_level_change)
        self.first_login.trace_add('write', lambda *_: self.sync_avatar_controls())
        self.identity_hint=tk.StringVar(value='')
        ttk.Label(form,textvariable=self.identity_hint).grid(row=len(FIELDS),column=1,columnspan=2,sticky='w',padx=8)
        form.columnconfigure(1,weight=1)

        progress=ttk.LabelFrame(tab_basic,text='服装与关卡',padding=10);progress.pack(fill='x',pady=10)
        self.cycle=tk.StringVar(value='保持不变');self.template=tk.StringVar(value='保持不变');self.rank=tk.StringVar(value='保持不变')
        self.story=tk.BooleanVar(value=False);self.extra=tk.BooleanVar(value=False)
        ttk.Label(progress,text='剧情 / 轮回',width=12).grid(row=0,column=0,sticky='w',pady=4)
        ttk.Label(progress,text='请使用“深度编辑”选择具体关卡或剧情。',wraplength=550).grid(row=0,column=1,columnspan=2,sticky='w')
        ttk.Label(progress,text='深渊进度').grid(row=1,column=0,sticky='w',pady=4)
        ttk.Combobox(progress,textvariable=self.template,values=list(TEMPLATES),state='readonly',width=25).grid(row=1,column=1,sticky='w')
        ttk.Label(progress,text='深渊段位').grid(row=2,column=0,sticky='w',pady=4)
        ttk.Combobox(progress,textvariable=self.rank,values=list(RANKS),state='readonly',width=25).grid(row=2,column=1,sticky='w')
        ttk.Label(progress,text='深度进度编辑适用于 BH2017-LOCRENASCI V0.2.0；其他版本请先确认兼容性。',wraplength=690).grid(row=3,column=0,columnspan=3,sticky='w',pady=3)
        self.costumes=tk.StringVar(value='保持不变')
        ttk.Label(progress,text='服装解锁').grid(row=6,column=0,sticky='w',pady=4)
        ttk.Combobox(progress,textvariable=self.costumes,values=list(COSTUMES),state='readonly',width=25).grid(row=6,column=1,sticky='w')
        ttk.Label(progress,text='锁定时自动换回默认。',wraplength=300).grid(row=6,column=2,sticky='w',padx=8)

        self.avatar_gate_hint=tk.StringVar(value=f'请先打开存档（需舰长等级 ≥ {MIN_CAPTAIN_LEVEL} 级且非首次登录才可调整女武神，避免影响新手与家园引导）。')
        ttk.Label(tab_avatars,textvariable=self.avatar_gate_hint,wraplength=850).pack(anchor='w',pady=(0,8))
        av_split=ttk.Frame(tab_avatars);av_split.pack(fill='both',expand=True)
        cols=('id','name','unlocked','level','star','equip')
        self.avatar_tree=ttk.Treeview(av_split,columns=cols,show='headings',selectmode='browse',height=16)
        for col,title,w in (('id','ID',56),('name','女武神',140),('unlocked','状态',64),('level','等级',56),('star','评阶',56),('equip','推荐满装',76)):
            self.avatar_tree.heading(col,text=title)
            self.avatar_tree.column(col,width=w,anchor='center' if col!='name' else 'w')
        av_scroll=ttk.Scrollbar(av_split,orient='vertical',command=self.avatar_tree.yview)
        self.avatar_tree.configure(yscrollcommand=av_scroll.set)
        self.avatar_tree.pack(side='left',fill='both',expand=True)
        av_scroll.pack(side='left',fill='y')
        self.avatar_tree.bind('<<TreeviewSelect>>',self._on_avatar_select)

        av_panel=ttk.LabelFrame(av_split,text='选中女武神设置',padding=12);av_panel.pack(side='left',fill='y',padx=(12,0))
        self.av_title=tk.StringVar(value='请在左侧选择女武神')
        ttk.Label(av_panel,textvariable=self.av_title,font=('Microsoft YaHei UI',11,'bold'),wraplength=250).pack(anchor='w',pady=(0,8))
        self.av_unlocked=tk.BooleanVar(value=False)
        self.av_unlocked_chk=ttk.Checkbutton(av_panel,text='已解锁该女武神',variable=self.av_unlocked,command=self._commit_avatar_form)
        self.av_unlocked_chk.pack(anchor='w',pady=4)
        lv_row=ttk.Frame(av_panel);lv_row.pack(fill='x',pady=6)
        ttk.Label(lv_row,text='等级：',width=8).pack(side='left')
        self.av_level=tk.StringVar(value='1')
        self.av_level_entry=ttk.Entry(lv_row,textvariable=self.av_level,width=10)
        self.av_level_entry.pack(side='left')
        self.av_level_entry.bind('<FocusOut>',lambda *_: self._commit_avatar_form())
        self.av_level_entry.bind('<Return>',lambda *_: self._commit_avatar_form())
        st_row=ttk.Frame(av_panel);st_row.pack(fill='x',pady=6)
        ttk.Label(st_row,text='评阶：',width=8).pack(side='left')
        self.av_star=tk.StringVar(value='A')
        self.av_star_combo=ttk.Combobox(st_row,textvariable=self.av_star,values=list(LABEL_TO_STAR),state='readonly',width=8)
        self.av_star_combo.pack(side='left')
        self.av_star_combo.bind('<<ComboboxSelected>>',lambda *_: self._commit_avatar_form())
        self.av_full=tk.BooleanVar(value=False)
        self.av_full_chk=ttk.Checkbutton(av_panel,text='为该角色提供并穿戴推荐满装',variable=self.av_full,command=self._commit_avatar_form)
        self.av_full_chk.pack(anchor='w',pady=6)
        self.av_note=tk.StringVar(value='')
        ttk.Label(av_panel,textvariable=self.av_note,wraplength=250).pack(anchor='w',pady=6)
        self.av_reset_btn=ttk.Button(av_panel,text='重置当前女武神',command=self._reset_selected_avatar)
        self.av_reset_btn.pack(fill='x',pady=(10,4))
        self.av_reset_all_btn=ttk.Button(av_panel,text='重置全部女武神改动',command=self._reset_all_avatars)
        self.av_reset_all_btn.pack(fill='x',pady=4)

        # Reserve the footer before allocating remaining space to the tabs;
        # otherwise Tk may clip the save controls at high display scaling.
        actions=ttk.Frame(outer);actions.pack(side='bottom',fill='x',pady=8,before=notebook)
        self.preview_button=ttk.Button(actions,text='预览修改',command=self.preview);self.preview_button.pack(side='left')
        self.save_button=ttk.Button(actions,text='保存',command=lambda:self.write(False));self.save_button.pack(side='right')
        ttk.Button(actions,text='另存为…',command=lambda:self.write(True)).pack(side='right',padx=8)
        self.status=tk.StringVar(value='')
        ttk.Label(outer,textvariable=self.status,wraplength=860).pack(side='bottom',anchor='w',before=notebook)
        from advanced_editor import create_tab
        self.advanced_tab = create_tab(notebook, self._working_snapshot,
                                       self._replace_working_snapshot, self._get_editor_catalog)
        notebook.bind('<<NotebookTabChanged>>', self._on_tab_changed, add='+')
        self.sync_avatar_controls()
        root.protocol('WM_DELETE_WINDOW',self.close)

    def _get_editor_catalog(self):
        if self._editor_catalog is None:
            from catalog_loader import load_catalog
            self._editor_catalog = load_catalog()
        return self._editor_catalog

    def _working_snapshot(self):
        # Include pending edits in the original tabs before a deep edit is made.
        return self.candidate()[0]

    def _replace_working_snapshot(self, account):
        if self.data is None:
            raise ValueError('请先打开存档。')
        # Preserve the original on-disk bytes for conflict detection and backup.
        # Rebinding merges changes from all tabs into one in-memory working copy.
        self.bind_data(copy.deepcopy(account), self.original, self.source, reset_reference=False)
        self.status.set('修改已加入工作副本，请预览并保存。')

    def _on_tab_changed(self, event=None):
        if self.notebook.select() == str(self.advanced_tab):
            self.advanced_tab.refresh()

    def _effective_captain_level(self):
        try:
            return int(self.variables['level'].get())
        except (ValueError, KeyError):
            return self.data['main'].get('level', 1) if self.data else 1

    def _on_level_change(self, *args):
        self.sync_first_login()
        self.sync_equipment_hint()
        self.sync_avatar_controls()

    def sync_equipment_hint(self):
        if self.data is None or 'equipment_size_limit' not in self.data['main']:
            self.field_hints['equipment_size_limit'].set('当前存档无此字段')
            return
        lv = max(1, min(80, self._effective_captain_level()))
        tier_floor = expected_equipment_size_limit(lv)
        owned = equipment_count(self.data)
        floor = max(tier_floor, owned)
        self.field_hints['equipment_size_limit'].set(
            f'{floor:,}–{FIELDS["equipment_size_limit"][1]:,}（等级档位 {tier_floor}，已有装备 {owned} 件）'
        )

    def sync_avatar_controls(self):
        if self.data is None:
            allowed = False
            msg = f'请先打开存档（需舰长等级 ≥ {MIN_CAPTAIN_LEVEL} 级且非首次登录才可调整女武神）。'
        else:
            lv = self._effective_captain_level()
            first = self.first_login.get() if (self.source is None and self.template_name == '新号') else bool(self.data.get('is_first_login', False))
            if first:
                allowed = False
                msg = '首次登录引导存档不可调整女武神；请先关闭首次登录且舰长等级 ≥ 15 级。'
            elif lv < MIN_CAPTAIN_LEVEL:
                allowed = False
                msg = f'当前舰长等级 {lv} < {MIN_CAPTAIN_LEVEL}，为避免影响新手与家园引导已锁定女武神调整；升至 {MIN_CAPTAIN_LEVEL} 级以上即可解锁。'
            else:
                allowed = True
                msg = f'已解锁女武神调整（当前舰长等级 {lv}：女武神等级上限 {lv}，评阶不低于初始星级）。'
        self.avatar_gate_hint.set(msg)
        state = 'normal' if allowed else 'disabled'
        for w in (self.av_unlocked_chk, self.av_level_entry, self.av_full_chk, self.av_reset_btn, self.av_reset_all_btn):
            w.configure(state=state)
        self.av_star_combo.configure(state='readonly' if allowed else 'disabled')

    def _refresh_avatar_tree(self):
        for iid in self.avatar_tree.get_children():
            self.avatar_tree.delete(iid)
        for aid, name, *_ in AVATAR_CATALOG:
            cfg = self.avatar_edits.get(aid, self.avatar_base.get(aid, {'unlocked': False, 'level': 1, 'star': 1, 'full_equip': False}))
            self.avatar_tree.insert(
                '', 'end', iid=str(aid),
                values=(
                    aid, name,
                    '已解锁' if cfg['unlocked'] else '未解锁',
                    cfg['level'] if cfg['unlocked'] else '-',
                    STAR_LABELS.get(cfg['star'], '-') if cfg['unlocked'] else '-',
                    '是' if cfg.get('full_equip') else '否',
                ),
            )

    def _on_avatar_select(self, event=None):
        sel = self.avatar_tree.selection()
        if not sel:
            return
        aid = int(sel[0])
        self._selected_avatar_id = aid
        meta = AVATAR_META[aid]
        cfg = self.avatar_edits.get(aid, self.avatar_base[aid])
        self._syncing_avatar_form = True
        try:
            base_note = f'（需先解锁{AVATAR_META[meta["base_avatar_id"]]["name"]}）' if meta['base_avatar_id'] else ''
            self.av_title.set(f'{aid} · {meta["name"]}{base_note}')
            self.av_unlocked.set(bool(cfg['unlocked']))
            self.av_level.set(str(cfg['level']))
            self.av_star.set(STAR_LABELS[cfg['star']])
            self.av_full.set(bool(cfg.get('full_equip', False)))
            allowed_stars = [STAR_LABELS[s] for s in range(meta['unlock_star'], 6)]
            self.av_star_combo.configure(values=allowed_stars)
            self.av_note.set(f'初始评阶：{STAR_LABELS[meta["unlock_star"]]}；满装会为角色生成推荐满级武器与三件圣痕。')
        finally:
            self._syncing_avatar_form = False

    def _commit_avatar_form(self):
        if self._syncing_avatar_form or self._selected_avatar_id is None or self.data is None:
            return
        aid = self._selected_avatar_id
        meta = AVATAR_META[aid]
        try:
            lv = int(self.av_level.get().strip())
        except ValueError:
            lv = self.avatar_edits.get(aid, self.avatar_base[aid])['level']
        star = LABEL_TO_STAR.get(self.av_star.get(), meta['unlock_star'])
        star = max(meta['unlock_star'], min(5, star))
        unlocked = bool(self.av_unlocked.get())
        full_equip = bool(self.av_full.get()) and unlocked
        if not unlocked and self.av_full.get():
            self.av_full.set(False)
        new_cfg = {'unlocked': unlocked, 'level': lv, 'star': star, 'full_equip': full_equip}
        if new_cfg == self.avatar_base[aid]:
            self.avatar_edits.pop(aid, None)
        else:
            self.avatar_edits[aid] = new_cfg
        self._refresh_avatar_tree()
        self.avatar_tree.selection_set(str(aid))

    def _reset_selected_avatar(self):
        if self._selected_avatar_id is None:
            return
        self.avatar_edits.pop(self._selected_avatar_id, None)
        self._refresh_avatar_tree()
        self.avatar_tree.selection_set(str(self._selected_avatar_id))
        self._on_avatar_select()

    def _reset_all_avatars(self):
        self.avatar_edits.clear()
        self._refresh_avatar_tree()
        if self._selected_avatar_id is not None:
            self.avatar_tree.selection_set(str(self._selected_avatar_id))
            self._on_avatar_select()

    def sync_first_login(self, *args):
        try:
            level_one = int(self.variables['level'].get()) == 1
        except ValueError:
            level_one = False
        if not level_one:
            self.first_login.set(False)
        enabled = self.source is None and self.template_name == '新号' and level_one
        self.first_login_switch.configure(state='normal' if enabled else 'disabled')

    def dirty(self):
        if self.data is not None and self.data != self._loaded_data:return True
        if self.data is not None and (self.costumes.get() != '保持不变' or bool(self.avatar_edits)):return True
        return self.data is not None and (self.source is None or self.rank.get()!='保持不变' or self.template.get()!='保持不变' or self.cycle.get()!='保持不变' or self.story.get() or self.extra.get() or any(v.get()!=str(self.data['main'][k]) for k,v in self.variables.items() if k in self.data['main']))

    def close(self):
        if not self.dirty() or messagebox.askyesno('未保存的修改','放弃当前修改并退出？'):self.root.destroy()

    def load(self,path):
        raw=Path(path).read_bytes();data=parse(raw)
        self.bind_data(data, raw, Path(path))

    def bind_data(self,data,raw,path=None,*,reset_reference=True):
        self.source,self.original,self.data=path,raw,data
        if reset_reference:self._loaded_data=copy.deepcopy(data)
        if path is not None: self.template_name=None
        self.avatar_base=current_avatar_states(data)
        self.avatar_edits={}
        self._selected_avatar_id=None
        for k,var in self.variables.items():
            var.set(str(data['main'][k]) if k in data['main'] else '')
            state = 'disabled' if k not in data['main'] else ('readonly' if k in IDENTITY_FIELDS else 'normal')
            self.entries[k].configure(state=state)
        self.rank.set('保持不变');self.template.set('保持不变');self.cycle.set('保持不变');self.story.set(False);self.extra.set(False)
        self.costumes.set('保持不变')
        self.first_login.set(bool(data.get('is_first_login',False)))
        self.sync_first_login()
        self.sync_equipment_hint()
        self.sync_avatar_controls()
        self._refresh_avatar_tree()
        if AVATAR_CATALOG:
            first_aid=str(AVATAR_CATALOG[0][0])
            self.avatar_tree.selection_set(first_aid)
            self._on_avatar_select()
        world=data.get('openworld_data',{});c=world.get('cycle')
        cycle_name={1:'第一轮',2:'第二轮',3:'第三轮',4:'第四轮 PART1'}.get(c,'未开启')
        rank_name=next((k for k,v in RANKS.items() if v==data.get('endless_runtime',{}).get('group')), '未开启')
        self.identity_hint.set('昵称和签名请在游戏内修改')
        self.info.set(f'{Path(path).name if path is not None else self.template_name}  ·  舰长等级 {data["main"].get("level","未知")}  ·  樱色轮回：{cycle_name}  ·  深渊：{rank_name}')
        if hasattr(self, 'advanced_tab'):
            self.advanced_tab.refresh()

    def new(self):
        if self.dirty() and not messagebox.askyesno('未保存的修改','放弃当前修改并新建存档？'):return
        try:
            kind=self.new_kind.get()
            data=load_template(kind)
            self.template_name=kind
            self.bind_data(data,json.dumps(data,ensure_ascii=False).encode('utf-8'))
            self.status.set('模板已载入。可以继续修改，点击保存生成新文件。')
        except Exception as e:messagebox.showerror('无法新建',str(e))

    def open(self):
        if self.dirty() and not messagebox.askyesno('未保存的修改','放弃当前修改并打开其他存档？'):return
        path=filedialog.askopenfilename(title='打开存档',filetypes=[('存档文件','*.json'),('所有文件','*.*')])
        if path:
            try:self.load(path);self.status.set('')
            except Exception as e:messagebox.showerror('无法读取',str(e))

    def candidate(self):
        if self.data is None:raise ValueError('请先打开存档。')
        self._commit_avatar_form()
        values={k:v.get() for k,v in self.variables.items() if k in self.data['main']}
        result,changes=edit(self.data,values,TEMPLATES[self.template.get()],cycle=CYCLES[self.cycle.get()],story=self.story.get(),extra=self.extra.get(),rank=RANKS[self.rank.get()],costumes=COSTUMES[self.costumes.get()],avatar_edits=self.avatar_edits)
        if self.source is None and self.template_name=='新号':
            enabled=self.first_login.get() and result['main'].get('level') == 1
            if enabled != result.get('is_first_login',False):
                result['is_first_login']=enabled
                changes.append('首次登录：'+('开启' if enabled else '关闭'))
        if result['main'].get('level') != 1 and result.get('is_first_login') is True:
            result['is_first_login']=False
            changes.append('首次登录：关闭（舰长等级不为1）')
        if self.data != self._loaded_data:
            changes = describe_working_changes(self._loaded_data, result)
        if self.source is None:changes.insert(0,'创建'+str(self.template_name)+'存档')
        return result,changes

    def preview(self):
        try:
            _,changes=self.candidate();messagebox.showinfo('修改预览','\n'.join(changes) or '没有修改。')
        except Exception as e:messagebox.showerror('暂时无法修改',str(e))

    def confirm_save(self, changes):
        dialog=tk.Toplevel(self.root)
        dialog.title('确认修改');dialog.transient(self.root);dialog.resizable(False,False)
        panel=ttk.Frame(dialog,padding=20);panel.pack(fill='both',expand=True)
        ttk.Label(panel,text='\n'.join(changes),wraplength=560).pack(anchor='w')
        tk.Label(panel,text='登录账号和密码可随意输入，本地不设置检查',
                 foreground='#8A3500',background='#FFF2C6',font=('Microsoft YaHei UI',11,'bold'),
                 padx=12,pady=12,wraplength=540).pack(fill='x',pady=(16,12))
        ttk.Label(panel,text='是否保存以上修改？').pack(anchor='w')
        actions=ttk.Frame(panel);actions.pack(fill='x',pady=(14,0))
        accepted=False
        def finish(value=False):
            nonlocal accepted
            accepted=value
            dialog.destroy()
        ttk.Button(actions,text='保存',command=lambda:finish(True)).pack(side='right')
        cancel=ttk.Button(actions,text='取消',command=finish);cancel.pack(side='right',padx=8)
        dialog.protocol('WM_DELETE_WINDOW',finish)
        dialog.bind('<Escape>',lambda event:finish())
        dialog.grab_set();cancel.focus_set()
        self.root.wait_window(dialog)
        return accepted

    def write(self,save_as):
        try:
            result,changes=self.candidate()
            if not changes:messagebox.showinfo('保存','没有修改。');return
            target=self.source
            if save_as or self.source is None:
                name=filedialog.asksaveasfilename(title='另存存档',initialfile='account.json' if self.source is None else 'account.edited.json',defaultextension='.json',filetypes=[('存档文件','*.json')])
                if not name:return
                target=Path(name)
            if not self.confirm_save(changes):return
            if self.source is None:
                save_new(target,result)
            else:
                save(self.source,self.original,target,result)
            self.load(target);self.status.set('保存成功。')
            messagebox.showinfo('保存成功','请将修改后的文件以 account.json 名称放回原存档目录。')
        except Exception as e:messagebox.showerror('保存未完成',str(e))


def packaged_self_test(report):
    """Exercise bundled Tcl/Tk and save code using synthetic data only."""
    sample = {'schema': 1, 'main': {'nickname': '测试', 'self_desc': 'Hello',
              'scoin': 10, 'hcoin': 20, 'stamina': 30, 'friends_point': 0},
              'avatar_list': [], 'keep': {'value': [1, 2, 3]}}
    sample['main']['level'] = 79
    sample['main']['exp'] = 123
    now=int(time.time())
    sample['endless_runtime']={'begin':now-60,'end':now+600,'group':1,'progress':0,'max_progress':0,'progress_time':now-60,'active':None}
    sample['stage_list'] = []
    sample['stage_runtime'] = {'schema':1,'active':None,'settlements':[]}
    sample['openworld_data'] = {'cycle':1,'finish_story_id_list':[],'cur_story_list':[]}
    sample['openworld_runtime'] = {'schema':1,'active':None,'receipts':{}}
    with tempfile.TemporaryDirectory(prefix='bh3-editor-test-') as folder:
        source = Path(folder) / 'account.json'
        original = json.dumps(sample, ensure_ascii=False).encode('utf-8')
        source.write_bytes(original)
        root = tk.Tk()
        root.withdraw()
        app = Editor(root)
        app.load(source)
        root.update()
        app.variables['scoin'].set('1000')
        app.variables['level'].set('80')
        app.rank.set('红莲深渊')
        result, changes = app.candidate()
        assert result['endless_runtime']['group']==6
        assert result['main']['level'] == 80 and result['main']['exp'] == 0
        assert changes and result['keep'] == sample['keep']
        assert result['stage_list'] == [] and result['stage_runtime']['settlements'] == []
        from editor_engine import apply as apply_deep
        edited = apply_deep(result, app._get_editor_catalog(), {'op': 'captain', 'friends_point': 123})
        app._replace_working_snapshot(edited)
        result, changes = app.candidate()
        assert app.dirty() and changes and result['main']['friends_point'] == 123
        assert result['main']['scoin'] == 1000 and result['main']['level'] == 80
        backup = save(source, original, source, result)
        assert backup.read_bytes() == original
        assert parse(source.read_bytes())['main']['scoin'] == 1000
        for kind in TEMPLATE_FILES:
            app.new_kind.set(kind)
            data=load_template(kind)
            app.template_name=kind
            app.bind_data(data,json.dumps(data,ensure_ascii=False).encode('utf-8'))
            assert all(str(app.entries[k]['state'])=='readonly' for k in IDENTITY_FIELDS)
            result,changes=app.candidate()
            assert changes and app.source is None
            target=Path(folder)/TEMPLATE_FILES[kind]
            save_new(target,result)
            assert parse(target.read_bytes())==data
            if kind == '新号':
                assert str(app.first_login_switch['state']) == 'normal'
                app.first_login.set(True)
                enabled, enabled_changes = app.candidate()
                assert enabled['is_first_login'] is True
                assert any('首次登录' in change for change in enabled_changes)
                expected = dict(data, is_first_login=True)
                assert enabled == expected
                for level in ('2', '80', ''):
                    app.variables['level'].set('1')
                    app.first_login.set(True)
                    app.variables['level'].set(level)
                    assert not app.first_login.get()
                    assert str(app.first_login_switch['state']) == 'disabled'
                    if level:
                        app.first_login.set(True)  # Saving must also enforce level.
                        assert app.candidate()[0]['is_first_login'] is False
                app.variables['level'].set('1')
                app.first_login.set(False)
                assert str(app.first_login_switch['state']) == 'normal'
                assert app.candidate()[0] == data
            else:
                assert str(app.first_login_switch['state']) == 'disabled'
            app.load(target)
            assert str(app.first_login_switch['state']) == 'disabled'
            assert all(str(app.entries[k]['state'])=='readonly' for k in IDENTITY_FIELDS)
            app.variables['nickname'].set('更名')
            try: app.candidate()
            except ValueError: pass
            else: raise AssertionError('Template identity modification accepted')
        app.load(source)
        assert all(str(app.entries[k]['state'])=='readonly' for k in IDENTITY_FIELDS)
        sample['avatar_list']=[{'avatar_id':101,'dress_list':[]}]
        app.bind_data(sample,json.dumps(sample).encode(),source)
        assert app.costumes.get()=='保持不变' and not app.dirty()
        app.costumes.set('全部解锁')
        assert app.dirty()
        dressed, dress_changes=app.candidate()
        assert 50019 in dressed['avatar_list'][0]['dress_list']
        assert 50019 in dressed['has_got_item_id_list']
        target=Path(folder)/'costumes.json'
        save_new(target,dressed);app.load(target)
        assert app.costumes.get()=='保持不变' and not app.dirty()
        app.costumes.set('全部锁定')
        assert app.candidate()[0]['avatar_list'][0]['dress_list']==[]
        root.destroy()
    Path(report).write_text(json.dumps({'status': 'passed', 'checks':
        ['bundled Tk widgets', 'load synthetic save', 'edit whitelist', 'standalone deep-edit catalog',
         'merge deep and basic edits in memory', 'preserve unknown data', 'backup and save readback',
         'identity readonly and validation', 'new-account first-login toggle on/off and save diff',
         'level changes cancel first-login; save enforces level1', 'costume unlock/lock and save/reload']}, indent=2), encoding='utf-8')


if __name__ == '__main__':
    import sys
    if len(sys.argv) == 3 and sys.argv[1] == '--self-test':
        packaged_self_test(sys.argv[2])
    else:
        root = tk.Tk()
        Editor(root)
        root.mainloop()
