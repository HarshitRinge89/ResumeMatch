const $ = (id) => document.getElementById(id);

function setMsg(text, isError) {
  const el = $("msg");
  el.innerText = text || "";
  el.className = "msg " + (isError ? "error" : "ok");
}

// Fill the result cards (innerText, so resume text can never inject HTML)
function render(p) {
  $("score").innerText = p.score + "%";
  $("skills").innerText = p.skills.length ? p.skills.join(", ") : "None detected";
  $("email").innerText = p.email || "Not found";
  $("phone").innerText = p.phone || "Not found";
  $("experience").innerText = p.experience + (p.experience === 1 ? " Year" : " Years");
}

// Show the previously analysed resume (if any) when the page opens
async function loadProfile() {
  try {
    const res = await fetch("/api/my-profile");
    if (res.status === 401 || res.status === 403) {
      window.location.href = "login.html";
      return;
    }
    const data = await res.json();
    if (data.profile) render(data.profile);
  } catch (err) {
    setMsg("Could not reach the server. Is app.py running?", true);
  }
}

$("resumeForm").addEventListener("submit", async function (e) {
  e.preventDefault();
  setMsg("");

  const btn = $("analyzeBtn");
  btn.disabled = true;
  setMsg("Analyzing...", false);

  try {
    const res = await fetch("/upload", { method: "POST", body: new FormData(this) });
    const data = await res.json().catch(() => ({}));

    if (res.status === 401 || res.status === 403) {
      window.location.href = "login.html";
      return;
    }
    if (!res.ok) {
      setMsg(data.message || "Upload failed", true);
      return;
    }
    render(data);
    setMsg("Resume analyzed!", false);
  } catch (err) {
    setMsg("Could not reach the server.", true);
  } finally {
    btn.disabled = false;
  }
});

async function logout() {
  try { await fetch("/logout", { method: "POST" }); } catch (err) {}
  window.location.href = "index.html";
}

loadProfile();