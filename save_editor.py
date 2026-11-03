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
    'scoin': ('金币', 100_000_000), 'hcoin': ('水晶', 1_000_000),
    'stamina': ('体力', 10_000), 'friends_point': ('友情点', 100_000),
}
TEMPLATES = {'保持不变': None, '到达32关': 31}
from progression import CYCLES, RANKS, unlock, set_cycle, set_rank


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
    if identity_locked(original) and any(original['main'].get(k) != result['main'].get(k) for k in IDENTITY_FIELDS):
        raise ValueError('模板存档的昵称和签名不可在编辑器中修改。')


def edit(data, values, template=None, now=None, *, cycle=None, story=False, extra=False, rank=None):
    result = copy.deepcopy(data)
    changes = []
    for key, text in values.items():
        if key not in FIELDS or key not in data['main']:
            raise ValueError('不允许添加或编辑字段：' + key)
        label, limit = FIELDS[key]
        old = data['main'][key]
        if str(old) == text:
            continue  # Preserve out-of-range legacy values unless explicitly edited.
        if identity_locked(data) and key in IDENTITY_FIELDS:
            raise ValueError('模板存档的昵称和签名不可在编辑器中修改。')
        if key in IDENTITY_FIELDS:
            if not isinstance(old, str):
                raise ValueError(label + '原字段类型不兼容。')
            new = text.strip()
            if not new or len(new.encode('utf-16-le')) // 2 > limit or any(ord(c) < 32 for c in new):
                raise ValueError(f'{label}须为 1–{limit} 个 UTF-16 单位，不能含控制字符。')
            if '<' in new or '>' in new:
                raise ValueError(label + '不支持富文本标签。')
        else:
            if type(old) is not int or not text.isascii() or not text.isdecimal():
                raise ValueError(label + '须为非负整数。')
            new = int(text)
            minimum = 1 if key == 'level' else 0
            if not minimum <= new <= limit:
                raise ValueError(f'{label}编辑范围为 {minimum}–{limit:,}。')
        if old != new:
            result['main'][key] = new
            changes.append(f'{label}：{old} → {new}')
            if key == 'level':
                exp = data['main'].get('exp')
                if type(exp) is not int or exp < 0:
                    raise ValueError('舰长经验字段不兼容，不能修改等级。')
                result['main']['exp'] = 0
                changes.append(f'舰长当前等级经验：{exp} → 0（不补发升级奖励）')
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
    if cycle is not None:
        changes.append(set_cycle(result, cycle))
    for kind, enabled in [('story', story), ('extra', extra)]:
        if enabled:
            change = unlock(result, kind, now)
            if change: changes.append(change)
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
    return parse((Path(__file__).parent / 'templates' / TEMPLATE_FILES[kind]).read_bytes())


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
        root.title('BH3 V1.9存档修改器')
        root.geometry('840x860');root.minsize(780,830)
        style=ttk.Style(root)
        if 'vista' in style.theme_names():style.theme_use('vista')
        outer=ttk.Frame(root,padding=20);outer.pack(fill='both',expand=True)
        ttk.Label(outer,text='BH3 V1.9存档修改器',font=('Microsoft YaHei UI',18,'bold')).pack(anchor='w')
        ttk.Label(outer,text='打开存档，选择需要修改的内容，然后保存。').pack(anchor='w',pady=(4,12))
        toolbar=ttk.Frame(outer);toolbar.pack(fill='x')
        ttk.Button(toolbar,text='打开存档…',command=self.open).pack(side='left')
        self.new_kind=tk.StringVar(value='新号')
        ttk.Combobox(toolbar,textvariable=self.new_kind,values=list(TEMPLATE_FILES),state='readonly',width=16).pack(side='left',padx=(24,8))
        ttk.Button(toolbar,text='使用模板新建',command=self.new).pack(side='left')
        self.template_name=None
        self.info=tk.StringVar(value='尚未打开存档')
        ttk.Label(outer,textvariable=self.info,wraplength=720).pack(anchor='w',pady=10)
        form=ttk.LabelFrame(outer,text='基本信息与资源',padding=12);form.pack(fill='x')
        self.variables={};self.entries={}
        for row,(key,(label,limit)) in enumerate(FIELDS.items()):
            ttk.Label(form,text=label,width=10).grid(row=row,column=0,sticky='w',pady=4)
            var=tk.StringVar();entry=ttk.Entry(form,textvariable=var,width=32,state='disabled')
            entry.grid(row=row,column=1,sticky='ew',padx=8)
            hint=f'最多 {limit} 字' if key in ('nickname','self_desc') else ('1–80；修改后经验归零' if key == 'level' else f'0–{limit:,}')
            ttk.Label(form,text=hint).grid(row=row,column=2,sticky='w')
            self.variables[key],self.entries[key]=var,entry
        self.identity_hint=tk.StringVar(value='')
        ttk.Label(form,textvariable=self.identity_hint).grid(row=len(FIELDS),column=1,columnspan=2,sticky='w',padx=8)
        form.columnconfigure(1,weight=1)
        progress=ttk.LabelFrame(outer,text='剧情与关卡',padding=12);progress.pack(fill='x',pady=12)
        self.cycle=tk.StringVar(value='保持不变');self.template=tk.StringVar(value='保持不变');self.rank=tk.StringVar(value='保持不变')
        self.story=tk.BooleanVar(value=False);self.extra=tk.BooleanVar(value=False)
        ttk.Label(progress,text='樱色轮回',width=12).grid(row=0,column=0,sticky='w',pady=5)
        ttk.Combobox(progress,textvariable=self.cycle,values=list(CYCLES),state='readonly',width=25).grid(row=0,column=1,sticky='w')
        ttk.Label(progress,text='从所选轮回开头继续').grid(row=1,column=1,sticky='w')
        ttk.Label(progress,text='深渊进度').grid(row=2,column=0,sticky='w',pady=10)
        ttk.Combobox(progress,textvariable=self.template,values=list(TEMPLATES),state='readonly',width=25).grid(row=2,column=1,sticky='w')
        ttk.Label(progress,text='深渊段位').grid(row=3,column=0,sticky='w',pady=6)
        ttk.Combobox(progress,textvariable=self.rank,values=list(RANKS),state='readonly',width=25).grid(row=3,column=1,sticky='w')
        ttk.Checkbutton(progress,text='剧情关卡全部通关',variable=self.story).grid(row=4,column=0,columnspan=2,sticky='w',pady=3)
        ttk.Checkbutton(progress,text='外传关卡全部通关',variable=self.extra).grid(row=5,column=0,columnspan=2,sticky='w',pady=3)
        ttk.Label(progress,text='按演示存档模板设为全通，相关任务已领取；不补发奖励。',wraplength=690).grid(row=6,column=0,columnspan=3,sticky='w',pady=5)
        actions=ttk.Frame(outer);actions.pack(fill='x',pady=10)
        ttk.Button(actions,text='预览修改',command=self.preview).pack(side='left')
        ttk.Button(actions,text='保存',command=lambda:self.write(False)).pack(side='right')
        ttk.Button(actions,text='另存为…',command=lambda:self.write(True)).pack(side='right',padx=8)
        self.status=tk.StringVar(value='')
        ttk.Label(outer,textvariable=self.status,wraplength=720).pack(anchor='w')
        root.protocol('WM_DELETE_WINDOW',self.close)

    def dirty(self):
        return self.data is not None and (self.source is None or self.rank.get()!='保持不变' or self.template.get()!='保持不变' or self.cycle.get()!='保持不变' or self.story.get() or self.extra.get() or any(v.get()!=str(self.data['main'][k]) for k,v in self.variables.items() if k in self.data['main']))

    def close(self):
        if not self.dirty() or messagebox.askyesno('未保存的修改','放弃当前修改并退出？'):self.root.destroy()

    def load(self,path):
        raw=Path(path).read_bytes();data=parse(raw)
        self.bind_data(data, raw, Path(path))

    def bind_data(self,data,raw,path=None):
        self.source,self.original,self.data=path,raw,data
        if path is not None: self.template_name=None
        for k,var in self.variables.items():
            var.set(str(data['main'][k]) if k in data['main'] else '')
            state = 'disabled' if k not in data['main'] else ('readonly' if identity_locked(data) and k in IDENTITY_FIELDS else 'normal')
            self.entries[k].configure(state=state)
        self.rank.set('保持不变');self.template.set('保持不变');self.cycle.set('保持不变');self.story.set(False);self.extra.set(False)
        world=data.get('openworld_data',{});c=world.get('cycle')
        cycle_name={1:'第一轮',2:'第二轮',3:'第三轮',4:'第四轮 PART1'}.get(c,'未开启')
        rank_name=next((k for k,v in RANKS.items() if v==data.get('endless_runtime',{}).get('group')), '未开启')
        self.identity_hint.set('模板昵称与签名不可编辑' if identity_locked(data) else '')
        self.info.set(f'{Path(path).name if path is not None else self.template_name}  ·  舰长等级 {data["main"].get("level","未知")}  ·  樱色轮回：{cycle_name}  ·  深渊：{rank_name}')

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
        values={k:v.get() for k,v in self.variables.items() if k in self.data['main']}
        result,changes=edit(self.data,values,TEMPLATES[self.template.get()],cycle=CYCLES[self.cycle.get()],story=self.story.get(),extra=self.extra.get(),rank=RANKS[self.rank.get()])
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
        app.cycle.set('第四轮 PART1'); app.story.set(True); app.extra.set(True); app.rank.set('红莲深渊')
        result, changes = app.candidate()
        assert result['endless_runtime']['group']==6
        assert result['main']['level'] == 80 and result['main']['exp'] == 0
        assert len(changes) == 7 and result['keep'] == sample['keep']
        assert len(result['stage_list']) == 250
        assert result['openworld_data']['cycle'] == 4
        assert 401 not in result['openworld_data']['finish_story_id_list']
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
            app.load(target)
            assert all(str(app.entries[k]['state'])=='readonly' for k in IDENTITY_FIELDS)
            app.variables['nickname'].set('更名')
            try: app.candidate()
            except ValueError: pass
            else: raise AssertionError('Template identity modification accepted')
        app.load(source)
        assert all(str(app.entries[k]['state'])=='normal' for k in IDENTITY_FIELDS)
        root.destroy()
    Path(report).write_text(json.dumps({'status': 'passed', 'checks':
        ['bundled Tk widgets', 'load synthetic save', 'edit whitelist', 'cycle4 start', '250 stage full-clear',
         'preserve unknown data', 'backup and save readback', 'template identity readonly and reload', 'template identity validation', 'ordinary identity editable']}, indent=2), encoding='utf-8')


if __name__ == '__main__':
    import sys
    if len(sys.argv) == 3 and sys.argv[1] == '--self-test':
        packaged_self_test(sys.argv[2])
    else:
        root = tk.Tk()
        Editor(root)
        root.mainloop()
