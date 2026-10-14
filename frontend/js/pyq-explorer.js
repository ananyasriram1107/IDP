let currentResults = [];
const pdfIdFilter = new URLSearchParams(window.location.search).get("pdf_id");

document.addEventListener("DOMContentLoaded", async () => {
  window.PyqAuth.initProtectedPage();
  await populateFilterOptions();
  wireFilters();
  wireBackButton();
  await runSearch();
});

async function populateFilterOptions() {
  try {
    const trends = await window.PyqApi.getJson("/exam/trends");
    fillSelect(document.getElementById("explorerSubject"), trends.by_subject.map((s) => s.subject), "All subjects");
    fillSelect(document.getElementById("explorerTopic"), trends.by_topic.map((t) => t.topic), "All topics");
    fillSelect(
      document.getElementById("explorerYear"),
      trends.by_year.map((y) => String(y.year)),
      "All years"
    );
  } catch (err) {
    // Non-fatal -- filters just stay at their defaults.
  }
}

function fillSelect(selectEl, values, placeholder) {
  const unique = [...new Set(values)].filter(Boolean).sort();
  selectEl.innerHTML = `<option value="">${placeholder}</option>`;
  unique.forEach((value) => {
    const option = document.createElement("option");
    option.value = value;
    option.textContent = value;
    selectEl.appendChild(option);
  });
}

function wireFilters() {
  const debounceSearch = debounce(runSearch, 350);
  document.getElementById("explorerSearch").addEventListener("input", debounceSearch);
  ["explorerSubject", "explorerTopic", "explorerYear", "explorerDifficulty"].forEach((id) => {
    document.getElementById(id).addEventListener("change", runSearch);
  });
}

function debounce(fn, delay) {
  let timer = null;
  return (...args) => {
    clearTimeout(timer);
    timer = setTimeout(() => fn(...args), delay);
  };
}

async function runSearch() {
  const statusEl = document.getElementById("explorerStatus");
  const resultsEl = document.getElementById("explorerResults");

  const subject = document.getElementById("explorerSubject").value;
  const topic = document.getElementById("explorerTopic").value;
  const year = document.getElementById("explorerYear").value;
  const difficulty = document.getElementById("explorerDifficulty").value;
  const search = document.getElementById("explorerSearch").value.trim().toLowerCase();

  const params = new URLSearchParams();
  if (subject) params.set("subject", subject);
  if (topic) params.set("topic", topic);
  if (difficulty) params.set("difficulty", difficulty);
  if (year) params.set("year", year);

  statusEl.textContent = "Loading...";
  statusEl.classList.remove("visible-error");

  try {
    const query = params.toString();
    let results = await window.PyqApi.getJson(`/questions${query ? `?${query}` : ""}`);

    if (pdfIdFilter) {
      results = results.filter((q) => q.pdf_id === pdfIdFilter);
    }
    if (search) {
      results = results.filter((q) => q.text.toLowerCase().includes(search));
    }

    currentResults = results;
    statusEl.textContent = `${results.length} question(s) found.`;
    renderResults(results, resultsEl);
  } catch (err) {
    statusEl.textContent = `Could not load questions: ${err.message}`;
    statusEl.classList.add("visible-error");
  }
}

function renderResults(results, container) {
  container.innerHTML = "";
  if (results.length === 0) {
    container.innerHTML = '<p style="color:var(--text-muted);font-size:13px;">No questions match these filters.</p>';
    return;
  }

  results.forEach((question) => {
    const card = document.createElement("div");
    card.className = "card question-card";
    const dna = question.classification;
    const chips = [dna.subject, dna.topic, dna.difficulty].filter(Boolean);
    card.innerHTML = `
      <div>${chips.map((c) => `<span class="dna-chip">${c}</span>`).join("")}</div>
      <p class="question-card-snippet">${question.text.slice(0, 160)}${question.text.length > 160 ? "..." : ""}</p>
      <p class="material-card-meta">${question.source.file} &middot; page ${question.source.page} &middot; Q${question.source.question_number}</p>
    `;
    card.addEventListener("click", () => showDetail(question));
    container.appendChild(card);
  });
}

function wireBackButton() {
  document.getElementById("explorerBackButton").addEventListener("click", () => {
    document.getElementById("explorerDetail").hidden = true;
    document.getElementById("explorerList").hidden = false;
  });
}

async function showDetail(question) {
  document.getElementById("explorerList").hidden = true;
  document.getElementById("explorerDetail").hidden = false;

  const dna = question.classification;
  const chips = [dna.subject, dna.chapter, dna.topic, dna.difficulty, dna.question_type, dna.cognitive_level]
    .filter(Boolean)
    .concat(dna.subtopics || [], dna.concepts || []);
  document.getElementById("detailDnaChips").innerHTML = chips
    .map((c) => `<span class="dna-chip">${c}</span>`)
    .join("");
  document.getElementById("detailText").textContent = question.text;

  const src = question.source;
  document.getElementById("detailSource").textContent =
    `Source: ${src.file} -- page ${src.page}, question ${src.question_number}${src.section ? `, ${src.section}` : ""}`;

  const relatedList = document.getElementById("detailRelated");
  relatedList.innerHTML = '<li class="recent-item">Loading related questions...</li>';

  try {
    const related = await window.PyqApi.getJson(`/questions/${question.question_id}/related`);
    relatedList.innerHTML = "";
    if (related.length === 0) {
      relatedList.innerHTML = '<li class="recent-item">No related questions found.</li>';
      return;
    }
    related.forEach((rel) => {
      const li = document.createElement("li");
      li.className = "recent-item";
      const target = currentResults.find((q) => q.question_id === rel.question_id);
      li.innerHTML = `
        <span>
          <p class="recent-item-title">${rel.type} (${Math.round(rel.confidence * 100)}%)</p>
          <p class="recent-item-meta">${rel.reason}</p>
        </span>
      `;
      if (target) {
        li.style.cursor = "pointer";
        li.addEventListener("click", () => showDetail(target));
      }
      relatedList.appendChild(li);
    });
  } catch (err) {
    relatedList.innerHTML = `<li class="recent-item">Could not load related questions: ${err.message}</li>`;
  }
}
