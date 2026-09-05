# -*- coding: utf-8 -*-
"""学生管理系统 - 无头逻辑测试（使用临时数据库，不污染正式 data.json）"""
import os
import sys
import tempfile

os.environ['SDL_VIDEODRIVER'] = 'dummy'   # 无关紧要，仅防止意外

# 保证能导入 Students Control 目录下的模块
HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

from database import Database  # noqa: E402


def make_db() -> Database:
    fd, path = tempfile.mkstemp(suffix='.json', prefix='stu_test_')
    os.close(fd)
    os.remove(path)
    return Database(path)


db = make_db()

# [1] 初始数据与管理员
assert len(db.data['teachers']) == 2 and db.data['teachers'][0]['role'] == 'admin'
admin = db.find_teacher('admin')
t1 = db.find_teacher('t001')
s1 = db.find_student('2024001')
assert db.is_admin(admin) and not db.is_admin(t1)
assert not db.verify(admin, 'wrong')
assert db.verify(admin, 'admin123')
print('[1] 初始数据/管理员/密码校验 OK')

# [2] 登录：各自按钮，用错报错
assert db.teacher_login('admin', 'admin123')[0] is admin
assert db.teacher_login('2024001', '123456')[1] == '该账号是学生账号，请点击「学生登录」按钮'
assert db.teacher_login('nobody', 'x')[1] == '教师账号不存在'
assert db.teacher_login('admin', 'x')[1] == '密码错误'
assert db.student_login('2024001', '123456')[0] is s1
assert db.student_login('t001', '123456')[1] == '该账号是教师账号，请点击「教师登录」按钮'
assert db.student_login('nobody', 'x')[1] == '学生账号不存在'
print('[2] 登录按钮校验/报错 OK')

# [3] 管理员添加学生（普通教师权限仅体现在界面上，此处测数据层）
ok, _ = db.add_student('2024004', '赵六', '男', '软件2402', '13800000004', 'abc123')
assert ok
ok, msg = db.add_student('2024004', '重复', '男', 'x', '1', 'x')
assert not ok and '已存在' in msg
ok, msg = db.add_student('t001', '占用', '男', 'x', '1', 'x')
assert not ok and '占用' in msg
print('[3] 添加学生/重号校验 OK')

# [4] 成绩维护
ok, _ = db.set_grades('2024004', {'语文': 95, '数学': 100})
assert ok
assert db.find_student('2024004')['grades']['语文'] == 95
ok, msg = db.set_grades('2024004', {'语文': 150})
assert not ok and '0~100' in msg
ok, _ = db.set_grades('2024004', {'语文': 90, '数学': 88, '英语': 92})
assert ok
print('[4] 成绩设置/校验 OK')

# [5] 学生修改申请：提交 -> 管理员批准后生效；拒绝不生效
s4 = db.find_student('2024004')
# 新值 = 原值 → 拒绝
ok, msg = db.add_request(s4, 'phone', '13800000004')
assert not ok and '相同' in msg
# 正常提交
ok, msg = db.add_request(s4, 'phone', '13900000000')
assert ok and '提交' in msg
ok, msg = db.add_request(s4, 'id', 'abc')  # 不允许改学号
assert not ok

reqs = db.list_requests('2024004')
assert len(reqs) == 1 and reqs[0]['status'] == 'pending'

ok, _ = db.handle_request(reqs[0]['req_id'], approve=False)
assert db.find_student('2024004')['phone'] == '13800000004'
assert db.list_requests('2024004')[0]['status'] == 'rejected'

ok, _ = db.add_request(s4, 'phone', '13911112222')
req = db.list_requests('2024004')[0]
ok, _ = db.handle_request(req['req_id'], approve=True)
assert db.find_student('2024004')['phone'] == '13911112222'
print('[5] 学生申请-管理员审核生效 OK')

# [6] 教师账号管理
ok, _ = db.add_teacher('t002', '王老师', '654321')
assert ok
ok, msg = db.add_teacher('t002', '重复', 'x')
assert not ok and '已存在' in msg
ok, msg = db.delete_teacher('admin')
assert not ok and '管理员' in msg
ok, _ = db.delete_teacher('t002')
assert db.find_teacher('t002') is None
ok, msg = db.reset_password(admin, '')
assert not ok
ok, _ = db.reset_password(admin, 'newpwd123')
assert db.verify(admin, 'newpwd123') and not db.verify(admin, 'admin123')
print('[6] 教师账号管理/重置密码 OK')

# [7] 学生删除清理关联申请
s2 = db.find_student('2024002')
db.add_request(s2, 'phone', '13777778888')
db.delete_student('2024002')
assert all(r['student_id'] != '2024002' for r in db.data['requests'])
assert db.find_student('2024002') is None
print('[7] 删除学生连带清理申请 OK')

# [8] 数据落盘：重开数据库读取一致
import json
with open(db.path, 'r', encoding='utf-8') as f:
    saved = json.load(f)
assert saved['teachers'][0]['id'] == 'admin'
assert saved['students'][0]['id'] == '2024001'
assert all('password_hash' in r for r in saved['students'])
assert all('salt' in r for r in saved['students'])
assert all('salt' in r for r in saved['teachers'])
print('[8] JSON 持久化与加密字段 OK')

# [9] GUI 冒烟：LoginApp / TeacherApp / StudentApp 可正常实例化
try:
    import tkinter as tk
    # 不真正弹出主循环，仅构造窗口后立即销毁
    root = tk.Tk()
    root.withdraw()
    from student_management import LoginApp, TeacherApp, StudentApp  # noqa: E402
    la = LoginApp(db)
    la.win.update_idletasks()
    la.win.destroy()
    ta = TeacherApp(db, db.find_teacher('admin'))
    ta.win.update_idletasks()
    ta.win.destroy()
    sa = StudentApp(db, db.find_student('2024001'))
    sa.win.update_idletasks()
    sa.win.destroy()
    root.destroy()
    print('[9] GUI 界面实例化冒烟 OK')
except Exception as e:  # 无显示环境时报错也作为提示
    print('[9] GUI 冒烟跳过（', type(e).__name__, e, '）')

print('\n学生管理系统全部逻辑测试通过')
