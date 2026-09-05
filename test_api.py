# -*- coding: utf-8 -*-
"""接口联调脚本：登录 → 鉴权 → 增删改查 → 越权拦截 → 还原数据"""
import json
import os
import urllib.request
import urllib.error

BASE = os.environ.get("TEST_BASE_URL", "http://127.0.0.1:8000") + "/api"


def call(path, method="GET", body=None, token=None):
    req = urllib.request.Request(BASE + path, method=method)
    if body is not None:
        req.add_header("Content-Type", "application/json")
        req.data = json.dumps(body, ensure_ascii=False).encode("utf-8")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req) as resp:
            return resp.status, json.loads(resp.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read())


passed = failed = 0


def check(name, cond, detail=""):
    global passed, failed
    if cond:
        passed += 1
        print(f"[通过] {name}")
    else:
        failed += 1
        print(f"[失败] {name}  {detail}")


# 1. 管理员登录
st, r = call("/login", "POST", {"username": "admin", "password": "admin123", "role": "teacher"})
check("管理员登录", st == 200 and r["code"] == 200 and r["data"]["user"]["role"] == "admin", r)
admin_token = r["data"]["token"]

# 2. 密码错误
st, r = call("/login", "POST", {"username": "admin", "password": "wrong", "role": "teacher"})
check("密码错误被拒", st == 200 and r["code"] == 400, r)

# 3. 无 token 访问
st, r = call("/students")
check("无 token 访问返回 401", st == 401, r)

# 4. 学生列表（含姓名中文完整性）
st, r = call("/students", token=admin_token)
check("学生列表", st == 200 and len(r["data"]) == 3 and r["data"][0]["name"] == "张三", r)

# 5. 关键词搜索
st, r = call("/students?keyword=" + urllib.parse.quote("王五"), token=admin_token)
check("关键词搜索", st == 200 and len(r["data"]) == 1, r)

# 6. 新增学生（附带成绩，一步保存）
st, r = call("/students", "POST",
             {"id": "2024004", "name": "赵六", "gender": "女",
              "class_name": "网络2403", "phone": "13800000004", "password": "123456",
              "grades": {"语文": 70, "数学": 82}},
             token=admin_token)
check("新增学生", st == 200 and r["code"] == 200, r)

st, r = call("/students/2024004", token=admin_token)
check("新增时成绩一并保存", st == 200 and r["data"]["grades"] == {"语文": 70, "数学": 82}
      and r["data"]["total"] == 152, r)

# 7. 重复学号被拒
st, r = call("/students", "POST",
             {"id": "2024004", "name": "x", "password": "123456"}, token=admin_token)
check("重复学号被拒", st == 200 and r["code"] == 400, r)

# 8. 修改信息
st, r = call("/students/2024004", "PUT", {"phone": "13900000004"}, token=admin_token)
check("修改信息", st == 200 and r["code"] == 200, r)

# 9. 覆盖成绩
st, r = call("/students/2024004/grades", "PUT", {"grades": {"语文": 88, "数学": 95}}, token=admin_token)
check("覆盖成绩", st == 200 and r["code"] == 200, r)

# 10. 成绩越界被拒
st, r = call("/students/2024004/grades", "PUT", {"grades": {"语文": 120}}, token=admin_token)
check("分数越界被拒", st == 422, r)

# 11. 详情核对修改结果
st, r = call("/students/2024004", token=admin_token)
check("详情核对", st == 200 and r["data"]["phone"] == "13900000004"
      and r["data"]["total"] == 183 and "salt" not in r["data"], r)

# 12. 学生 token：只能看自己
st, r = call("/login", "POST", {"username": "2024001", "password": "123456", "role": "student"})
stu_token = r["data"]["token"]
st, r = call("/me", token=stu_token)
check("学生查看自己信息", st == 200 and r["data"]["id"] == "2024001", r)
st, r = call("/students/2024002", token=stu_token)
check("学生看他人信息被拒", st == 403, r)
st, r = call("/students/2024004", "DELETE", token=stu_token)
check("学生越权删除被拒", st == 403, r)

# 13. 普通教师只读
st, r = call("/login", "POST", {"username": "t001", "password": "123456", "role": "teacher"})
t_token = r["data"]["token"]
st, r = call("/students", token=t_token)
check("教师可查列表", st == 200 and r["code"] == 200, r)
st, r = call("/students/2024004", "DELETE", token=t_token)
check("教师删除被拒(403)", st == 403, r)

# 14. 删除测试学生，还原
st, r = call("/students/2024004", "DELETE", token=admin_token)
check("删除还原", st == 200 and r["code"] == 200, r)
st, r = call("/students", token=admin_token)
check("数据已还原(3人)", st == 200 and len(r["data"]) == 3, r)

# 15. 修改自己的密码：旧密码错误被拒 → 修改成功 → 新密码可登录 → 改回原密码
st, r = call("/me/password", "PUT",
             {"old_password": "wrong", "new_password": "temp1234"}, token=admin_token)
check("改密-旧密码错误被拒", st == 200 and r["code"] == 400, r)
st, r = call("/me/password", "PUT",
             {"old_password": "admin123", "new_password": "temp1234"}, token=admin_token)
check("改密-成功", st == 200 and r["code"] == 200, r)
st, r = call("/login", "POST", {"username": "admin", "password": "temp1234", "role": "teacher"})
check("改密-新密码可登录", st == 200 and r["code"] == 200, r)
st, r = call("/login", "POST", {"username": "admin", "password": "admin123", "role": "teacher"})
check("改密-旧密码已失效", st == 200 and r["code"] == 400, r)
# 改回原密码（用刚拿到的新 token）
st, r = call("/login", "POST", {"username": "admin", "password": "temp1234", "role": "teacher"})
temp_token = r["data"]["token"]
st, r = call("/me/password", "PUT",
             {"old_password": "temp1234", "new_password": "admin123"}, token=temp_token)
check("改密-已还原", st == 200 and r["code"] == 200, r)
st, r = call("/login", "POST", {"username": "admin", "password": "admin123", "role": "teacher"})
admin_token = r["data"]["token"]
check("改密-还原后原密码恢复可用", st == 200 and r["code"] == 200, r)

# 16. 数据统计
st, r = call("/stats", token=admin_token)
check("统计-管理员可用", st == 200 and r["data"]["student_count"] == 3
      and len(r["data"]["classes"]) >= 2 and len(r["data"]["subject_avg"]) >= 3, r)
st, r = call("/stats", token=stu_token)
check("统计-学生被拒", st == 403, r)

# 17. 教师账号管理：添加 → 列表可见 → 重置密码 → 新密码登录 → 删除
st, r = call("/teachers", "POST",
             {"id": "t900", "name": "测试老师", "password": "123456"}, token=admin_token)
check("添加教师", st == 200 and r["code"] == 200, r)
st, r = call("/teachers", token=admin_token)
check("教师列表含新账号", st == 200 and any(t["id"] == "t900" for t in r["data"]), r)
st, r = call("/teachers", token=t_token)
check("教师列表-普通教师被拒", st == 403, r)
st, r = call("/passwords/reset", "POST",
             {"target_id": "t900", "new_password": "654321"}, token=admin_token)
check("重置密码", st == 200 and r["code"] == 200, r)
st, r = call("/login", "POST", {"username": "t900", "password": "654321", "role": "teacher"})
check("新密码可登录", st == 200 and r["code"] == 200, r)
st, r = call("/teachers/t900", "DELETE", token=admin_token)
check("删除测试教师", st == 200 and r["code"] == 200, r)

# 18. 修改申请全流程：学生提交 → 管理员批准 → 信息生效 → 管理员接口还原
orig_phone = call("/students/2024001", token=admin_token)[1]["data"]["phone"]
st, r = call("/requests", "POST", {"field": "phone", "new_value": "13711112222"}, token=stu_token)
check("学生提交申请", st == 200 and r["code"] == 200, r)
st, r = call("/requests", token=stu_token)
req_id = r["data"][0]["req_id"]
check("学生查看自己的申请", st == 200 and r["data"][0]["status"] == "pending", r)
st, r = call("/requests", token=t_token)
check("普通教师查看申请被拒", st == 403, r)
st, r = call(f"/requests/{req_id}/handle", "POST", {"approve": True}, token=admin_token)
check("管理员批准申请", st == 200 and r["code"] == 200, r)
st, r = call("/students/2024001", token=admin_token)
check("批准后信息已生效", st == 200 and r["data"]["phone"] == "13711112222", r)
# 还原电话
st, r = call("/students/2024001", "PUT", {"phone": orig_phone}, token=admin_token)
check("测试数据已还原(电话)", st == 200 and r["code"] == 200, r)
st, r = call("/students/2024001", token=admin_token)
check("电话已还原", st == 200 and r["data"]["phone"] == orig_phone, r)

# 19. 静态页面可访问
SITE = BASE.rsplit("/", 1)[0]
for page in ("/", "/teacher.html", "/student.html"):
    with urllib.request.urlopen(SITE + page) as resp:
        check(f"页面 {page}", resp.status == 200 and "学生管理系统" in resp.read().decode("utf-8"))

print(f"\n结果：{passed} 通过 / {failed} 失败")
