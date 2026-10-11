/**
 * Shared session handling for the PYQ Parser frontend prototype.
 *
 * This is intentionally NOT real authentication -- there is no backend
 * auth endpoint. It only stores a display name in localStorage so the
 * dashboard UI can be demoed as if a user were logged in.
 */
(function () {
  const STORAGE_KEY = "pyq_user_name";

  function isInPagesDir() {
    return window.location.pathname.includes("/pages/");
  }

  function loginUrl() {
    return isInPagesDir() ? "../index.html" : "index.html";
  }

  function dashboardUrl() {
    return isInPagesDir() ? "dashboard.html" : "pages/dashboard.html";
  }

  function getUserName() {
    return window.localStorage.getItem(STORAGE_KEY);
  }

  function setUserName(name) {
    window.localStorage.setItem(STORAGE_KEY, name);
  }

  function logout() {
    window.localStorage.removeItem(STORAGE_KEY);
    window.location.href = loginUrl();
  }

  // Redirects to the login page if no user is stored. Call this at the
  // top of every protected page before rendering page content.
  function requireAuth() {
    const name = getUserName();
    if (!name) {
      window.location.href = loginUrl();
      return null;
    }
    return name;
  }

  function applyUserName(name) {
    document.querySelectorAll("[data-user-name]").forEach((el) => {
      el.textContent = name;
    });
    document.querySelectorAll("[data-user-initials]").forEach((el) => {
      el.textContent = initials(name);
    });
    document.querySelectorAll("[data-user-greeting-name]").forEach((el) => {
      el.textContent = name;
    });
  }

  function initials(name) {
    const parts = name.trim().split(/\s+/).filter(Boolean);
    if (parts.length === 0) return "?";
    if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
    return (parts[0][0] + parts[1][0]).toUpperCase();
  }

  function highlightActiveNav() {
    const currentPage = document.body.getAttribute("data-page");
    if (!currentPage) return;
    document.querySelectorAll("[data-nav-page]").forEach((link) => {
      link.classList.toggle("active", link.getAttribute("data-nav-page") === currentPage);
    });
  }

  function wireLogoutControls() {
    document.querySelectorAll("[data-logout]").forEach((el) => {
      el.addEventListener("click", (event) => {
        event.preventDefault();
        logout();
      });
    });
  }

  // Standard setup for any page inside pages/: enforce login, fill in
  // the user's name, highlight the active sidebar link, wire logout.
  function initProtectedPage() {
    const name = requireAuth();
    if (!name) return;
    applyUserName(name);
    highlightActiveNav();
    wireLogoutControls();
  }

  window.PyqAuth = {
    STORAGE_KEY,
    getUserName,
    setUserName,
    logout,
    requireAuth,
    applyUserName,
    initProtectedPage,
    dashboardUrl,
    loginUrl,
  };
})();
