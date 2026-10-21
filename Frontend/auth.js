// Shared by login.html and signup.html (signup has a "confirm-password" field).
const isSignup = !!document.getElementById("confirm-password");

// The "Sign Up" / "Login" link at the bottom of the card
function toggleForm() {
  window.location.href = isSignup ? "login.html" : "signup.html";
}

const form = document.getElementById("auth-form");
const submitBtn = form.querySelector("button[type=submit]");

// Message line shown above the submit button
const msg = document.createElement("p");
msg.style.cssText = "font-size:14px;margin:8px 0;min-height:18px;color:#dc2626;";
submitBtn.before(msg);

function showMessage(text, ok) {
  msg.style.color = ok ? "#16a34a" : "#dc2626";
  msg.innerText = text;
}

form.addEventListener("submit", async function (e) {
  e.preventDefault();
  showMessage("");

  const payload = {
    username: document.getElementById("username").value.trim(),
    password: document.getElementById("password").value,
    role: document.getElementById("role").value
  };

  if (isSignup) {
    payload.email = document.getElementById("email").value.trim();
    if (payload.password !== document.getElementById("confirm-password").value) {
      showMessage("Passwords do not match");
      return;
    }
  }

  submitBtn.disabled = true;
  try {
    const res = await fetch(isSignup ? "/signup" : "/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    const data = await res.json().catch(() => ({}));

    if (!res.ok) {
      showMessage(data.message || "Something went wrong");
      return;
    }

    window.location.href =
      data.role === "recruiter" ? "recruiter.html" : "applicant_dashboard.html";
  } catch (err) {
    showMessage("Could not reach the server. Open http://127.0.0.1:5000");
  } finally {
    submitBtn.disabled = false;
  }
});