const user = getUser();
if (!user || user.role !== "student") { location.replace("/"); throw new Error("no auth"); }

document.getElementById("welcome").textContent = `欢迎，${user.name}（${user.id}）`;
document.getElementById("whoami").textContent = `当前登录：${user.name}（${user.id}） · 学生`;

async function load() {
  const res = await api("/me");
  if (res.code !== 200) { alert(res.msg); return; }
  const s = res.data;

  document.getElementById("iId").textContent = s.id;
  document.getElementById("iName").textContent = s.name;
  document.getElementById("iGender").textContent = s.gender;
  document.getElementById("iClass").textContent = s.class_name;
  document.getElementById("iPhone").textContent = s.phone;

  const entries = Object.entries(s.grades);
  document.getElementById("gradeBody").innerHTML = entries.length
    ? entries.map(([sub, v]) => `<tr><td>${esc(sub)}</td><td>${esc(v)}</td></tr>`).join("")
    : '<tr><td colspan="2">（暂无成绩）</td></tr>';
  document.getElementById("summary").textContent = entries.length
    ? `总分：${s.total}　　平均分：${(s.total / entries.length).toFixed(1)}`
    : "";
}

load();

const $ = id => document.getElementById(id);

/* ---------- 申请修改信息 ---------- */
const STATUS_CN = { pending: "待审核", approved: "已批准", rejected: "已拒绝" };

$("requestBtn").onclick = async () => {
  const res = await api("/editable-fields");
  if (res.code !== 200) { alert(res.msg); return; }
  const fields = res.data;
  $("reqField").innerHTML = Object.entries(fields)
    .map(([k, label]) => `<option value="${esc(k)}">${esc(label)}</option>`).join("");
  $("reqValue").value = "";
  $("reqDialog").showModal();
};
$("cancelReqBtn").onclick = () => $("reqDialog").close();
$("submitReqBtn").onclick = async () => {
  const body = { field: $("reqField").value, new_value: $("reqValue").value.trim() };
  if (!body.new_value) { alert("请填写新的内容"); return; }
  const res = await api("/requests", { method: "POST", body: JSON.stringify(body) });
  alert(res.msg);
  if (res.code === 200) { $("reqDialog").close(); load(); }
};

/* ---------- 我的申请记录 ---------- */
$("myReqBtn").onclick = async () => {
  $("myReqDialog").showModal();
  const res = await api("/requests");
  if (res.code !== 200) { alert(res.msg); return; }
  $("myReqBody").innerHTML = res.data.length
    ? res.data.map(r =>
        `<tr><td>${r.req_id}</td><td>${esc(r.field_label)}</td>` +
        `<td>${esc(r.old_value)}</td><td>${esc(r.new_value)}</td>` +
        `<td><span class="badge ${esc(r.status)}">${STATUS_CN[r.status] || esc(r.status)}</span></td>` +
        `<td>${esc(r.time)}</td></tr>`).join("")
    : '<tr><td colspan="6"><div class="empty-hint">暂无申请记录</div></td></tr>';
};

/* ---------- 修改密码 ---------- */
$("myPwdBtn").onclick = () => {
  $("oldPwd").value = $("newPwd").value = $("newPwd2").value = "";
  $("myPwdDialog").showModal();
};
$("cancelMyPwdBtn").onclick = () => $("myPwdDialog").close();
$("saveMyPwdBtn").onclick = async () => {
  const oldPwd = $("oldPwd").value, newPwd = $("newPwd").value;
  if (!oldPwd || !newPwd) { alert("请填写完整"); return; }
  if (newPwd !== $("newPwd2").value) { alert("两次输入的新密码不一致"); return; }
  const res = await api("/me/password",
    { method: "PUT", body: JSON.stringify({ old_password: oldPwd, new_password: newPwd }) });
  alert(res.msg);
  if (res.code === 200) $("myPwdDialog").close();
};
