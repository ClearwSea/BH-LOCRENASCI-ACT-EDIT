"""Detailed Tkinter views for the offline save editor.

All operations edit a caller-owned in-memory account via editor_engine; this
module deliberately does not open, save, or replace any account files.
"""
import re
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog


class AdvancedEditor(ttk.Frame):
    def __init__(self, notebook, get_account, set_account, get_catalog):
        super().__init__(notebook, padding=6)
        self.get_account, self.set_account, self.get_catalog = get_account, set_account, get_catalog
        self.pages = ttk.Notebook(self)
        self.pages.pack(fill='both', expand=True)
        self._build_captain()
        self._build_avatar()
        self._build_costume()
        self._build_equipment()
        self._build_material()
        self._build_story()
        self._build_world()
        self._build_cabin()
        self.pages.bind('<<NotebookTabChanged>>', lambda event: self.refresh())

    def _account(self):
        return getattr(self, '_cached_account', {})

    def _catalog(self):
        return getattr(self, '_cached_catalog', {})

    def _rows(self, name):
        value = self._catalog().get(name, [])
        return value if isinstance(value, list) else []

    @staticmethod
    def _find(rows, key, value):
        return next((row for row in rows if isinstance(row, dict) and row.get(key) == value), None)

    def _label(self, row, key, identity):
        raw = row.get(key, '') if row else ''
        translated = getattr(self, '_text_cache', {}).get(raw)
        if translated:
            raw = translated
        elif not raw or str(raw).isdigit() or str(raw).startswith(('Avatar_', 'Material_', 'Weapon_', 'Stigmata_', 'Dress_', 'SubSkill_')):
            return 'ID ' + str(identity)
        return re.sub(r'<[^>]+>', '', str(raw))

    def _apply(self, operation):
        try:
            import editor_engine
            account, catalog = self.get_account(), self.get_catalog()
            if not isinstance(account, dict):
                raise ValueError('请先打开或新建存档。')
            if not isinstance(catalog, dict) or not catalog:
                raise ValueError('当前版本的编辑目录不可用，请先配置编辑目录。')
            changed = editor_engine.apply(account, catalog, operation)
            self.set_account(changed)
            self.refresh()
            return True
        except Exception as exc:
            messagebox.showerror('无法应用修改', str(exc), parent=self)
            return False

    def _number(self, title, current, hint='请输入整数。'):
        return simpledialog.askinteger(title, hint, initialvalue=current, parent=self)

    def _pick(self, title, choices):
        """Select a (label, value) without trusting labels to be unique."""
        if not choices:
            messagebox.showinfo(title, '没有可选项。', parent=self)
            return None
        dialog = tk.Toplevel(self)
        dialog.title(title); dialog.transient(self.winfo_toplevel())
        dialog.geometry('620x460'); dialog.minsize(380, 260)
        body = ttk.Frame(dialog, padding=10); body.pack(fill='both', expand=True)
        query = tk.StringVar()
        ttk.Entry(body, textvariable=query).pack(fill='x', pady=(0, 6))
        listing = tk.Listbox(body, exportselection=False)
        listing.pack(side='left', fill='both', expand=True)
        scroll = ttk.Scrollbar(body, orient='vertical', command=listing.yview)
        scroll.pack(side='right', fill='y'); listing.configure(yscrollcommand=scroll.set)
        visible = []
        def populate(*_):
            listing.delete(0, 'end'); visible.clear()
            q = query.get().strip().casefold()
            for label, value in choices:
                if not q or q in str(label).casefold():
                    visible.append(value); listing.insert('end', label)
        query.trace_add('write', populate); populate()
        selected = []
        def choose(event=None):
            indexes = listing.curselection()
            if indexes:
                selected.append(visible[indexes[0]]); dialog.destroy()
        ttk.Button(dialog, text='选择', command=choose).pack(pady=(0, 8))
        listing.bind('<Double-1>', choose); dialog.bind('<Escape>', lambda _: dialog.destroy())
        dialog.grab_set(); self.wait_window(dialog)
        return selected[0] if selected else None

    def _tree(self, parent, columns, headings=None):
        pane = ttk.Frame(parent); pane.pack(fill='both', expand=True)
        tree = ttk.Treeview(pane, columns=columns, show='headings', selectmode='browse', height=10)
        for col, title in zip(columns, headings or columns):
            tree.heading(col, text=title); tree.column(col, width=115, minwidth=60, stretch=True)
        scroll = ttk.Scrollbar(pane, orient='vertical', command=tree.yview)
        horizontal = ttk.Scrollbar(pane, orient='horizontal', command=tree.xview)
        horizontal.pack(side='bottom', fill='x')
        tree.configure(yscrollcommand=scroll.set, xscrollcommand=horizontal.set)
        tree.pack(side='left', fill='both', expand=True)
        scroll.pack(side='right', fill='y')
        return tree

    @staticmethod
    def _populate(tree, rows):
        selection = tree.selection()
        selected = selection[0] if selection else None
        tree.delete(*tree.get_children())
        for iid, values in rows:
            tree.insert('', 'end', iid=str(iid), values=values)
        if selected and tree.exists(selected):
            tree.selection_set(selected); tree.focus(selected)

    @staticmethod
    def _selected(tree):
        selected = tree.selection()
        return selected[0] if selected else None

    def _page(self, title, subtitle=''):
        frame = ttk.Frame(self.pages, padding=6); self.pages.add(frame, text=title)
        if subtitle:
            ttk.Label(frame, text=subtitle, wraplength=780).pack(anchor='w', pady=(0, 6))
        return frame

    def _bar(self, parent, buttons):
        bar = ttk.Frame(parent); bar.pack(fill='x', pady=6)
        for title, callback in buttons:
            ttk.Button(bar, text=title, command=callback).pack(side='left', padx=(0, 5))
        return bar

    def _search(self, parent, callback):
        bar = ttk.Frame(parent); bar.pack(fill='x', pady=(0, 6))
        ttk.Label(bar, text='搜索名称 / ID：').pack(side='left')
        query = tk.StringVar()
        ttk.Entry(bar, textvariable=query).pack(side='left', fill='x', expand=True)
        query.trace_add('write', lambda *_: callback())
        return query, bar

    def _build_captain(self):
        frame = self._page('舰长', '读取当前状态；名称和签名在游戏中修改。')
        self.captain_identity = tk.StringVar()
        ttk.Label(frame, textvariable=self.captain_identity).pack(anchor='w')
        self._bar(frame, [('修改所选数值', self._captain_edit)])
        self.captain_tree = self._tree(frame, ('field', 'value', 'range'), ('项目', '当前值', '允许范围'))
        self.captain_tree.bind('<Double-1>', lambda e: self._captain_edit())

    def _refresh_captain(self):
        account = self._account(); main = account.get('main', {})
        if not account:
            self.captain_identity.set('请先打开或新建存档。')
            self._populate(self.captain_tree, [])
            return
        self.captain_identity.set('名称：%s    签名：%s' % (main.get('nickname', '—'), main.get('self_desc', '—')))
        names = {'level':'等级', 'scoin':'金币', 'hcoin':'水晶', 'stamina':'体力', 'friends_point':'友情点',
                 'skill_point':'技能点', 'skill_point_limit':'技能点上限', 'equipment_size_limit':'装备容量'}
        try:
            import editor_engine
            limits = editor_engine.limits(account, self._catalog()) if account else {}
        except Exception:
            limits = {}
        rows = []
        for key, name in names.items():
            if key not in main and key != 'friends_point': continue
            bound = limits.get(key, {})
            interval = '%s – %s' % (bound.get('min', '?'), bound.get('max', '?'))
            rows.append((key, (name, main.get(key, 0), interval)))
        self._populate(self.captain_tree, rows)

    def _captain_edit(self):
        key = self._selected(self.captain_tree)
        if not key: return
        item = self.captain_tree.item(key, 'values')
        current = self._account().get('main', {}).get(key, 0)
        value = self._number(item[0], current, '允许范围：' + str(item[2]))
        if value is not None: self._apply({'op':'captain', key:value})

    def _build_avatar(self):
        frame = self._page('女武神与技能')
        self.avatar_query, _ = self._search(frame, self._refresh_avatar)
        self._bar(frame, [('解锁 / 评阶', lambda: self._avatar_number('star', '解锁与评阶（0 为锁定）')),
                          ('等级', lambda: self._avatar_number('level', '等级')),
                          ('互动好感', lambda: self._avatar_number('touch_goodfeel', '互动好感')),
                          ('出战好感', lambda: self._avatar_number('stage_goodfeel', '出战好感')),
                          ('碎片', lambda: self._avatar_number('fragment', '角色碎片'))])
        self.avatar_tree = self._tree(frame, ('id','name','star','level','fragment','touch','stage','dress'), ('ID','女武神','评阶','等级','碎片','互动好感','出战好感','当前服装 ID'))
        self.avatar_tree.bind('<<TreeviewSelect>>', lambda e: self._refresh_skills())
        self._bar(frame, [('修改所选技能', self._skill_edit), ('装备到所选角色', self._equip_for_avatar),
                          ('交换武器', self._exchange_weapon), ('切回默认服装', self._avatar_default_dress)])
        self.skill_tree = self._tree(frame, ('skill','sub','name','level','max'), ('技能 ID','子技能 ID','技能','当前等级','上限'))
        self.skill_tree.bind('<Double-1>', lambda e: self._skill_edit())

    def _refresh_avatar(self):
        if not hasattr(self, 'avatar_tree'): return
        q = self.avatar_query.get().strip().casefold(); account = self._account()
        owned = account.get('avatar_list', [])
        rows = []
        for meta in self._rows('avatardata'):
            identity = meta.get('avatarID'); name = self._label(meta, 'fullName', identity)
            if type(identity) is not int or identity <= 0 or q not in (name + ' ' + str(identity)).casefold(): continue
            avatar = self._find(owned, 'avatar_id', identity) or {}
            rows.append((identity, (identity,name,avatar.get('star',0),avatar.get('level',1),avatar.get('fragment',0),avatar.get('touch_goodfeel',0),avatar.get('stage_goodfeel',0),avatar.get('dress_id',0))))
        self._populate(self.avatar_tree, rows); self._refresh_skills()

    def _avatar_number(self, field, title):
        identity = self._selected(self.avatar_tree)
        if not identity: return
        avatar = self._find(self._account().get('avatar_list', []), 'avatar_id', int(identity)) or {}
        current = avatar.get(field, 1 if field == 'level' else 0)
        value = self._number(title, current, '当前：%s；输入新值后按当前表校验。' % current)
        if value is not None: self._apply({'op':'avatar','avatar_id':int(identity),field:value})

    def _refresh_skills(self):
        if not hasattr(self, 'skill_tree'): return
        selected = self._selected(self.avatar_tree); rows = []
        if selected:
            aid = int(selected); avatar = self._find(self._account().get('avatar_list', []), 'avatar_id', aid) or {}
            meta = self._find(self._rows('avatardata'), 'avatarID', aid) or {}
            if avatar.get('star',0) > 0:
                for skill in self._rows('avatarsubskilldata'):
                    sid, subid = skill.get('skillId'), skill.get('avatarSubSkillId')
                    if sid not in meta.get('skillList', []) or type(subid) is not int or subid <= 0: continue
                    owned = self._find(avatar.get('skill_list', []), 'skill_id', sid) or {}
                    sub = self._find(owned.get('sub_skill_list', []), 'sub_skill_id', subid) or {}
                    rows.append(('%s:%s' % (sid,subid), (sid,subid,self._label(skill,'name',subid),sub.get('level',0),skill.get('maxLv','?'))))
        self._populate(self.skill_tree, rows)

    def _skill_edit(self):
        aid, key = self._selected(self.avatar_tree), self._selected(self.skill_tree)
        if not aid or not key: return
        sid, subid = map(int, key.split(':')); values = self.skill_tree.item(key, 'values')
        level = self._number(str(values[2]), int(values[3]), '允许范围：0 – ' + str(values[4]))
        if level is not None: self._apply({'op':'skill','avatar_id':int(aid),'skill_id':sid,'sub_skill_id':subid,'level':level})

    def _equip_for_avatar(self):
        aid = self._selected(self.avatar_tree)
        if not aid: return
        aid = int(aid)
        slot = self._pick('选择装备槽位', [('武器',1),('圣痕上',2),('圣痕中',3),('圣痕下',4)])
        if slot is None: return
        items = [] if slot == 1 else [('卸下', 0)]
        for kind in ('weapon','stigmata'):
            if (slot == 1) != (kind == 'weapon'): continue
            for item in self._account().get(kind+'_list', []):
                meta = self._find(self._rows('weapondata' if kind == 'weapon' else 'stigmatadata'),'ID',item.get('id')) or {}
                if kind == 'stigmata' and meta.get('baseType') != slot-1: continue
                uid = item.get('unique_id'); items.append(('%s · 实例 %s · %s' % (self._label(meta,'displayTitle',item.get('id')),uid,self._owner(uid)),uid))
        uid = self._pick('选择装备', items)
        if uid is not None: self._apply({'op':'equipment_equip','avatar_id':aid,'slot':slot,'unique_id':uid})

    def _avatar_default_dress(self):
        aid = self._selected(self.avatar_tree)
        if aid:
            self._apply({'op':'costume','avatar_id':int(aid),'equip':0})

    def _exchange_weapon(self):
        aid = self._selected(self.avatar_tree)
        if not aid: return
        choices = []
        for avatar in self._account().get('avatar_list', []):
            identity = avatar.get('avatar_id')
            if identity == int(aid) or avatar.get('star',0) <= 0: continue
            meta = self._find(self._rows('avatardata'), 'avatarID', identity) or {}
            choices.append(('%s #%s' % (self._label(meta,'fullName',identity),identity),identity))
        other = self._pick('选择交换武器的角色', choices)
        if other is not None: self._apply({'op':'equipment_exchange','avatar_id_1':int(aid),'avatar_id_2':other})

    def _build_costume(self):
        frame = self._page('服装', '逐套解锁、锁定或切换；锁定正在穿着的服装会切回默认。')
        self.costume_query, _ = self._search(frame, self._refresh_costume)
        self._bar(frame, [('解锁 / 锁定所选', self._costume_toggle), ('切换到角色', self._costume_equip),
                          ('解锁全部', self._costume_all)])
        self.costume_tree = self._tree(frame, ('id','name','state','avatars'), ('ID','服装','状态','适用角色 ID'))

    def _refresh_costume(self):
        if not hasattr(self, 'costume_tree'): return
        q = self.costume_query.get().strip().casefold(); owned = self._account().get('has_got_item_id_list', [])
        rows = []
        for item in self._rows('dressdata'):
            identity, avatars = item.get('dressID'), item.get('avatarIDList', [])
            if item.get('dressType') != 1 or type(identity) is not int or identity <= 0 or not avatars: continue
            name = self._label(item,'name',identity)
            if q not in (name + ' ' + str(identity)).casefold(): continue
            rows.append((identity, (identity,name,'已解锁' if identity in owned else '未解锁',', '.join(map(str,avatars)))))
        self._populate(self.costume_tree, rows)

    def _costume_toggle(self):
        selected = self._selected(self.costume_tree)
        if selected:
            identity = int(selected); owned = identity in self._account().get('has_got_item_id_list', [])
            self._apply({'op':'costume','dress_id':identity,'owned':not owned})

    def _costume_equip(self):
        selected = self._selected(self.costume_tree)
        if not selected: return
        identity = int(selected); meta = self._find(self._rows('dressdata'),'dressID',identity) or {}
        choices = []
        for aid in meta.get('avatarIDList', []):
            avatar = self._find(self._account().get('avatar_list', []),'avatar_id',aid)
            if not avatar or avatar.get('star',0) <= 0: continue
            ameta = self._find(self._rows('avatardata'),'avatarID',aid) or {}
            choices.append(('%s #%s' % (self._label(ameta,'fullName',aid),aid),aid))
        aid = self._pick('选择穿着角色', choices)
        if aid is not None: self._apply({'op':'costume','avatar_id':aid,'equip':identity})

    def _costume_all(self):
        if messagebox.askyesno('解锁全部服装', '为所有适用角色解锁全部服装？', parent=self):
            self._apply({'op':'costume_all','owned':True})

    def _owner(self, uid):
        if not uid: return '未穿戴'
        fields = ('weapon_unique_id','stigmata_unique_id_1','stigmata_unique_id_2','stigmata_unique_id_3')
        for avatar in self._account().get('avatar_list', []):
            if uid in (avatar.get(key,0) for key in fields):
                aid = avatar.get('avatar_id'); meta = self._find(self._rows('avatardata'),'avatarID',aid) or {}
                return self._label(meta,'fullName',aid)
        return '未穿戴'

    def _build_equipment(self):
        frame = self._page('装备', '按当前表校验等级、经验、穿戴关系和进化信息；删除已穿戴装备前请先换装。')
        self.equipment_query, bar = self._search(frame, self._refresh_equipment)
        self.equipment_kind = tk.StringVar(value='全部')
        kind = ttk.Combobox(bar, textvariable=self.equipment_kind, values=('全部','武器','圣痕上','圣痕中','圣痕下'), state='readonly', width=9)
        kind.pack(side='left', padx=5); kind.bind('<<ComboboxSelected>>', lambda e:self._refresh_equipment())
        self._bar(frame, [('添加',self._equipment_add), ('等级',lambda:self._equipment_number('level','装备等级')),
                          ('经验',lambda:self._equipment_number('exp','装备经验')), ('切换保护',self._equipment_lock),
                          ('穿戴',self._equipment_equip), ('删除',self._equipment_delete)])
        self.equipment_tree = self._tree(frame, ('uid','id','name','slot','set','level','exp','lock','owner'),
                                         ('实例','ID','名称','类型','套装','等级','经验','保护','穿戴者'))
        self.equipment_tree.bind('<<TreeviewSelect>>', lambda e:self._equipment_detail())
        self.equipment_info = tk.StringVar()
        ttk.Label(frame, textvariable=self.equipment_info, wraplength=780).pack(anchor='w', pady=4)

    def _equipment_meta(self, kind, item):
        return self._find(self._rows('weapondata' if kind == 'weapon' else 'stigmatadata'),'ID',item.get('id')) or {}

    def _equipment_item(self, uid):
        for kind in ('weapon','stigmata'):
            item = self._find(self._account().get(kind+'_list', []),'unique_id',uid)
            if item is not None: return kind,item
        return None,None

    def _refresh_equipment(self):
        if not hasattr(self, 'equipment_tree'): return
        q = self.equipment_query.get().strip().casefold(); wanted = self.equipment_kind.get(); rows=[]
        for kind in ('weapon','stigmata'):
            for item in self._account().get(kind+'_list', []):
                identity, uid = item.get('id'), item.get('unique_id'); meta = self._equipment_meta(kind,item)
                if type(uid) is not int: continue
                slot = '武器' if kind == 'weapon' else {1:'圣痕上',2:'圣痕中',3:'圣痕下'}.get(meta.get('baseType'),'圣痕')
                name = self._label(meta,'displayTitle',identity); setid = meta.get('setID','')
                if wanted != '全部' and slot != wanted: continue
                if q not in ('%s %s %s %s' % (name,identity,uid,setid)).casefold(): continue
                rows.append((uid, (uid,identity,name,slot,setid,item.get('level',1),item.get('exp',0),
                                   '是' if item.get('is_protected') else '否',self._owner(uid))))
        self._populate(self.equipment_tree,rows); self._equipment_detail()

    def _equipment_detail(self):
        if not hasattr(self,'equipment_info'): return
        selected = self._selected(self.equipment_tree)
        if not selected: self.equipment_info.set(''); return
        kind,item = self._equipment_item(int(selected)); meta = self._equipment_meta(kind,item) if item else {}
        self.equipment_info.set('等级上限：%s    进化 ID：%s    进化材料：%s' %
                                (meta.get('maxLv','—'),meta.get('evoID','—'),meta.get('evoMaterial','—')))

    def _equipment_add(self):
        choices=[]
        for kind in ('weapon','stigmata'):
            for row in self._rows('weapondata' if kind == 'weapon' else 'stigmatadata'):
                identity = row.get('ID')
                if type(identity) is not int or identity <= 0: continue
                slot = '武器' if kind == 'weapon' else {1:'圣痕上',2:'圣痕中',3:'圣痕下'}.get(row.get('baseType'),'圣痕')
                choices.append(('%s · %s #%s · 套装 %s' % (slot,self._label(row,'displayTitle',identity),identity,row.get('setID','—')),(kind,identity)))
        choice = self._pick('搜索并选择要添加的装备（等级 1）',choices)
        if choice is not None: self._apply({'op':'equipment_add','kind':choice[0],'id':choice[1]})

    def _equipment_number(self, field, title):
        selected = self._selected(self.equipment_tree)
        if not selected: return
        kind,item = self._equipment_item(int(selected))
        if item is None: return
        meta = self._equipment_meta(kind,item); current = item.get(field,0)
        hint = '当前：%s；将按当前装备表校验。' % current
        if field == 'level': hint += ' 等级上限：%s' % meta.get('maxLv','未知')
        value = self._number(title,current,hint)
        if value is not None: self._apply({'op':'equipment_edit','unique_id':int(selected),field:value})

    def _equipment_lock(self):
        selected = self._selected(self.equipment_tree)
        if not selected: return
        _,item = self._equipment_item(int(selected))
        if item is not None: self._apply({'op':'equipment_edit','unique_id':int(selected),'is_protected':not item.get('is_protected',False)})

    def _equipment_equip(self):
        selected = self._selected(self.equipment_tree)
        if not selected: return
        kind,item = self._equipment_item(int(selected)); meta = self._equipment_meta(kind,item)
        slot = 1 if kind == 'weapon' else meta.get('baseType',0)+1
        choices=[]
        for avatar in self._account().get('avatar_list', []):
            if avatar.get('star',0) <= 0: continue
            aid = avatar.get('avatar_id'); ameta = self._find(self._rows('avatardata'),'avatarID',aid) or {}
            choices.append(('%s #%s' % (self._label(ameta,'fullName',aid),aid),aid))
        aid = self._pick('选择穿戴角色',choices)
        if aid is not None: self._apply({'op':'equipment_equip','avatar_id':aid,'slot':slot,'unique_id':int(selected)})

    def _equipment_delete(self):
        selected = self._selected(self.equipment_tree)
        if not selected: return
        if self._owner(int(selected)) != '未穿戴':
            messagebox.showinfo('删除装备','请先为角色更换装备，再删除该实例。',parent=self); return
        if messagebox.askyesno('删除装备','确认从工作副本中删除所选实例？',parent=self):
            self._apply({'op':'equipment_delete','unique_id':int(selected)})

    def _build_material(self):
        frame = self._page('材料与道具', '角色碎片在“女武神与技能”中单独修改。')
        self.material_query, _ = self._search(frame,self._refresh_material)
        self._bar(frame, [('修改数量',self._material_edit), ('批量补充',self._materials_batch)])
        self.material_tree = self._tree(frame, ('id','name','type','num','max'), ('ID','名称','类型','当前数量','上限'))
        self.material_tree.bind('<Double-1>',lambda e:self._material_edit())

    def _refresh_material(self):
        if not hasattr(self,'material_tree'): return
        q = self.material_query.get().strip().casefold(); rows=[]
        fragments = {a.get('avatarFragmentID') for a in self._rows('avatardata')}
        owned = self._account().get('material_list', [])
        for item in self._rows('materialdata'):
            identity = item.get('ID')
            if type(identity) is not int or identity <= 0 or identity in fragments: continue
            name = self._label(item,'displayTitle',identity); kind = item.get('ItemType','')
            if q not in ('%s %s %s' % (name,identity,kind)).casefold(): continue
            saved = self._find(owned,'id',identity) or {}
            rows.append((identity,(identity,name,kind,saved.get('num',0),item.get('quantityLimit','?'))))
        self._populate(self.material_tree,rows)

    def _material_edit(self):
        selected = self._selected(self.material_tree)
        if not selected: return
        row = self.material_tree.item(selected,'values')
        value = self._number(str(row[1]),int(row[3]),'允许范围：0 – ' + str(row[4]))
        if value is not None: self._apply({'op':'material','id':int(selected),'num':value})

    def _materials_batch(self):
        presets = self._rows('material_presets')
        choices = [(p.get('name',p.get('id','预设')),i) for i,p in enumerate(presets) if p.get('items')]
        index = self._pick('选择批量补充预设',choices)
        if index is None: return
        preset = presets[index]; items = preset['items']; lines=[]
        for item in items:
            meta = self._find(self._rows('materialdata'),'ID',item.get('id')) or {}
            lines.append('%s：%s' % (self._label(meta,'displayTitle',item.get('id')),item.get('num')))
        if messagebox.askyesno('批量补充','数量不足时补至目标，已有更多时保留：\n'+'\n'.join(lines),parent=self):
            self._apply({'op':'materials_batch','items':items})

    def _build_story(self):
        frame = self._page('剧情与外传', '深度进度面向 BH2017 V0.2.0，旧版 Android / NS 尚未验证；请先在游戏解锁相关章节。')
        form = ttk.Frame(frame); form.pack(fill='x')
        self.story_kind = tk.StringVar(value='剧情'); self.story_diff = tk.StringVar()
        self.story_chapter = tk.StringVar(); self.story_stage = tk.StringVar()
        self.story_kind_box = ttk.Combobox(form,textvariable=self.story_kind,values=('剧情','外传'),state='readonly',width=8)
        self.story_diff_box = ttk.Combobox(form,textvariable=self.story_diff,state='readonly',width=12)
        self.story_chapter_box = ttk.Combobox(form,textvariable=self.story_chapter,state='readonly',width=12)
        self.story_stage_box = ttk.Combobox(form,textvariable=self.story_stage,state='readonly',width=30)
        for title, box in (('类型',self.story_kind_box),('难度',self.story_diff_box),('章节',self.story_chapter_box),('关卡',self.story_stage_box)):
            ttk.Label(form,text=title).pack(side='left'); box.pack(side='left',padx=5)
        self.story_kind_box.bind('<<ComboboxSelected>>',lambda e:self._refresh_story(reset=1))
        self.story_diff_box.bind('<<ComboboxSelected>>',lambda e:self._refresh_story(reset=2))
        self.story_chapter_box.bind('<<ComboboxSelected>>',lambda e:self._refresh_story(reset=3))
        self.story_stage_box.bind('<<ComboboxSelected>>',lambda e:self._story_status())
        self._bar(frame,[('解锁到所选关卡',self._story_unlock),('本章节满星',self._story_chapter_stars),('全部剧情与外传满星',self._story_all_stars)])
        self.story_current = tk.StringVar()
        ttk.Label(frame,textvariable=self.story_current,wraplength=760).pack(anchor='w',pady=8)

    def _refresh_story(self, reset=0):
        if not hasattr(self,'story_stage_box'): return
        kind = 'story' if self.story_kind.get() == '剧情' else 'extra'
        stages = [s for s in self._rows('stages') if s.get('kind') == kind]
        diffs = sorted({s.get('difficulty') for s in stages if type(s.get('difficulty')) is int})
        self._story_diffs = {'%s (%s)' % ({1:'普通',2:'困难',3:'噩梦'}.get(x,'难度'),x):x for x in diffs}
        self.story_diff_box['values'] = list(self._story_diffs)
        if reset == 1 or self.story_diff.get() not in self._story_diffs:
            self.story_diff.set(next(iter(self._story_diffs),''))
        diff = self._story_diffs.get(self.story_diff.get())
        chapters = sorted({s.get('editor_chapter_id',s.get('chapterId')) for s in stages if s.get('difficulty') == diff and type(s.get('editor_chapter_id',s.get('chapterId'))) is int})
        self._story_chapters = {'章节 %s' % x:x for x in chapters}
        self.story_chapter_box['values'] = list(self._story_chapters)
        if reset in (1,2) or self.story_chapter.get() not in self._story_chapters:
            self.story_chapter.set(next(iter(self._story_chapters),''))
        chapter = self._story_chapters.get(self.story_chapter.get())
        selected = [s for s in stages if s.get('difficulty') == diff and s.get('editor_chapter_id',s.get('chapterId')) == chapter and type(s.get('id')) is int]
        self._story_stages = {'%s · #%s' % (s.get('display_name',s['id']),s['id']):s['id'] for s in selected}
        self.story_stage_box['values'] = list(self._story_stages)
        if reset in (1,2,3) or self.story_stage.get() not in self._story_stages:
            self.story_stage.set(next(iter(self._story_stages),''))
        self._story_status()

    def _story_status(self):
        if not hasattr(self,'story_current'): return
        identity = getattr(self,'_story_stages',{}).get(self.story_stage.get())
        account = self._account()
        saved = self._find(account.get('stage_list', []),'id',identity)
        if identity is None:
            self.story_current.set('暂无可编辑关卡。')
            return
        if saved is None:
            self.story_current.set('当前：尚无关卡记录')
            return
        stars = saved.get('challenge_index_list', [])
        editor_stars = account.get('stage_editor_stars', {})
        approved = editor_stars.get(str(identity), []) if isinstance(editor_stars,dict) else None
        if not isinstance(stars,list) or not isinstance(approved,list) or any(type(x) is not int for x in stars + approved):
            self.story_current.set('当前进度：%s    星级数据格式异常' % saved.get('progress',0))
            return
        stage = self._find(self._rows('stages'),'id',identity) or {}
        challenge_count = len(stage.get('challengeList', []))
        progress, max_progress = saved.get('progress', 0), stage.get('maxProgress', 1)
        if (len(set(stars)) != len(stars) or any(x < 0 or x >= challenge_count for x in stars + approved)
                or type(progress) is not int or type(max_progress) is not int):
            self.story_current.set('当前进度或星级数据与目录不一致')
            return
        runtime = account.get('stage_runtime',{})
        receipts = runtime.get('settlements',[]) if isinstance(runtime,dict) else []
        if not isinstance(receipts,list): receipts = []
        won = any(isinstance(r,dict) and r.get('stage_id') == identity and r.get('end_status') == 1 and
                  isinstance(r.get('response',{}),dict) and r.get('response',{}).get('retcode') == 0 and
                  r.get('response',{}).get('progress') == 1 for r in receipts)
        completed = won and saved.get('is_done') and progress >= max_progress
        effective = set(stars) if completed else set(stars) & set(approved)
        self.story_current.set('当前进度：%s    记录星级：%s    已确认星级：%s' %
                               (saved.get('progress',0),len(set(stars)),len(effective)))

    def _story_unlock(self):
        identity = getattr(self,'_story_stages',{}).get(self.story_stage.get())
        if identity is not None: self._apply({'op':'story_unlock','stage_id':identity})

    def _story_chapter_stars(self):
        diff = getattr(self,'_story_diffs',{}).get(self.story_diff.get())
        chapter = getattr(self,'_story_chapters',{}).get(self.story_chapter.get())
        if diff is not None and chapter is not None:
            self._apply({'op':'story_max_stars','kind':'story' if self.story_kind.get()=='剧情' else 'extra','difficulty':diff,'chapter_id':chapter})

    def _story_all_stars(self):
        if not messagebox.askyesno('全部满星','逐章校验所有剧情及外传难度；如有不满足条件的章节，本次不会应用任何修改。继续？',parent=self): return
        try:
            import editor_engine
            account, catalog = self.get_account(), self.get_catalog()
            if not isinstance(account,dict) or not isinstance(catalog,dict): raise ValueError('请先打开存档和编辑目录。')
            groups = {(s.get('kind'),s.get('difficulty'),s.get('editor_chapter_id',s.get('chapterId'))) for s in catalog.get('stages',[])}
            for kind,diff,chapter in sorted(groups):
                account = editor_engine.apply(account,catalog,{'op':'story_max_stars','kind':kind,'difficulty':diff,'chapter_id':chapter})
            self.set_account(account); self.refresh()
        except Exception as exc:
            messagebox.showerror('无法应用修改',str(exc),parent=self)

    def _build_world(self):
        frame = self._page('轮回与深渊', '深度进度面向 BH2017 V0.2.0，旧版 Android / NS 尚未验证；保留已有领奖记录。')
        sakura = ttk.LabelFrame(frame,text='樱色轮回',padding=8); sakura.pack(fill='x',pady=(0,8))
        self.sakura_current = tk.StringVar(); ttk.Label(sakura,textvariable=self.sakura_current).pack(anchor='w')
        bar = ttk.Frame(sakura); bar.pack(fill='x',pady=6)
        self.sakura_cycle = tk.StringVar(); self.sakura_part = tk.StringVar()
        self.sakura_cycle_box = ttk.Combobox(bar,textvariable=self.sakura_cycle,state='readonly',width=14)
        self.sakura_part_box = ttk.Combobox(bar,textvariable=self.sakura_part,state='readonly',width=25)
        self.sakura_cycle_box.pack(side='left'); self.sakura_part_box.pack(side='left',padx=8)
        self.sakura_cycle_box.bind('<<ComboboxSelected>>',lambda e:self._refresh_world(reset=True))
        ttk.Button(bar,text='切换至所选任务',command=self._sakura_set).pack(side='left')
        abyss = ttk.LabelFrame(frame,text='深渊',padding=8); abyss.pack(fill='x')
        self.abyss_current = tk.StringVar(); ttk.Label(abyss,textvariable=self.abyss_current).pack(anchor='w')
        bar = ttk.Frame(abyss); bar.pack(fill='x',pady=6)
        ttk.Label(bar,text='段位（1–7）').pack(side='left')
        self.abyss_group = tk.StringVar(); ttk.Entry(bar,textvariable=self.abyss_group,width=8).pack(side='left',padx=5)
        ttk.Label(bar,text='目标层数').pack(side='left')
        self.abyss_floor = tk.StringVar(); ttk.Entry(bar,textvariable=self.abyss_floor,width=8).pack(side='left',padx=5)
        ttk.Button(bar,text='应用深渊设置',command=self._abyss_set).pack(side='left',padx=8)
        self._world_identity = None

    def _refresh_world(self, reset=False):
        if not hasattr(self,'sakura_cycle_box'): return
        world = self._account().get('openworld_data',{})
        active = ', '.join(str(r.get('story_id')) for r in world.get('cur_story_list',[]) if isinstance(r,dict)) or '无'
        self.sakura_current.set('当前轮回：%s    进行中的任务：%s' % (world.get('cycle','无'),active))
        sakura = self._catalog().get('sakura',{}); stories = sakura.get('stories',[]) if isinstance(sakura,dict) else []
        cycles = sorted({r.get('Cycle') for r in stories if type(r.get('Cycle')) is int and 1 <= r['Cycle'] <= 4})
        self._sakura_cycles = {'第 %s 轮回' % x:x for x in cycles}; self.sakura_cycle_box['values'] = list(self._sakura_cycles)
        if self.sakura_cycle.get() not in self._sakura_cycles: self.sakura_cycle.set(next(iter(self._sakura_cycles),''))
        cycle = self._sakura_cycles.get(self.sakura_cycle.get())
        self._sakura_parts = {'PART %s · #%s' % (r['StoryID'] % 100,r['StoryID']):r['StoryID'] for r in stories if r.get('Cycle') == cycle and type(r.get('StoryID')) is int}
        self.sakura_part_box['values'] = list(self._sakura_parts)
        if reset or self.sakura_part.get() not in self._sakura_parts: self.sakura_part.set(next(iter(self._sakura_parts),''))
        state = self._account().get('endless_runtime',{}); group = state.get('group'); floor = state.get('progress')
        self.abyss_current.set('当前段位：%s    当前关卡：%s    可选层数：1–%s' % (group if group is not None else '未开启', floor+1 if type(floor) is int else '—',self._catalog().get('abyss_floors','?')))
        identity = (group,floor)
        if identity != self._world_identity:
            self.abyss_group.set(str(group) if group is not None else '')
            self.abyss_floor.set(str(floor+1) if type(floor) is int else '')
            self._world_identity = identity

    def _sakura_set(self):
        cycle = getattr(self,'_sakura_cycles',{}).get(self.sakura_cycle.get())
        story = getattr(self,'_sakura_parts',{}).get(self.sakura_part.get())
        if cycle is not None and story is not None: self._apply({'op':'sakura_set_part','cycle':cycle,'story_id':story})

    def _abyss_set(self):
        try: group,floor = int(self.abyss_group.get()),int(self.abyss_floor.get())
        except ValueError:
            messagebox.showerror('无法应用修改','段位和层数请输入整数。',parent=self); return
        self._apply({'op':'abyss_set','group':group,'floor':floor})

    def _build_cabin(self):
        frame = self._page('家园与宿舍', '仅支持已适配的 3、4、5 号舱室；科技信息只读。')
        self._bar(frame,[('提高等级',lambda:self._cabin_number('level','舱室等级')),
                         ('提高扩建',lambda:self._cabin_number('extend_grade','扩建等级'))])
        self.cabin_tree = self._tree(frame,('type','level','grade','tech'),('舱室','等级','扩建','科技节点'))
        self.cabin_tree.bind('<<TreeviewSelect>>',lambda e:self._cabin_detail())
        self.cabin_info = tk.StringVar()
        ttk.Label(frame,textvariable=self.cabin_info,wraplength=780).pack(anchor='w',pady=6)

    def _refresh_cabin(self):
        if not hasattr(self,'cabin_tree'): return
        rows=[]
        if self._account():
            for kind in (3,4,5):
                cabin = self._find(self._account().get('cabin_list',[]),'type',kind)
                if cabin is None:
                    rows.append((kind,(kind,'未解锁','—','—')))
                else:
                    tech = cabin.get('tech_list',[])
                    rows.append((kind,(kind,cabin.get('level','—'),cabin.get('extend_grade','—'),len(tech))))
        self._populate(self.cabin_tree,rows); self._cabin_detail()

    def _cabin_detail(self):
        if not hasattr(self,'cabin_info'): return
        selected = self._selected(self.cabin_tree)
        if not selected: self.cabin_info.set(''); return
        cabin = self._find(self._account().get('cabin_list',[]),'type',int(selected))
        if cabin is None:
            self.cabin_info.set('舱室尚无记录，未解锁。')
            return
        nodes=[]
        for tech in cabin.get('tech_list',[]):
            x,y = tech.get('pos_x'),tech.get('pos_y')
            meta = next((r for r in self._rows('cabintechtreedata') if r.get('Cabin')==int(selected) and r.get('X')==x and r.get('Y')==y),{})
            nodes.append('%s (%s,%s)' % (self._label(meta,'Title','科技'),x,y))
        self.cabin_info.set('已解锁科技（只读）：' + ('、'.join(nodes) if nodes else '无'))

    def _cabin_number(self,field,title):
        selected = self._selected(self.cabin_tree)
        if not selected: return
        cabin = self._find(self._account().get('cabin_list',[]),'type',int(selected)) or {}
        value = self._number(title,cabin.get(field,1),'仅支持提高；按当前舰长等级、扩建及科技条件校验。')
        if value is not None: self._apply({'op':'cabin','cabin_type':int(selected),field:value})

    def refresh(self):
        try:
            account = self.get_account()
        except ValueError:
            # The host has no open account yet (or an incomplete form).
            account = None
        catalog = self.get_catalog()
        self._cached_account = account if isinstance(account, dict) else {}
        self._cached_catalog = catalog if isinstance(account, dict) and isinstance(catalog, dict) else {}
        self._text_cache = {row.get('ID'):row.get('Text') for row in self._cached_catalog.get('textmap',[]) if isinstance(row,dict)}
        for method in (self._refresh_captain,self._refresh_avatar,self._refresh_costume,self._refresh_equipment,
                       self._refresh_material,self._refresh_story,self._refresh_world,self._refresh_cabin):
            method()


def create_tab(notebook, get_account, set_account, get_catalog):
    """Create the detailed editor tab; call .refresh() when the account changes."""
    frame = AdvancedEditor(notebook, get_account, set_account, get_catalog)
    notebook.add(frame,text='深度编辑')
    frame.refresh()
    return frame
