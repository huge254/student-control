# -*- coding: utf-8 -*-
"""学生管理系统 - 图形界面（tkinter）

角色权限：
  管理员（第一个教师账号 admin）: 对数据库拥有全部权限
     - 学生增删改查、成绩录入/修改/删除
     - 教师账号管理（添加/删除/重置密码）
     - 审核学生提交的修改申请
  普通教师: 仅查看学生信息与成绩（只读）
  学生: 仅查看自己的信息与成绩；可提交修改申请，需管理员审核后生效

登录：教师/学生分别通过各自按钮登录，用错按钮会明确报错。
运行：python student_management.py
"""
import tkinter as tk
from collections.abc import Callable
from tkinter import ttk, messagebox

from database import Database, EDITABLE_FIELDS, Record

# ---------- 配色 ----------
COLOR_BG = '#f0f2f5'
COLOR_HEAD = '#2b3a55'
COLOR_ACCENT = '#1f6feb'
COLOR_BTN_T = '#3a6ea5'          # 教师登录按钮
COLOR_BTN_S = '#3a9e6d'          # 学生登录按钮
COLOR_DANGER = '#c0392b'
FONT = ('Microsoft YaHei', 10)
FONT_TITLE = ('Microsoft YaHei', 22, 'bold')


class LoginApp:
    """登录界面：账号 + 密码 + 教师/学生两个登录按钮"""

    def __init__(self, db: Database):
        self.db = db
        self.win = tk.Tk()
        self.win.title('学生管理系统')
        self.win.geometry('460x420')
        self.win.configure(bg=COLOR_BG)
        self.win.resizable(False, False)
        self._build()

    def _build(self) -> None:
        head = tk.Frame(self.win, bg=COLOR_HEAD, height=120)
        head.pack(fill='x')
        head.pack_propagate(False)
        tk.Label(head, text='学生管理系统', bg=COLOR_HEAD, fg='white',
                 font=FONT_TITLE).pack(pady=(26, 4))
        tk.Label(head, text='教师 / 学生双角色登录', bg=COLOR_HEAD, fg='#b8c4d9',
                 font=('Microsoft YaHei', 10)).pack()

        body = tk.Frame(self.win, bg=COLOR_BG)
        body.pack(fill='both', expand=True, padx=55, pady=16)

        tk.Label(body, text='账号', bg=COLOR_BG, font=FONT).pack(anchor='w')
        self.var_id = tk.StringVar()
        self.ent_id = tk.Entry(body, textvariable=self.var_id, font=FONT)
        self.ent_id.pack(fill='x', ipady=4, pady=(2, 10))

        tk.Label(body, text='密码', bg=COLOR_BG, font=FONT).pack(anchor='w')
        self.var_pwd = tk.StringVar()
        self.ent_pwd = tk.Entry(body, textvariable=self.var_pwd, show='*', font=FONT)
        self.ent_pwd.pack(fill='x', ipady=4, pady=(2, 14))

        btns = tk.Frame(body, bg=COLOR_BG)
        btns.pack(fill='x', pady=4)
        self.btn_teacher = tk.Button(
            btns, text='教 师 登 录', bg=COLOR_BTN_T, fg='white', relief='flat',
            font=('Microsoft YaHei', 12, 'bold'), activebackground='#2f5a88',
            activeforeground='white', cursor='hand2', command=self._teacher_login)
        self.btn_teacher.pack(side='left', expand=True, fill='x', padx=(0, 8), ipady=9)
        self.btn_student = tk.Button(
            btns, text='学 生 登 录', bg=COLOR_BTN_S, fg='white', relief='flat',
            font=('Microsoft YaHei', 12, 'bold'), activebackground='#2e7d5a',
            activeforeground='white', cursor='hand2', command=self._student_login)
        self.btn_student.pack(side='left', expand=True, fill='x', padx=(8, 0), ipady=9)

        self.var_msg = tk.StringVar(value=' ')
        tk.Label(body, textvariable=self.var_msg, bg=COLOR_BG, fg=COLOR_DANGER,
                 font=FONT).pack(pady=(12, 0))

        tip = tk.Label(self.win, justify='center', bg=COLOR_BG, fg='#8a94a6',
                       font=('Microsoft YaHei', 9),
                       text='默认账号：管理员 admin / admin123   教师 t001 / 123456\n'
                            '学生 2024001 / 123456（初始密码均为 123456）')
        tip.pack(side='bottom', pady=10)

    def _teacher_login(self) -> None:
        uid = self.var_id.get().strip()
        pwd = self.var_pwd.get()
        if not uid or not pwd:
            self.var_msg.set('请输入账号和密码！')
            return
        teacher, err = self.db.teacher_login(uid, pwd)
        if err:
            self.var_msg.set(err)
            return
        if teacher is None:
            return
        self.win.destroy()
        TeacherApp(self.db, teacher).run()

    def _student_login(self) -> None:
        uid = self.var_id.get().strip()
        pwd = self.var_pwd.get()
        if not uid or not pwd:
            self.var_msg.set('请输入账号和密码！')
            return
        student, err = self.db.student_login(uid, pwd)
        if err:
            self.var_msg.set(err)
            return
        if student is None:
            return
        self.win.destroy()
        StudentApp(self.db, student).run()

    def run(self) -> None:
        self.win.mainloop()


# ============================================================
# 教师端
# ============================================================
class TeacherApp:
    """教师端主窗口：管理员拥有全部权限，普通教师只读"""

    def __init__(self, db: Database, teacher: Record):
        self.db = db
        self.teacher = teacher
        self.is_admin = db.is_admin(teacher)
        self.win = tk.Tk()
        role_txt = '管理员' if self.is_admin else '普通教师'
        self.win.title(f'教师端（{role_txt}）- {teacher["name"]}')
        self.win.geometry('1120x620')
        self.win.configure(bg=COLOR_BG)
        self._build()
        self._refresh()

    def _build(self) -> None:
        # 顶部工具栏
        bar = tk.Frame(self.win, bg=COLOR_BG)
        bar.pack(fill='x', padx=12, pady=10)
        tk.Label(bar, text='搜索:', bg=COLOR_BG, font=FONT).pack(side='left')
        self.var_search = tk.StringVar()
        tk.Entry(bar, textvariable=self.var_search, width=18, font=FONT).pack(
            side='left', padx=(4, 8))
        tk.Button(bar, text='查询', command=self._refresh, bg=COLOR_ACCENT, fg='white',
                  relief='flat', font=FONT, cursor='hand2').pack(side='left', padx=(0, 6))

        tk.Button(bar, text='刷新', command=self._refresh, bg='#5b6b85', fg='white',
                  relief='flat', font=FONT, cursor='hand2').pack(side='left')

        right = tk.Frame(bar, bg=COLOR_BG)
        right.pack(side='right')
        if self.is_admin:
            for text, cmd in (('添加学生', self._add_student),
                              ('修改信息', self._edit_student),
                              ('编辑成绩', self._edit_grades),
                              ('删除学生', self._delete_student),
                              ('账号管理', self._manage_accounts),
                              ('审核申请', self._manage_requests)):
                tk.Button(right, text=text, bg=COLOR_BTN_T, fg='white', relief='flat',
                          font=FONT, cursor='hand2', command=cmd).pack(
                    side='left', padx=3)

        # 表格容器（管理员额外拥有「教师信息」页签）
        self.nb = ttk.Notebook(self.win)
        self.nb.pack(fill='both', expand=True, padx=12)

        self.stu_tab = tk.Frame(self.nb, bg=COLOR_BG)
        self.nb.add(self.stu_tab, text='学生信息')
        self.table_frame = tk.Frame(self.stu_tab, bg=COLOR_BG)
        self.table_frame.pack(fill='both', expand=True)

        if self.is_admin:
            self.tea_tab = tk.Frame(self.nb, bg=COLOR_BG)
            self.nb.add(self.tea_tab, text='教师信息')
            self.tea_tree = self._make_info_tree(self.tea_tab)

        # 底部状态栏
        role_txt = '管理员（全部权限）' if self.is_admin else '普通教师（只读）'
        tk.Label(self.win, text=f'当前登录：{self.teacher["name"]}（{self.teacher["id"]}）  {role_txt}',
                 bg=COLOR_HEAD, fg='white', font=('Microsoft YaHei', 9),
                 anchor='w').pack(fill='x', side='bottom', ipady=4)

    def _all_subjects(self) -> list[str]:
        subs = set()
        for s in self.db.data['students']:
            subs.update(s['grades'].keys())
        return sorted(subs)

    def _refresh(self) -> None:
        kw = self.var_search.get().strip().lower()
        for w in self.table_frame.winfo_children():
            w.destroy()

        subs = self._all_subjects()
        cols = ['学号', '姓名', '性别', '班级', '电话'] + subs + ['总分']
        widths = [90, 90, 60, 120, 130] + [60] * len(subs) + [70]

        tree = ttk.Treeview(self.table_frame, columns=cols, show='headings',
                            height=18)
        for c, w in zip(cols, widths):
            tree.heading(c, text=c)
            tree.column(c, width=w, anchor='center')
        ysb = ttk.Scrollbar(self.table_frame, orient='vertical', command=tree.yview)
        tree.configure(yscrollcommand=ysb.set)
        tree.pack(side='left', fill='both', expand=True)
        ysb.pack(side='right', fill='y')

        for s in self.db.data['students']:
            if kw and kw not in (s['id'] + s['name'] + s['class_name']).lower():
                continue
            total = sum(s['grades'].values())
            row = [s['id'], s['name'], s['gender'], s['class_name'], s['phone']]
            row += [s['grades'].get(sub, '-') for sub in subs]
            row += [total if s['grades'] else '-']
            tree.insert('', 'end', iid=s['id'], values=row)
        self._tree = tree
        self._refresh_teacher_tab()

    def _make_info_tree(self, parent) -> ttk.Treeview:
        """通用信息表格（带滚动条）"""
        frame = tk.Frame(parent, bg=COLOR_BG)
        frame.pack(fill='both', expand=True)
        cols = ('工号', '姓名', '角色')
        tree = ttk.Treeview(frame, columns=cols, show='headings', height=18)
        for c in cols:
            tree.heading(c, text=c)
            tree.column(c, width=200, anchor='center')
        ysb = ttk.Scrollbar(frame, orient='vertical', command=tree.yview)
        tree.configure(yscrollcommand=ysb.set)
        tree.pack(side='left', fill='both', expand=True)
        ysb.pack(side='right', fill='y')
        return tree

    def _refresh_teacher_tab(self) -> None:
        """管理员可见：展示全部教师信息"""
        if not self.is_admin:
            return
        self.tea_tree.delete(*self.tea_tree.get_children())
        for t in self.db.data['teachers']:
            role = '管理员' if t['role'] == 'admin' else '普通教师'
            self.tea_tree.insert('', 'end', iid=t['id'],
                                 values=(t['id'], t['name'], role))

    # ---------- 选中学生 ----------
    def _selected_student(self):
        tree = getattr(self, '_tree', None)
        if tree is None:
            return None
        sel = tree.selection()
        if not sel:
            messagebox.showinfo('提示', '请先在表格中选中一名学生', parent=self.win)
            return None
        return self.db.find_student(sel[0])

    # ---------- 管理员操作 ----------
    def _add_student(self) -> None:
        StudentForm(self.win, self.db, self._refresh)

    def _edit_student(self) -> None:
        s = self._selected_student()
        if s is None:
            return
        StudentForm(self.win, self.db, self._refresh, student=s)

    def _delete_student(self) -> None:
        s = self._selected_student()
        if s is None:
            return
        if not messagebox.askyesno('确认', f'确定删除学生 {s["name"]}（{s["id"]}）吗？\n'
                                          f'其成绩与相关申请将一并删除。', parent=self.win):
            return
        ok, msg = self.db.delete_student(s['id'])
        messagebox.showinfo('结果', msg, parent=self.win)
        self._refresh()

    def _edit_grades(self) -> None:
        s = self._selected_student()
        if s is None:
            return
        GradeDialog(self.win, self.db, s, self._refresh)

    def _manage_accounts(self) -> None:
        AccountDialog(self.win, self.db, self.teacher)

    def _manage_requests(self) -> None:
        RequestDialog(self.win, self.db)

    def run(self) -> None:
        self.win.mainloop()


class StudentForm(tk.Toplevel):
    """添加 / 修改学生信息对话框"""

    def __init__(self, master: tk.Misc, db: Database,
                 on_saved: Callable[[], None], student: Record | None = None):
        super().__init__(master)
        self.db = db
        self.on_saved = on_saved
        self.student = student
        self.title('修改学生信息' if student else '添加学生')
        self.geometry('360x360')
        self.resizable(False, False)
        self.configure(bg=COLOR_BG)

        body = tk.Frame(self, bg=COLOR_BG)
        body.pack(fill='both', expand=True, padx=24, pady=14)
        entries = {}

        def row(label: str, key: str, show: str = ''):
            tk.Label(body, text=label, bg=COLOR_BG, font=FONT).pack(anchor='w', pady=(8, 2))
            var = tk.StringVar()
            if student:
                var.set(student.get(key, ''))
            ent = tk.Entry(body, textvariable=var, show=show, font=FONT)
            ent.pack(fill='x', ipady=3)
            entries[key] = var

        if student is None:
            row('学号 *', 'id')
        row('姓名 *', 'name')
        tk.Label(body, text='性别', bg=COLOR_BG, font=FONT).pack(anchor='w', pady=(8, 2))
        var_g = tk.StringVar(value=student.get('gender', '男') if student else '男')
        ttk.Combobox(body, textvariable=var_g, values=('男', '女'),
                     state='readonly', font=FONT).pack(fill='x')
        entries['gender'] = var_g
        row('班级', 'class_name')
        row('电话', 'phone')
        if student is None:
            row('初始密码 *', 'password', show='*')

        btns = tk.Frame(self, bg=COLOR_BG)
        btns.pack(pady=12)
        tk.Button(btns, text='保存', width=10, bg=COLOR_ACCENT, fg='white',
                  relief='flat', font=FONT, cursor='hand2',
                  command=lambda: self._save(entries)).pack(side='left', padx=6)
        tk.Button(btns, text='取消', width=10, bg='#7a8699', fg='white',
                  relief='flat', font=FONT, cursor='hand2',
                  command=self.destroy).pack(side='left', padx=6)

    def _save(self, entries: dict[str, tk.StringVar]) -> None:
        if self.student is None:
            sid = entries['id'].get().strip()
            pwd = entries['password'].get()
            if not sid or not entries['name'].get().strip() or not pwd:
                messagebox.showwarning('提示', '学号、姓名、初始密码不能为空', parent=self)
                return
            ok, msg = self.db.add_student(sid, entries['name'].get().strip(),
                                          entries['gender'].get(),
                                          entries['class_name'].get().strip(),
                                          entries['phone'].get().strip(), pwd)
        else:
            ok, msg = self.db.update_student_info(
                self.student['id'],
                name=entries['name'].get().strip() or None,
                gender=entries['gender'].get(),
                class_name=entries['class_name'].get().strip() or None,
                phone=entries['phone'].get().strip() or None)
        messagebox.showinfo('结果', msg, parent=self)
        if ok:
            self.on_saved()
            self.destroy()


class GradeDialog(tk.Toplevel):
    """成绩编辑对话框：修改现有科目分数、添加新科目、删除科目"""

    def __init__(self, master: tk.Misc, db: Database, student: Record,
                 on_saved: Callable[[], None]):
        super().__init__(master)
        self.db = db
        self.student = student
        self.on_saved = on_saved
        self.spins: list[tuple[str, tk.Spinbox]] = []
        self.title(f'编辑成绩 - {student["name"]}（{student["id"]}）')
        self.geometry('380x460')
        self.configure(bg=COLOR_BG)

        body = tk.Frame(self, bg=COLOR_BG)
        body.pack(fill='both', expand=True, padx=20, pady=12)

        self.box = tk.Frame(body, bg=COLOR_BG)
        self.box.pack(fill='both', expand=True)
        self._render()

        add_row = tk.Frame(body, bg=COLOR_BG)
        add_row.pack(fill='x', pady=(10, 4))
        tk.Label(add_row, text='新科目:', bg=COLOR_BG, font=FONT).pack(side='left')
        self.var_sub = tk.StringVar()
        tk.Entry(add_row, textvariable=self.var_sub, width=10, font=FONT).pack(
            side='left', padx=2)
        self.var_score = tk.IntVar(value=0)
        tk.Spinbox(add_row, from_=0, to=100, textvariable=self.var_score,
                   width=6, font=FONT).pack(side='left', padx=2)
        tk.Button(add_row, text='添加', command=self._add_subject, bg=COLOR_BTN_S,
                  fg='white', relief='flat', font=FONT, cursor='hand2').pack(
            side='left', padx=4)

        btns = tk.Frame(self, bg=COLOR_BG)
        btns.pack(pady=10)
        tk.Button(btns, text='保存', width=10, bg=COLOR_ACCENT, fg='white',
                  relief='flat', font=FONT, cursor='hand2',
                  command=self._save).pack(side='left', padx=6)
        tk.Button(btns, text='取消', width=10, bg='#7a8699', fg='white',
                  relief='flat', font=FONT, cursor='hand2',
                  command=self.destroy).pack(side='left', padx=6)

    def _render(self) -> None:
        for w in self.box.winfo_children():
            w.destroy()
        self.spins = []
        if not self.student['grades']:
            tk.Label(self.box, text='（暂无成绩，可在下方添加科目）', bg=COLOR_BG,
                     fg='#8a94a6', font=FONT).pack(pady=20)
        for sub, score in self.student['grades'].items():
            row = tk.Frame(self.box, bg=COLOR_BG)
            row.pack(fill='x', pady=3)
            tk.Label(row, text=sub, width=12, bg=COLOR_BG, font=FONT,
                     anchor='w').pack(side='left')
            var = tk.IntVar(value=score)
            sp = tk.Spinbox(row, from_=0, to=100, textvariable=var, width=8, font=FONT)
            sp.pack(side='left')
            self.spins.append((sub, sp))
            tk.Button(row, text='删', width=3, bg=COLOR_DANGER, fg='white',
                      relief='flat', font=FONT, cursor='hand2',
                      command=lambda x=sub: self._del_subject(x)).pack(
                side='left', padx=4)

    def _del_subject(self, sub: str) -> None:
        self.student['grades'].pop(sub, None)
        self._render()

    def _add_subject(self) -> None:
        sub = self.var_sub.get().strip()
        if not sub:
            messagebox.showwarning('提示', '请填写科目名称', parent=self)
            return
        if sub in self.student['grades']:
            messagebox.showwarning('提示', '该科目已存在', parent=self)
            return
        self.student['grades'][sub] = self.var_score.get()
        self.var_sub.set('')
        self._render()

    def _save(self) -> None:
        grades = {sub: int(sp.get() or 0) for sub, sp in self.spins}
        ok, msg = self.db.set_grades(self.student['id'], grades)
        messagebox.showinfo('结果', msg, parent=self)
        if ok:
            self.on_saved()
            self.destroy()


class AccountDialog(tk.Toplevel):
    """账号管理（仅管理员）：教师/学生账号的增删与密码重置"""

    def __init__(self, master: tk.Misc, db: Database, current_teacher: Record):
        super().__init__(master)
        self.db = db
        self.current = current_teacher
        self.title('账号管理')
        self.geometry('760x460')
        self.configure(bg=COLOR_BG)

        nb = ttk.Notebook(self)
        nb.pack(fill='both', expand=True, padx=10, pady=10)

        self.teacher_frame = tk.Frame(nb, bg=COLOR_BG)
        self.student_frame = tk.Frame(nb, bg=COLOR_BG)
        nb.add(self.teacher_frame, text='教师账号')
        nb.add(self.student_frame, text='学生账号')

        self._build_teacher_tab()
        self._build_student_tab()

    def _make_tree(self, parent: tk.Misc, cols: tuple[str, ...]):
        frame = tk.Frame(parent, bg=COLOR_BG)
        frame.pack(fill='both', expand=True, padx=8, pady=8)
        tree = ttk.Treeview(frame, columns=cols, show='headings', height=10)
        for c in cols:
            tree.heading(c, text=c)
            tree.column(c, width=120, anchor='center')
        ysb = ttk.Scrollbar(frame, orient='vertical', command=tree.yview)
        tree.configure(yscrollcommand=ysb.set)
        tree.pack(side='left', fill='both', expand=True)
        ysb.pack(side='right', fill='y')
        return tree

    def _build_teacher_tab(self) -> None:
        bar = tk.Frame(self.teacher_frame, bg=COLOR_BG)
        bar.pack(fill='x', padx=8)
        tk.Button(bar, text='添加教师', command=self._add_teacher, bg=COLOR_BTN_T,
                  fg='white', relief='flat', font=FONT, cursor='hand2').pack(side='left', padx=3)
        tk.Button(bar, text='删除选中', command=self._del_teacher, bg=COLOR_DANGER,
                  fg='white', relief='flat', font=FONT, cursor='hand2').pack(side='left', padx=3)
        tk.Button(bar, text='重置密码', command=lambda: self._reset(self.t_tree),
                  bg=COLOR_ACCENT, fg='white', relief='flat', font=FONT,
                  cursor='hand2').pack(side='left', padx=3)
        self.t_tree = self._make_tree(self.teacher_frame, ('工号', '姓名', '角色'))
        self._reload_teachers()

    def _build_student_tab(self) -> None:
        bar = tk.Frame(self.student_frame, bg=COLOR_BG)
        bar.pack(fill='x', padx=8)
        tk.Button(bar, text='重置密码', command=lambda: self._reset(self.s_tree),
                  bg=COLOR_ACCENT, fg='white', relief='flat', font=FONT,
                  cursor='hand2').pack(side='left', padx=3)
        self.s_tree = self._make_tree(self.student_frame,
                                      ('学号', '姓名', '班级', '电话'))
        self._reload_students()

    def _reload_teachers(self) -> None:
        self.t_tree.delete(*self.t_tree.get_children())
        for t in self.db.data['teachers']:
            role = '管理员' if t['role'] == 'admin' else '普通教师'
            self.t_tree.insert('', 'end', iid=t['id'], values=(t['id'], t['name'], role))

    def _reload_students(self) -> None:
        self.s_tree.delete(*self.s_tree.get_children())
        for s in self.db.data['students']:
            self.s_tree.insert('', 'end', iid=s['id'],
                               values=(s['id'], s['name'], s['class_name'], s['phone']))

    def _add_teacher(self) -> None:
        dialog = tk.Toplevel(self)
        dialog.title('添加教师')
        dialog.geometry('320x230')
        dialog.configure(bg=COLOR_BG)
        frame = tk.Frame(dialog, bg=COLOR_BG)
        frame.pack(padx=20, pady=14)
        vars_ = {}

        def row(label: str, key: str, show: str = ''):
            tk.Label(frame, text=label, bg=COLOR_BG, font=FONT).pack(anchor='w', pady=(6, 2))
            var = tk.StringVar()
            tk.Entry(frame, textvariable=var, show=show, font=FONT).pack(fill='x', ipady=3)
            vars_[key] = var

        row('工号 *', 'id')
        row('姓名 *', 'name')
        row('初始密码 *', 'password', show='*')
        btn = tk.Frame(dialog, bg=COLOR_BG)
        btn.pack(pady=8)

        def save() -> None:
            tid = vars_['id'].get().strip()
            name = vars_['name'].get().strip()
            pwd = vars_['password'].get()
            if not tid or not name or not pwd:
                messagebox.showwarning('提示', '工号、姓名、密码不能为空', parent=dialog)
                return
            ok, msg = self.db.add_teacher(tid, name, pwd)
            messagebox.showinfo('结果', msg, parent=dialog)
            if ok:
                self._reload_teachers()
                dialog.destroy()

        tk.Button(btn, text='保存', width=10, bg=COLOR_ACCENT, fg='white',
                  relief='flat', font=FONT, cursor='hand2', command=save).pack(side='left', padx=5)
        tk.Button(btn, text='取消', width=10, bg='#7a8699', fg='white',
                  relief='flat', font=FONT, cursor='hand2',
                  command=dialog.destroy).pack(side='left', padx=5)

    def _del_teacher(self) -> None:
        sel = self.t_tree.selection()
        if not sel:
            messagebox.showinfo('提示', '请先选中教师账号', parent=self)
            return
        tid = sel[0]
        if tid == self.current['id']:
            messagebox.showwarning('提示', '不能删除当前登录的账号', parent=self)
            return
        if not messagebox.askyesno('确认', f'确定删除教师账号 {tid} 吗？', parent=self):
            return
        ok, msg = self.db.delete_teacher(tid)
        messagebox.showinfo('结果', msg, parent=self)
        self._reload_teachers()

    def _reset(self, tree: ttk.Treeview) -> None:
        sel = tree.selection()
        if not sel:
            messagebox.showinfo('提示', '请先选中一个账号', parent=self)
            return
        from tkinter import simpledialog
        new_pwd = simpledialog.askstring('重置密码', '请输入新密码：', show='*', parent=self)
        if new_pwd is None:
            return
        rec = self.db.find_teacher(sel[0]) or self.db.find_student(sel[0])
        if rec is None:
            return
        ok, msg = self.db.reset_password(rec, new_pwd)
        messagebox.showinfo('结果', msg, parent=self)


class RequestDialog(tk.Toplevel):
    """学生修改申请审核（仅管理员）"""

    def __init__(self, master: tk.Misc, db: Database):
        super().__init__(master)
        self.db = db
        self.title('修改申请审核')
        self.geometry('760x420')
        self.configure(bg=COLOR_BG)

        bar = tk.Frame(self, bg=COLOR_BG)
        bar.pack(fill='x', padx=10, pady=6)
        tk.Button(bar, text='批准选中', bg=COLOR_BTN_S, fg='white', relief='flat',
                  font=FONT, cursor='hand2', command=lambda: self._handle(True)).pack(
            side='left', padx=3)
        tk.Button(bar, text='拒绝选中', bg=COLOR_DANGER, fg='white', relief='flat',
                  font=FONT, cursor='hand2', command=lambda: self._handle(False)).pack(
            side='left', padx=3)
        tk.Button(bar, text='刷新', bg='#5b6b85', fg='white', relief='flat',
                  font=FONT, cursor='hand2', command=self._reload).pack(side='left', padx=3)

        frame = tk.Frame(self, bg=COLOR_BG)
        frame.pack(fill='both', expand=True, padx=10, pady=(0, 10))
        cols = ('申请号', '学号', '姓名', '修改字段', '原值', '新值', '状态', '时间')
        self.tree = ttk.Treeview(frame, columns=cols, show='headings', height=12)
        widths = (70, 90, 90, 90, 130, 130, 80, 150)
        for c, w in zip(cols, widths):
            self.tree.heading(c, text=c)
            self.tree.column(c, width=w, anchor='center')
        ysb = ttk.Scrollbar(frame, orient='vertical', command=self.tree.yview)
        self.tree.configure(yscrollcommand=ysb.set)
        self.tree.pack(side='left', fill='both', expand=True)
        ysb.pack(side='right', fill='y')
        self._reload()

    def _reload(self) -> None:
        self.tree.delete(*self.tree.get_children())
        for r in self.db.list_requests():
            self.tree.insert('', 'end', iid=str(r['req_id']), values=(
                r['req_id'], r['student_id'], r['student_name'], r['field_label'],
                r['old_value'], r['new_value'], r['status'], r['time']))

    def _handle(self, approve: bool) -> None:
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo('提示', '请先选中一条申请', parent=self)
            return
        ok, msg = self.db.handle_request(int(sel[0]), approve)
        messagebox.showinfo('结果', msg, parent=self)
        self._reload()


# ============================================================
# 学生端
# ============================================================
class StudentApp:
    """学生端主窗口：仅查看自己的信息与成绩，修改需提交申请"""

    def __init__(self, db: Database, student: Record):
        self.db = db
        self.student = student
        self.win = tk.Tk()
        self.win.title(f'学生端 - {student["name"]}')
        self.win.geometry('760x560')
        self.win.configure(bg=COLOR_BG)
        self._build()
        self._refresh()

    def _build(self) -> None:
        head = tk.Frame(self.win, bg=COLOR_HEAD)
        head.pack(fill='x', ipady=10)
        tk.Label(head, text=f'欢迎，{self.student["name"]}（{self.student["id"]}）',
                 bg=COLOR_HEAD, fg='white', font=('Microsoft YaHei', 15, 'bold')).pack()

        body = tk.Frame(self.win, bg=COLOR_BG)
        body.pack(fill='both', expand=True, padx=16, pady=12)

        # 左侧：个人信息
        left = tk.Frame(body, bg=COLOR_BG)
        left.pack(side='left', fill='y', padx=(0, 14))
        tk.Label(left, text='我的信息', bg=COLOR_HEAD, fg='white', font=FONT,
                 width=18).pack(ipady=4)
        self.info = {}
        for key, label in (('id', '学号'), ('name', '姓名'), ('gender', '性别'),
                           ('class_name', '班级'), ('phone', '电话')):
            tk.Label(left, text=label, bg=COLOR_BG, font=FONT, anchor='w',
                     width=18).pack(pady=(8, 0))
            var = tk.StringVar()
            tk.Label(left, textvariable=var, bg='white', font=FONT, anchor='w',
                     width=18).pack(ipady=3)
            self.info[key] = var

        tk.Label(left, text='', bg=COLOR_BG).pack()
        tk.Button(left, text='申请修改信息', command=self._request_change,
                  bg=COLOR_BTN_S, fg='white', relief='flat', font=FONT,
                  cursor='hand2', width=18).pack(pady=3)
        tk.Button(left, text='我的申请记录', command=self._my_requests,
                  bg=COLOR_BTN_T, fg='white', relief='flat', font=FONT,
                  cursor='hand2', width=18).pack(pady=3)
        tk.Label(left, text='修改需管理员审核通过后生效', bg=COLOR_BG, fg='#8a94a6',
                 font=('Microsoft YaHei', 8)).pack(pady=(6, 0))

        # 右侧：成绩
        right = tk.Frame(body, bg=COLOR_BG)
        right.pack(side='left', fill='both', expand=True)
        tk.Label(right, text='我的成绩', bg=COLOR_HEAD, fg='white', font=FONT).pack(
            fill='x', ipady=4)
        self.table_frame = tk.Frame(right, bg=COLOR_BG)
        self.table_frame.pack(fill='both', expand=True, pady=8)

    def _refresh(self) -> None:
        s = self.student
        for k, var in self.info.items():
            var.set(s.get(k, ''))
        for w in self.table_frame.winfo_children():
            w.destroy()

        tree = ttk.Treeview(self.table_frame, columns=('科目', '分数'),
                            show='headings', height=12)
        tree.heading('科目', text='科目')
        tree.heading('分数', text='分数')
        tree.column('科目', width=180, anchor='center')
        tree.column('分数', width=120, anchor='center')
        ysb = ttk.Scrollbar(self.table_frame, orient='vertical', command=tree.yview)
        tree.configure(yscrollcommand=ysb.set)
        tree.pack(side='left', fill='both', expand=True)
        ysb.pack(side='right', fill='y')

        grades = s['grades']
        if not grades:
            tree.insert('', 'end', values=('（暂无成绩）', ''))
        for sub, score in grades.items():
            tree.insert('', 'end', values=(sub, score))
        total = sum(grades.values())
        avg = round(total / len(grades), 1) if grades else 0
        tk.Label(self.table_frame, text=f'总分：{total}    平均分：{avg}',
                 bg=COLOR_BG, fg=COLOR_ACCENT, font=('Microsoft YaHei', 11, 'bold')
                 ).pack(side='bottom', pady=6)

    def _request_change(self) -> None:
        ChangeRequestDialog(self.win, self.db, self.student, self._refresh)

    def _my_requests(self) -> None:
        MyRequestsDialog(self.win, self.db, self.student)

    def run(self) -> None:
        self.win.mainloop()


class ChangeRequestDialog(tk.Toplevel):
    """学生申请修改信息"""

    def __init__(self, master: tk.Misc, db: Database, student: Record,
                 on_saved: Callable[[], None]):
        super().__init__(master)
        self.db = db
        self.student = student
        self.on_saved = on_saved
        self.title('申请修改信息')
        self.geometry('360x240')
        self.resizable(False, False)
        self.configure(bg=COLOR_BG)

        body = tk.Frame(self, bg=COLOR_BG)
        body.pack(fill='both', expand=True, padx=24, pady=16)

        tk.Label(body, text='选择修改项', bg=COLOR_BG, font=FONT).pack(anchor='w')
        self.var_field = tk.StringVar()
        box = ttk.Combobox(body, textvariable=self.var_field, state='readonly',
                           values=list(EDITABLE_FIELDS.values()), font=FONT)
        box.pack(fill='x', ipady=2, pady=(2, 10))
        box.current(0)

        tk.Label(body, text='新的内容', bg=COLOR_BG, font=FONT).pack(anchor='w')
        self.var_new = tk.StringVar()
        tk.Entry(body, textvariable=self.var_new, font=FONT).pack(
            fill='x', ipady=3, pady=(2, 14))

        btns = tk.Frame(self, bg=COLOR_BG)
        btns.pack(pady=8)
        tk.Button(btns, text='提交申请', width=10, bg=COLOR_ACCENT, fg='white',
                  relief='flat', font=FONT, cursor='hand2',
                  command=self._submit).pack(side='left', padx=5)
        tk.Button(btns, text='取消', width=10, bg='#7a8699', fg='white',
                  relief='flat', font=FONT, cursor='hand2',
                  command=self.destroy).pack(side='left', padx=5)

    def _submit(self) -> None:
        label = self.var_field.get()
        field = next((k for k, v in EDITABLE_FIELDS.items() if v == label), None)
        if field is None:
            return
        new_value = self.var_new.get().strip()
        if not new_value:
            messagebox.showwarning('提示', '请填写新的内容', parent=self)
            return
        ok, msg = self.db.add_request(self.student, field, new_value)
        messagebox.showinfo('结果', msg, parent=self)
        if ok:
            self.on_saved()
            self.destroy()


class MyRequestsDialog(tk.Toplevel):
    """学生查看自己的申请记录"""

    def __init__(self, master: tk.Misc, db: Database, student: Record):
        super().__init__(master)
        self.db = db
        self.student = student
        self.title('我的申请记录')
        self.geometry('620x360')
        self.configure(bg=COLOR_BG)

        frame = tk.Frame(self, bg=COLOR_BG)
        frame.pack(fill='both', expand=True, padx=12, pady=12)
        cols = ('申请号', '修改字段', '原值', '新值', '状态', '时间')
        tree = ttk.Treeview(frame, columns=cols, show='headings', height=10)
        widths = (70, 90, 140, 140, 90, 150)
        for c, w in zip(cols, widths):
            tree.heading(c, text=c)
            tree.column(c, width=w, anchor='center')
        ysb = ttk.Scrollbar(frame, orient='vertical', command=tree.yview)
        tree.configure(yscrollcommand=ysb.set)
        tree.pack(side='left', fill='both', expand=True)
        ysb.pack(side='right', fill='y')

        for r in self.db.list_requests(self.student['id']):
            tree.insert('', 'end', values=(
                r['req_id'], r['field_label'], r['old_value'], r['new_value'],
                r['status'], r['time']))


def main() -> None:
    db = Database()
    LoginApp(db).run()


if __name__ == '__main__':
    main()
