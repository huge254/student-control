// 前端公共工具：请求封装 / 登录态 / HTML 转义
const TOKEN_KEY = "sms_token";
const USER_KEY = "sms_user";

async function api(path, options = {}) {
  const headers = { ...(options.headers || {}) };
  if (options.body) headers["Content-Type"] = "application/json";
  const token = localStorage.getItem(TOKEN_KEY);
  if (token) headers["Authorization"] = "Bearer " + token;

  let resp;
  try {
    resp = await fetch("/api" + path, { ...options, headers });
  } catch (e) {
    alert("无法连接后端服务，请确认已运行 python -m uvicorn main:app");
    throw e;
  }
  const body = await resp.json().catch(() => ({ code: resp.status, msg: "响应格式错误", data: null }));

  // 登录过期统一跳回登录页
  if (resp.status === 401 && !path.startsWith("/login")) {
    alert(body.msg || "登录已过期，请重新登录");
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(USER_KEY);
    location.href = "/";
    throw new Error("unauthorized");
  }
  return body; // {code, msg, data}
}

function getUser() {
  try { return JSON.parse(localStorage.getItem(USER_KEY) || "null"); }
  catch { return null; }
}

function logout() {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(USER_KEY);
  location.href = "/";
}

// 渲染用户数据前必须转义，防止 XSS
function esc(s) {
  return String(s ?? "").replace(/[&<>"']/g,
    c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}

// 全局弹窗控制：Esc 或点击 ×/关闭 按钮，关闭最上层弹窗
function closeTopDialog() {
  const opened = [...document.querySelectorAll("dialog")].filter(d => d.open);
  if (opened.length) opened[opened.length - 1].close();
}
document.addEventListener("keydown", e => {
  if (e.key === "Escape") closeTopDialog();
});
document.addEventListener("click", e => {
  if (e.target.closest("[data-close]")) closeTopDialog();
});
