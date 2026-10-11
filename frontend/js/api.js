(function () {
  const API_BASE_URL = "http://127.0.0.1:8000";

  async function postJson(path, body) {
    const response = await fetch(`${API_BASE_URL}${path}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });

    if (!response.ok) {
      throw new Error(`Request to ${path} failed with HTTP ${response.status}`);
    }

    return response.json();
  }

  async function getJson(path) {
    const response = await fetch(`${API_BASE_URL}${path}`);
    if (!response.ok) {
      throw new Error(`Request to ${path} failed with HTTP ${response.status}`);
    }
    return response.json();
  }

  window.PyqApi = {
    API_BASE_URL,
    postJson,
    getJson,
  };
})();
