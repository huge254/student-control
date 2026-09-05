const msgEl = document.getElementById("loginMsg");

async function doLogin(role) {
  const username = document.getElementById("username").value.trim();
  const password = document.getElementById("password").value;
  msgEl.textContent = "";
  if (!username || !password) {
    msgEl.textContent = "请输入账号和密码！";
    return;
  }
  const res = await api("/login", {
    method: "POST",
    body: JSON.stringify({ username, password, role }),
  });
  if (res.code !== 200) {
    msgEl.textContent = res.msg;
    return;
  }
  localStorage.setItem(TOKEN_KEY, res.data.token);
  localStorage.setItem(USER_KEY, JSON.stringify(res.data.user));
  location.href = res.data.user.role === "student" ? "/student.html" : "/teacher.html";
}

document.getElementById("teacherLoginBtn").onclick = () => doLogin("teacher");
document.getElementById("studentLoginBtn").onclick = () => doLogin("student");
