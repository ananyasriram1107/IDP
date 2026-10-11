(function () {
  document.addEventListener("DOMContentLoaded", () => {
    // If already "logged in", skip straight to the dashboard.
    if (window.PyqAuth.getUserName()) {
      window.location.href = window.PyqAuth.dashboardUrl();
      return;
    }

    const tabs = document.querySelectorAll(".auth-tab");
    const submitButton = document.getElementById("authSubmit");
    const subtitle = document.getElementById("authSubtitle");
    const form = document.getElementById("authForm");
    const nameInput = document.getElementById("authName");
    const passwordInput = document.getElementById("authPassword");
    const errorEl = document.getElementById("authError");

    const copy = {
      login: { submit: "Log in", subtitle: "Log in to continue your JEE prep." },
      signup: { submit: "Sign up", subtitle: "Create an account to get started." },
    };

    function setMode(mode) {
      tabs.forEach((tab) => tab.classList.toggle("active", tab.dataset.mode === mode));
      submitButton.textContent = copy[mode].submit;
      subtitle.textContent = copy[mode].subtitle;
      form.dataset.mode = mode;
      errorEl.classList.remove("visible");
    }

    tabs.forEach((tab) => {
      tab.addEventListener("click", () => setMode(tab.dataset.mode));
    });

    form.addEventListener("submit", (event) => {
      event.preventDefault();
      const name = nameInput.value.trim();
      const password = passwordInput.value;

      if (!name || !password) {
        errorEl.textContent = "Please enter both a name and a password.";
        errorEl.classList.add("visible");
        return;
      }

      // Prototype only: no backend auth call, no password check/storage.
      // We just remember the display name for the session.
      window.PyqAuth.setUserName(name);
      window.location.href = window.PyqAuth.dashboardUrl();
    });

    setMode("login");
  });
})();
