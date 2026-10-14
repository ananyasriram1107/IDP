document.addEventListener("DOMContentLoaded", () => {
  window.PyqAuth.initProtectedPage();
  initTabs();
  initPaperUpload();
  initMaterialUpload();
  loadPapers();
  loadMaterials();
});

function initTabs() {
  const tabs = document.querySelectorAll(".tab-button");
  const papersPanel = document.getElementById("papersPanel");
  const materialsPanel = document.getElementById("materialsPanel");

  tabs.forEach((tab) => {
    tab.addEventListener("click", () => {
      tabs.forEach((t) => t.classList.toggle("active", t === tab));
      const isPapers = tab.dataset.tab === "papers";
      papersPanel.hidden = !isPapers;
      materialsPanel.hidden = isPapers;
    });
  });
}

function formatDate(isoString) {
  try {
    return new Date(isoString).toLocaleDateString(undefined, { year: "numeric", month: "short", day: "numeric" });
  } catch (err) {
    return isoString;
  }
}

async function uploadFile(path, fileInput, statusEl, onDone) {
  const file = fileInput.files[0];
  if (!file) return;

  const formData = new FormData();
  formData.append("file", file);
  statusEl.textContent = "Uploading and processing...";
  statusEl.classList.remove("visible-error");

  try {
    const response = await fetch(`${window.PyqApi.API_BASE_URL}${path}`, {
      method: "POST",
      body: formData,
    });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const doc = await response.json();
    statusEl.textContent = `Processed "${doc.original_filename}".`;
    fileInput.value = "";
    await onDone();
  } catch (err) {
    statusEl.textContent = `Upload failed: ${err.message}`;
    statusEl.classList.add("visible-error");
  }
}

function initPaperUpload() {
  const form = document.getElementById("paperUploadForm");
  form.addEventListener("submit", (event) => {
    event.preventDefault();
    uploadFile(
      "/pdf/upload",
      document.getElementById("paperUploadFile"),
      document.getElementById("paperUploadStatus"),
      loadPapers
    );
  });
}

function initMaterialUpload() {
  const form = document.getElementById("materialUploadForm");
  form.addEventListener("submit", (event) => {
    event.preventDefault();
    uploadFile(
      "/materials/upload",
      document.getElementById("materialUploadFile"),
      document.getElementById("materialUploadStatus"),
      loadMaterials
    );
  });
}

async function loadPapers() {
  const grid = document.getElementById("papersGrid");
  try {
    const papers = await window.PyqApi.getJson("/pdf");
    grid.innerHTML = "";
    if (papers.length === 0) {
      grid.innerHTML = '<p style="color:var(--text-muted);font-size:13px;">No PYQ papers uploaded yet.</p>';
      return;
    }
    papers.forEach((paper) => {
      const card = document.createElement("a");
      card.className = "card material-card";
      card.href = `pyq-explorer.html?pdf_id=${encodeURIComponent(paper.id)}`;
      card.innerHTML = `
        <p class="material-card-title">${paper.original_filename}</p>
        <p class="material-card-meta">${paper.page_count} pages &middot; ${paper.question_count} questions &middot; ${formatDate(paper.uploaded_at)}</p>
      `;
      grid.appendChild(card);
    });
  } catch (err) {
    grid.innerHTML = `<p style="color:var(--error);font-size:13px;">Could not load PYQ papers: ${err.message}</p>`;
  }
}

async function loadMaterials() {
  const grid = document.getElementById("materialsGrid");
  try {
    const materials = await window.PyqApi.getJson("/materials");
    grid.innerHTML = "";
    if (materials.length === 0) {
      grid.innerHTML = '<p style="color:var(--text-muted);font-size:13px;">No study materials uploaded yet.</p>';
      return;
    }
    materials.forEach((material) => {
      const card = document.createElement("div");
      card.className = "card material-card";
      card.innerHTML = `
        <p class="material-card-title">${material.original_filename}</p>
        <p class="material-card-meta">${material.page_count} pages &middot; ${formatDate(material.uploaded_at)}</p>
      `;
      card.addEventListener("click", () => openMaterialViewer(material));
      grid.appendChild(card);
    });
  } catch (err) {
    grid.innerHTML = `<p style="color:var(--error);font-size:13px;">Could not load study materials: ${err.message}</p>`;
  }
}

async function openMaterialViewer(material) {
  const viewer = document.getElementById("materialViewer");
  const title = document.getElementById("materialViewerTitle");
  const content = document.getElementById("materialViewerContent");

  title.textContent = `Extracted content -- ${material.original_filename}`;
  content.innerHTML = "<p style=\"color:var(--text-muted);font-size:13px;\">Loading...</p>";
  viewer.hidden = false;
  viewer.scrollIntoView({ behavior: "smooth", block: "nearest" });

  try {
    const chunks = await window.PyqApi.getJson(`/materials/${material.id}/content`);
    content.innerHTML = "";
    if (chunks.length === 0) {
      content.innerHTML = '<p style="color:var(--text-muted);font-size:13px;">No text could be extracted from this file.</p>';
      return;
    }
    chunks.forEach((chunk) => {
      const item = document.createElement("div");
      item.className = "chunk-item";
      item.innerHTML = `
        <p class="chunk-item-page">Page ${chunk.page}</p>
        <p class="chunk-item-text"></p>
      `;
      item.querySelector(".chunk-item-text").textContent = chunk.text;
      content.appendChild(item);
    });
  } catch (err) {
    content.innerHTML = `<p style="color:var(--error);font-size:13px;">Could not load content: ${err.message}</p>`;
  }
}

document.addEventListener("DOMContentLoaded", () => {
  document.getElementById("materialViewerClose").addEventListener("click", () => {
    document.getElementById("materialViewer").hidden = true;
  });
});
