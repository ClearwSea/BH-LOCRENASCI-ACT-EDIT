"""V0.2.0 save-editor operations for the standalone PC interface.

The caller supplies a version-matched catalog. No operation writes files; all
results are independent copies. Runtime data and private saves are not bundled.
"""
from editor_core import cabin, captain, inventory, progress, templates

_CAPTAIN_LABELS = {
    'level': '舰长等级', 'scoin': '金币', 'hcoin': '水晶', 'stamina': '体力',
    'friends_point': '友情点', 'skill_point': '技能点', 'skill_point_limit': '技能点上限',
    'equipment_size_limit': '装备容量',
}
_MESSAGES = {
    'Character or equipment is locked by an active battle or Memorial Arena': '角色或装备正被进行中的战斗或记忆战场锁定',
    'Equipment is worn by a character locked in battle': '该装备被战斗锁定的角色穿戴',
    'Equipment is not compatible with this slot': '装备与该角色或槽位不兼容',
    'Equipment cost exceeds character capacity': '装备负载超过角色上限',
    'Equipment is already worn': '装备已被其他位置穿戴',
    'Equipment has multiple owners': '装备同时被多个角色穿戴，无法安全修改',
    'Equipment not found': '找不到指定装备',
    'Missing equipped item': '角色穿戴的装备不存在',
    'Missing equipment experience threshold': '当前目录缺少装备经验等级数据',
    'Invalid or empty weapon slot': '武器槽必须保留有效装备',
    'Invalid equipment protection': '装备保护状态无效',
    'Duplicate equipment UID': '存档中存在重复装备编号',
    'Equipment UID range is exhausted': '装备实例编号已用尽',
    'Unknown equipment kind': '未知装备类型',
    'Character is locked': '角色尚未解锁',
    'Skill does not belong to character': '技能不属于该角色',
    'Duplicate skill': '存档中存在重复技能',
    'Duplicate subskill': '存档中存在重复子技能',
    'Malformed shared skill mapping': '共享技能对应表格式错误',
    'Duplicate character': '存档中存在重复角色',
    'Costume ownership must be boolean': '服装解锁状态无效',
    'Costume is not an unlockable character outfit': '该服装不属于可解锁的角色服装',
    'Costume is not unlocked for character': '该角色尚未解锁此服装',
    'Use character fragment editing for fragments': '角色碎片请在对应角色页面修改',
    'Material batch target must leave room for rewards': '批量材料数量需要为后续奖励预留空间',
    'Duplicate material': '存档中存在重复材料记录',
    'Character rank is below its initial rank': '角色评阶低于初始评阶',
    'Unlock the original character before its awakened version': '请先解锁原角色再解锁觉醒角色',
    'Lock the awakened character first': '请先锁定觉醒角色',
    'Cannot lock the last unlocked character': '不能锁定最后一名已解锁角色',
    'Remove character from saved teams first': '请先将角色移出已保存编队',
    'Cannot change the level of a locked character': '不能修改未解锁角色的等级',
    'Cannot change affection of a locked character': '不能修改未解锁角色的好感',
    'Legacy material fragment stack needs migration before editing': '旧式角色碎片尚未迁移，无法安全编辑',
    'Expected account, catalog and operation objects': '存档、数据目录或操作格式错误',
    'Conflicting editor operation names': '编辑操作名称不一致',
    'Conflicting operation names': '编辑操作名称不一致',
    'Only bulk unlock is supported': '批量服装操作只支持解锁',
    'Missing material batch': '缺少批量材料数据',
    'Two different characters are required': '请选择两名不同的角色',
    'Both characters must be unlocked': '两名角色都必须已解锁',
    'Two different equipped weapons are required': '需要两件不同的已装备武器',
    'Replacement must be another item': '替代装备必须是另一件装备',
    'Missing table: ': '当前目录缺少数据表：',
    'Missing or duplicate ': '当前目录缺少或重复记录：',
    'Unsupported editor operation: ': '不支持的编辑操作：',
    'Unknown cabin operation': '不支持的舱室编辑操作',
    'Technology is read-only until native power and prerequisite rules are verified': '科技暂时只读，原生电力和前置条件尚未验证',
    'Missing or duplicate cabin table row': '舱室目录缺少记录或存在重复记录',
    'Cabin level exceeds extension limit': '舱室等级超过扩建上限',
    'Captain level is below the cabin requirement': '舰长等级不足以使用该舱室等级',
    'Duplicate cabin technology': '存档存在重复的舱室科技',
    'Existing technology requires a higher cabin level': '已解锁的科技需要更高舱室等级',
    'Technology requires an unlocked character at a higher level': '科技需要对应角色解锁并达到指定等级',
    'Duplicate cabin': '存档中存在重复舱室',
    'Finish the ongoing cabin upgrade in game first': '请先在游戏内完成当前舱室升级',
    'Lowering a cabin level or extension is not yet verified': '舱室降级和降低扩建尚未验证',
}
_LABELS = {
    'equipment UID': '装备编号', 'equipment max level': '装备等级上限',
    'equipment level': '装备等级', 'equipment experience type': '装备经验类型',
    'equipment experience threshold': '装备经验上限', 'equipment exp': '装备经验',
    'equipment cost': '装备负载', 'avatar maximum equipment cost': '角色负载上限',
    'equipment id': '装备 ID', 'skill level': '技能等级', 'skill max level': '技能等级上限',
    'material limit': '材料上限', 'material quantity': '材料数量',
    'character rank': '角色评阶', 'initial rank': '初始评阶',
    'character level': '角色等级', 'character level cap': '角色等级上限',
    'fragment count': '角色碎片数量', 'fragment limit': '角色碎片上限',
    'equipment slot': '装备槽位', 'replacement UID': '替代装备编号',
    'cabin type': '舱室类型', 'cabin level': '舱室等级', 'cabin extension': '舱室扩建',
    'skill point bonus': '技能点加成', 'skill point limit': '技能点上限',
}


def _message(error):
    message = str(error)
    for source, target in _MESSAGES.items():
        if message.startswith(source):
            return target + message[len(source):]
    if ' must be an integer in ' in message:
        name, bounds = message.split(' must be an integer in ', 1)
        return f"{_LABELS.get(name, name)}必须为 {bounds} 范围内的整数"
    if message.startswith('Invalid '):
        return '数据无效：' + _LABELS.get(message[8:], message[8:])
    for key, label in _CAPTAIN_LABELS.items():
        if message.startswith(key + ' 允许范围'):
            return label + message[len(key):]
    return message


def limits(account, catalog):
    """Return current captain bounds, including the Cabin 4 skill bonus."""
    try:
        return captain.limits(account, catalog)
    except KeyError as error:
        raise ValueError('存档或数据目录缺少必要字段：' + str(error)) from error
    except ValueError as error:
        raise ValueError(_message(error)) from error


def apply(account, catalog, operation):
    """Apply a single validated operation to a copy; never mutate the caller."""
    if not isinstance(account, dict) or not isinstance(catalog, dict) or not isinstance(operation, dict):
        raise ValueError('存档、数据目录或操作格式错误')
    if 'op' in operation and 'type' in operation and operation['op'] != operation['type']:
        raise ValueError('编辑操作名称不一致')
    command = operation.get('op', operation.get('type'))
    try:
        if command == 'captain':
            return captain.apply(account, catalog, operation)
        if command == 'template':
            return templates.create(catalog, operation.get('kind'), uid=account['uid'])
        if command in ('story_unlock', 'story_max_stars', 'sakura_set_part', 'abyss_set'):
            command_op = dict(operation, op=command)
            return progress.apply(account, catalog, command_op)[0]
        if command in ('cabin', 'cabin_tech'):
            return cabin.apply(account, catalog, operation)
        return inventory.apply(account, catalog, operation)
    except KeyError as error:
        raise ValueError('存档或数据目录缺少必要字段：' + str(error)) from error
    except ValueError as error:
        raise ValueError(_message(error)) from error
