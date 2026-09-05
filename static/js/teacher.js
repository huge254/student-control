// 教师端：管理员拥有全部功能，普通教师只读
const user = getUser();
if (!user || user.role === "student") { location.replace("/"); throw new Error("no auth"); }

const isAdmin = user.role === "admin";
// 普通教师：直接从 DOM 移除管理员专属元素
if (!isAdmin) document.querySelectorAll(".admin-only").forEach(el => el.remove());
document.getElementById("whoami").textContent =
  `当前登录：${user.name}（${user.id}） · ${isAdmin ? "管理员（全部权限）" : "普通教师（只读）"}`;

const $ = id => document.getElementById(id);
// 安全绑定：元素可能因权限差异已被移除，不存在则跳过（避免脚本报错中断）
function on(id, fn) {
  const el = $(id);
  if (el) el.onclick = fn;
}

let students = [];
let selectedId = null;
let gradeDraft = {};

/* ---------- 数据加载与渲染（所有角色） ---------- */
async function load() {
  const res = await api("/students?keyword=" + encodeURIComponent($("keyword").value.trim()));
  if (res.code !== 200) { alert(res.msg); return; }
  students = res.data;
  render();
  updateOverview();
}

async function updateOverview() {
  $("ovStudents").textContent = students.length;
  $("ovClasses").textContent = new Set(students.map(s => s.class_name)).size;
  const scores = students.flatMap(s => Object.values(s.grades));
  $("ovAvg").textContent = scores.length
    ? (scores.reduce((a, b) => a + b, 0) / scores.length).toFixed(1)
    : "-";
  if (isAdmin) {
    const res = await api("/requests");
    if (res.code === 200) {
      $("ovPending").textContent =
        res.data.filter(r => r.status === "pending").length;
    }
  } else {
    $("ovPending").textContent = "—";
  }
}

function render() {
  const subjects = [...new Set(students.flatMap(s => Object.keys(s.grades)))].sort();
  $("thead").innerHTML = "<tr>" +
    ["学号", "姓名", "性别", "班级", "电话", ...subjects, "总分"]
      .map(h => `<th>${esc(h)}</th>`).join("") + "</tr>";
  $("tbody").innerHTML = students.map(s => {
    const cells = [s.id, s.name, s.gender, s.class_name, s.phone,
      ...subjects.map(sub => s.grades[sub] ?? "-"),
      Object.keys(s.grades).length ? s.total : "-"];
    return `<tr data-id="${esc(s.id)}" class="${s.id === selectedId ? "selected" : ""}">` +
      cells.map(c => `<td>${esc(c)}</td>`).join("") + "</tr>";
  }).join("") || '<tr><td colspan="99">没有匹配的学生</td></tr>';

  document.querySelectorAll("#tbody tr[data-id]").forEach(tr => {
    tr.onclick = () => { selectedId = tr.dataset.id; render(); };
  });
}

function selectedStudent() {
  const s = students.find(x => x.id === selectedId);
  if (!s) alert("请先在表格中选中一名学生");
  return s;
}

on("searchBtn", load);
on("refreshBtn", () => { $("keyword").value = ""; load(); });
const kwEl = $("keyword");
if (kwEl) kwEl.addEventListener("keydown", e => { if (e.key === "Enter") load(); });

/* ---------- 添加 / 修改学生信息（管理员） ---------- */
function openForm(s) {
  $("formTitle").textContent = s ? "修改学生信息" : "添加学生";
  $("rowId").style.display = s ? "none" : "";
  $("rowPwd").style.display = s ? "none" : "";
  $("fId").value = s ? s.id : "";
  $("fName").value = s ? s.name : "";
  $("fGender").value = s ? s.gender : "男";
  $("fClass").value = s ? s.class_name : "";
  $("fPhone").value = s ? s.phone : "";
  $("fPwd").value = "";
  $("formDialog").dataset.editId = s ? s.id : "";
  $("formDialog").showModal();
}

on("addBtn", () => openForm(null));
on("editBtn", () => { const s = selectedStudent(); if (s) openForm(s); });
on("saveFormBtn", async () => {
  const editId = $("formDialog").dataset.editId;
  const common = {
    name: $("fName").value.trim(),
    gender: $("fGender").value,
    class_name: $("fClass").value.trim(),
    phone: $("fPhone").value.trim(),
  };
  if (!common.name) { alert("姓名不能为空"); return; }

  let res;
  if (editId) {
    res = await api("/students/" + encodeURIComponent(editId),
      { method: "PUT", body: JSON.stringify(common) });
  } else {
    const id = $("fId").value.trim(), pwd = $("fPwd").value;
    if (!id || !pwd) { alert("学号和初始密码不能为空"); return; }
    res = await api("/students",
      { method: "POST", body: JSON.stringify({ id, password: pwd, ...common }) });
  }
  alert(res.msg);
  if (res.code === 200) { $("formDialog").close(); load(); }
});
on("cancelFormBtn", () => $("formDialog").close());

/* ---------- 删除学生（管理员） ---------- */
on("delBtn", async () => {
  const s = selectedStudent();
  if (!s) return;
  if (!confirm(`确定删除学生 ${s.name}（${s.id}）吗？\n其成绩与相关申请将一并删除。`)) return;
  const res = await api("/students/" + encodeURIComponent(s.id), { method: "DELETE" });
  alert(res.msg);
  if (res.code === 200) { selectedId = null; load(); }
});

/* ---------- 编辑成绩（管理员） ---------- */
on("gradeBtn", () => {
  const s = selectedStudent();
  if (!s) return;
  gradeDraft = { ...s.grades };
  $("gradeTitle").textContent = `编辑成绩 - ${s.name}（${s.id}）`;
  $("gradeDialog").dataset.sid = s.id;
  renderGrades();
  $("gradeDialog").showModal();
});

function renderGrades() {
  $("gradeList").innerHTML = Object.keys(gradeDraft).length
    ? Object.entries(gradeDraft).map(([sub, score]) =>
        `<div class="grade-row"><span>${esc(sub)}</span>` +
        `<input type="number" min="0" max="100" value="${score}" data-sub="${esc(sub)}">` +
        `<button class="btn danger" data-del="${esc(sub)}">删</button></div>`).join("")
    : '<div style="color:#8a94a6;padding:12px 0">（暂无成绩，可在下方添加科目）</div>';
  $("gradeList").querySelectorAll("[data-del]").forEach(btn =>
    btn.onclick = () => { delete gradeDraft[btn.dataset.del]; renderGrades(); });
}

on("addSubjectBtn", () => {
  const sub = $("newSubject").value.trim();
  if (!sub) { alert("请填写科目名称"); return; }
  if (sub in gradeDraft) { alert("该科目已存在"); return; }
  const score = Number($("newScore").value);
  if (!(score >= 0 && score <= 100)) { alert("分数必须在 0~100 之间"); return; }
  gradeDraft[sub] = score;
  $("newSubject").value = "";
  renderGrades();
});

on("saveGradeBtn", async () => {
  const grades = {};
  for (const input of $("gradeList").querySelectorAll("input[data-sub]")) {
    const v = Number(input.value);
    if (!(v >= 0 && v <= 100)) { alert(`「${input.dataset.sub}」分数必须在 0~100 之间`); return; }
    grades[input.dataset.sub] = v;
  }
  const sid = $("gradeDialog").dataset.sid;
  const res = await api("/students/" + encodeURIComponent(sid) + "/grades",
    { method: "PUT", body: JSON.stringify({ grades }) });
  alert(res.msg);
  if (res.code === 200) { $("gradeDialog").close(); load(); }
});
on("cancelGradeBtn", () => $("gradeDialog").close());

/* ---------- 数据统计 / 导出 / 密码（管理员与普通教师通用） ---------- */
on("statsBtn", async () => {
  $("statsDialog").showModal();
  const res = await api("/stats");
  if (res.code !== 200) { alert(res.msg); return; }
  const d = res.data;
  $("statStudents").textContent = d.student_count;
  $("statTeachers").textContent = d.teacher_count;
  $("statPending").textContent = d.pending_requests;

  const maxCount = Math.max(1, ...d.classes.map(c => c.count));
  $("classBars").innerHTML = d.classes.map(c =>
    `<div class="bar-row"><span class="bar-label">${esc(c.name)}</span>` +
    `<div class="bar-track"><div class="bar-fill" style="width:${c.count / maxCount * 100}%"></div></div>` +
    `<span class="bar-value">${c.count} 人</span></div>`).join("") || '<div class="empty-hint">暂无数据</div>';

  $("avgBars").innerHTML = d.subject_avg.map(s =>
    `<div class="bar-row"><span class="bar-label">${esc(s.subject)}</span>` +
    `<div class="bar-track"><div class="bar-fill green" style="width:${s.avg}%"></div></div>` +
    `<span class="bar-value">${s.avg} 分</span></div>`).join("") || '<div class="empty-hint">暂无成绩</div>';
});

/* 导出 CSV（按当前搜索结果） */
on("exportBtn", () => {
  if (!students.length) { alert("没有可导出的学生"); return; }
  const subjects = [...new Set(students.flatMap(s => Object.keys(s.grades)))].sort();
  const header = ["学号", "姓名", "性别", "班级", "电话", ...subjects, "总分"];
  const rows = students.map(s =>
    [s.id, s.name, s.gender, s.class_name, s.phone,
     ...subjects.map(sub => s.grades[sub] ?? ""),
     Object.keys(s.grades).length ? s.total : ""]);
  const csv = [header, ...rows]
    .map(row => row.map(v => `"${String(v).replace(/"/g, '""')}"`).join(",")).join("\r\n");
  // 加 BOM，让 Excel 正确识别中文
  const blob = new Blob(["\ufeff" + csv], { type: "text/csv;charset=utf-8" });
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = "学生信息导出_" + new Date().toISOString().slice(0, 10) + ".csv";
  a.click();
  URL.revokeObjectURL(a.href);
});

/* 修改自己的密码 */
on("myPwdBtn", () => {
  $("oldPwd").value = $("newPwd").value = $("newPwd2").value = "";
  $("myPwdDialog").showModal();
});
on("cancelMyPwdBtn", () => $("myPwdDialog").close());
on("saveMyPwdBtn", async () => {
  const oldPwd = $("oldPwd").value, newPwd = $("newPwd").value;
  if (!oldPwd || !newPwd) { alert("请填写完整"); return; }
  if (newPwd !== $("newPwd2").value) { alert("两次输入的新密码不一致"); return; }
  const res = await api("/me/password",
    { method: "PUT", body: JSON.stringify({ old_password: oldPwd, new_password: newPwd }) });
  alert(res.msg);
  if (res.code === 200) $("myPwdDialog").close();
});

/* 重置他人密码（管理员） */
function openResetPwd(targetId) {
  $("resetPwdDialog").dataset.target = targetId;
  $("resetPwdTitle").textContent = `重置密码 - ${targetId}`;
  $("resetPwdInput").value = "";
  $("resetPwdDialog").showModal();
}
on("cancelResetPwdBtn", () => $("resetPwdDialog").close());
on("saveResetPwdBtn", async () => {
  const res = await api("/passwords/reset", {
    method: "POST",
    body: JSON.stringify({
      target_id: $("resetPwdDialog").dataset.target,
      new_password: $("resetPwdInput").value,
    }),
  });
  alert(res.msg);
  if (res.code === 200) $("resetPwdDialog").close();
});

/* ---------- 以下仅管理员：页签切换、教师管理、审核申请 ---------- */
if (isAdmin) {
  /* 页签切换 */
  document.querySelectorAll(".page-tab").forEach(btn =>
    btn.onclick = () => {
      document.querySelectorAll(".page-tab")
        .forEach(b => b.classList.toggle("active", b === btn));
      const page = btn.dataset.page;
      $("panel-students").style.display = page === "students" ? "" : "none";
      $("panel-teachers").style.display = page === "teachers" ? "" : "none";
      // 切换工具栏中仅学生相关的元素
      document.querySelectorAll(".stu-ui").forEach(el =>
        el.style.display = page === "students" ? "" : "none");
      if (page === "teachers") reloadTeacherPanel();
    });

  /* 教师面板 */
  async function reloadTeacherPanel() {
    const res = await api("/teachers");
    if (res.code !== 200) { alert(res.msg); return; }
    $("teacherBody").innerHTML = res.data.map(t => {
      const isAdminRow = t.role === "admin";
      const roleBadge = `<span class="badge ${isAdminRow ? "role-admin" : "role-teacher"}">` +
        `${isAdminRow ? "管理员" : "普通教师"}</span>`;
      const actions =
        `<button class="btn outline" style="padding:3px 10px" data-reset="${esc(t.id)}">重置密码</button>` +
        (isAdminRow ? "" :
          ` <button class="btn danger" style="padding:3px 10px" data-del="${esc(t.id)}">删除</button>`);
      return `<tr><td>${esc(t.id)}</td><td>${esc(t.name)}</td>` +
        `<td>${roleBadge}</td><td>${actions}</td></tr>`;
    }).join("");

    $("teacherBody").querySelectorAll("[data-reset]").forEach(btn =>
      btn.onclick = () => openResetPwd(btn.dataset.reset));
    $("teacherBody").querySelectorAll("[data-del]").forEach(btn =>
      btn.onclick = async () => {
        const tid = btn.dataset.del;
        if (!confirm(`确定删除教师账号 ${tid} 吗？`)) return;
        const res = await api("/teachers/" + encodeURIComponent(tid), { method: "DELETE" });
        alert(res.msg);
        if (res.code === 200) reloadTeacherPanel();
      });
  }

  on("addTeacherBtn", () => {
    $("tId").value = $("tName").value = $("tPwd").value = "";
    $("teacherFormDialog").showModal();
  });
  on("cancelTeacherBtn", () => $("teacherFormDialog").close());
  on("saveTeacherBtn", async () => {
    const body = { id: $("tId").value.trim(), name: $("tName").value.trim(), password: $("tPwd").value };
    if (!body.id || !body.name || !body.password) { alert("工号、姓名、密码不能为空"); return; }
    const res = await api("/teachers", { method: "POST", body: JSON.stringify(body) });
    alert(res.msg);
    if (res.code === 200) { $("teacherFormDialog").close(); reloadTeacherPanel(); }
  });

  /* 学生列表工具栏：重置选中学生的密码 */
  on("stuResetPwdBtn", () => {
    const s = selectedStudent();
    if (s) openResetPwd(s.id);
  });

  /* 审核学生修改申请 */
  const STATUS_CN = { pending: "待审核", approved: "已批准", rejected: "已拒绝" };

  on("requestBtn", async () => {
    $("requestDialog").showModal();
    await reloadRequests();
  });

  async function reloadRequests() {
    const res = await api("/requests");
    if (res.code !== 200) { alert(res.msg); return; }
    $("reqBody").innerHTML = res.data.length
      ? res.data.map(r =>
        `<tr><td>${r.req_id}</td><td>${esc(r.student_id)}</td><td>${esc(r.student_name)}</td>` +
        `<td>${esc(r.field_label)}</td><td>${esc(r.old_value)}</td><td>${esc(r.new_value)}</td>` +
        `<td><span class="badge ${esc(r.status)}">${STATUS_CN[r.status] || esc(r.status)}</span></td>` +
        `<td>${esc(r.time)}</td>` +
        `<td>${r.status === "pending"
          ? `<button class="btn student" style="padding:3px 10px" data-ok="${r.req_id}">批准</button> ` +
            `<button class="btn danger" style="padding:3px 10px" data-no="${r.req_id}">拒绝</button>`
          : "—"}</td></tr>`).join("")
      : '<tr><td colspan="9"><div class="empty-hint">暂无修改申请</div></td></tr>';

    $("reqBody").querySelectorAll("[data-ok]").forEach(btn =>
      btn.onclick = () => handleReq(btn.dataset.ok, true));
    $("reqBody").querySelectorAll("[data-no]").forEach(btn =>
      btn.onclick = () => handleReq(btn.dataset.no, false));
  }

  async function handleReq(reqId, approve) {
    const res = await api("/requests/" + reqId + "/handle",
      { method: "POST", body: JSON.stringify({ approve }) });
    alert(res.msg);
    reloadRequests();
  }
}

load();
