// Used by index.html (checkLogin) and recruiter.html (findCandidates, logout)

// Upload Resume on home page
async function checkLogin() {
  try {
    const res = await fetch("/api/me");
    if (res.ok) {
      const user = await res.json();
      window.location.href =
        user.role === "recruiter" ? "recruiter.html" : "applicant_dashboard.html";
      return;
    }
  } catch (err) {
    // server not reachable: fall through to the login page
  }
  alert("Please login first!");
  window.location.href = "login.html";
}

async function logout() {
  try { await fetch("/logout", { method: "POST" }); } catch (err) {}
  window.location.href = "index.html";
}

function candidateCard(c) {
  const card = document.createElement("div");
  card.className = "candidate-card";

  const add = (tag, text, cls) => {
    const el = document.createElement(tag);
    el.textContent = text;       // textContent: resume data can't inject HTML
    if (cls) el.className = cls;
    card.appendChild(el);
  };

  add("h3", c.name || "Candidate");
  add("span", "Score " + c.score + "%", "badge");
  add("p", "Experience: " + c.experience + (c.experience === 1 ? " year" : " years"));
  add("p", "Skills: " + (c.skills.length ? c.skills.join(", ") : "none detected"));
  if (c.matched && c.matched.length) add("p", "Matched: " + c.matched.join(", "), "matched");
  add("p", "Email: " + (c.email || "not found"));
  add("p", "Phone: " + (c.phone || "not found"));
  return card;
}

async function findCandidates(e) {
  if (e) e.preventDefault();

  const msg = document.getElementById("search-msg");
  const box = document.getElementById("candidates");
  msg.textContent = "";
  box.replaceChildren();

  const params = new URLSearchParams({
    skills: document.getElementById("skills").value,
    experience: document.getElementById("experience").value || "0"
  });

  try {
    const res = await fetch("/api/candidates?" + params);
    if (res.status === 401 || res.status === 403) {
      window.location.href = "login.html";
      return;
    }
    const data = await res.json();
    if (!data.candidates.length) {
      msg.textContent = "No candidates found.";
      return;
    }
    msg.textContent = data.candidates.length + " candidate(s) found";
    data.candidates.forEach((c) => box.appendChild(candidateCard(c)));
  } catch (err) {
    msg.textContent = "Could not reach the server. Is app.py running?";
  }
}