let allQuestionsCache = null;

document.addEventListener("DOMContentLoaded", async () => {
  window.PyqAuth.initProtectedPage();
  initTabs();
  await populateFilterOptions();
  initTeachMe();
  initFlashcards();
  initQuiz();
  initTutorPanel();
});

function initTabs() {
  const tabs = document.querySelectorAll(".tab-button");
  const panels = {
    teachme: document.getElementById("teachmePanel"),
    flashcards: document.getElementById("flashcardsPanel"),
    quiz: document.getElementById("quizPanel"),
    tutor: document.getElementById("tutorPanel"),
  };

  tabs.forEach((tab) => {
    tab.addEventListener("click", () => {
      tabs.forEach((t) => t.classList.toggle("active", t === tab));
      Object.entries(panels).forEach(([name, panel]) => {
        panel.hidden = name !== tab.dataset.tab;
      });
    });
  });
}

async function getAllQuestions() {
  if (!allQuestionsCache) {
    allQuestionsCache = await window.PyqApi.getJson("/questions");
  }
  return allQuestionsCache;
}

/** Populates the Teach Me topic select and the Flashcards/Quiz subject
 * and topic selects from real aggregate data (/exam/trends), not
 * guessed values. */
async function populateFilterOptions() {
  try {
    const trends = await window.PyqApi.getJson("/exam/trends");
    fillSelect(document.getElementById("teachMeTopic"), trends.by_topic.map((t) => t.topic), "Choose a topic...");
    fillSelect(document.getElementById("flashcardSubject"), trends.by_subject.map((s) => s.subject), "All subjects");
    fillSelect(document.getElementById("flashcardTopic"), trends.by_topic.map((t) => t.topic), "All topics");
    fillSelect(document.getElementById("quizSubject"), trends.by_subject.map((s) => s.subject), "All subjects");
    fillSelect(document.getElementById("quizTopic"), trends.by_topic.map((t) => t.topic), "All topics");
  } catch (err) {
    // Non-fatal -- the selects just stay at their default "All" option.
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

function dnaChipsHtml(classification) {
  const chips = [];
  if (classification.subject) chips.push(classification.subject);
  if (classification.topic) chips.push(classification.topic);
  if (classification.difficulty) chips.push(classification.difficulty);
  if (classification.concepts) {
    classification.concepts.slice(0, 3).forEach((c) => chips.push(c));
  }
  return chips.map((c) => `<span class="dna-chip">${c}</span>`).join("");
}

/* ---------------- Teach Me ---------------- */

function initTeachMe() {
  const form = document.getElementById("teachMeForm");
  const topicSelect = document.getElementById("teachMeTopic");
  const customInput = document.getElementById("teachMeCustomTopic");
  const submitButton = document.getElementById("teachMeSubmit");
  const statusEl = document.getElementById("teachMeStatus");
  const answerSection = document.getElementById("teachMeAnswer");
  const answerText = document.getElementById("teachMeAnswerText");
  const sourcesSection = document.getElementById("teachMeSourcesSection");
  const sourcesList = document.getElementById("teachMeSources");

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const topic = customInput.value.trim() || topicSelect.value;
    if (!topic) {
      statusEl.textContent = "Choose or type a topic first.";
      statusEl.classList.add("visible-error");
      return;
    }

    submitButton.disabled = true;
    submitButton.textContent = "Thinking...";
    statusEl.classList.remove("visible-error");
    statusEl.textContent = "Asking the tutor -- this can take a while on local Ollama.";
    answerSection.hidden = true;
    sourcesSection.hidden = true;

    const query = `Explain ${topic} using my uploaded study materials. If no relevant material is found, say so clearly instead of guessing.`;

    try {
      const result = await window.PyqApi.postJson("/intelligence/query", { query });
      renderAnswer(answerText, answerSection, sourcesList, sourcesSection, result);
      statusEl.textContent = result.grounded
        ? `Answered using ${result.tool_calls_made} tool call(s).`
        : "The tutor could not ground this explanation in retrieved evidence.";

      if (result.grounded) {
        await recordProgressEvent({ activity_type: "teach_me", subject: null, topic });
      }
    } catch (err) {
      statusEl.textContent = `Could not reach the tutor: ${err.message}`;
      statusEl.classList.add("visible-error");
    } finally {
      submitButton.disabled = false;
      submitButton.textContent = "Explain";
    }
  });
}

/* Shared by Teach Me and Ask a Tutor -- both hit the same endpoint and
 * render the same answer/sources shape. */
function renderAnswer(answerTextEl, answerSectionEl, sourcesListEl, sourcesSectionEl, result) {
  answerTextEl.textContent = result.answer;
  answerSectionEl.hidden = false;

  sourcesListEl.innerHTML = "";
  if (result.sources && result.sources.length > 0) {
    result.sources.forEach((source) => {
      const li = document.createElement("li");
      li.className = "recent-item";
      li.textContent = `${source.file} -- page ${source.page}, Q${source.question_number}`;
      sourcesListEl.appendChild(li);
    });
    sourcesSectionEl.hidden = false;
  }
}

/* ---------------- Flashcards ---------------- */

function initFlashcards() {
  const loadButton = document.getElementById("flashcardLoadButton");
  const card = document.getElementById("flashcardCard");
  const face = document.getElementById("flashcardFace");
  const hint = document.getElementById("flashcardHint");
  const controls = document.getElementById("flashcardControls");
  const positionEl = document.getElementById("flashcardPosition");

  let deck = [];
  let index = 0;
  let showingBack = false;

  function render() {
    if (deck.length === 0) {
      card.hidden = true;
      controls.hidden = true;
      return;
    }
    card.hidden = false;
    controls.hidden = false;
    const question = deck[index];
    face.innerHTML = showingBack
      ? dnaChipsHtml(question.classification) || "<em>No Question DNA recorded for this question.</em>"
      : question.text;
    hint.textContent = showingBack ? "Click to see the question again" : "Click the card to reveal concepts";
    positionEl.textContent = `Card ${index + 1} of ${deck.length}`;
  }

  card.addEventListener("click", async () => {
    showingBack = !showingBack;
    render();
    if (showingBack && deck[index]) {
      const dna = deck[index].classification;
      await recordProgressEvent({ activity_type: "flashcard", subject: dna.subject, topic: dna.topic });
    }
  });

  document.getElementById("flashcardPrev").addEventListener("click", () => {
    if (deck.length === 0) return;
    index = (index - 1 + deck.length) % deck.length;
    showingBack = false;
    render();
  });

  document.getElementById("flashcardNext").addEventListener("click", () => {
    if (deck.length === 0) return;
    index = (index + 1) % deck.length;
    showingBack = false;
    render();
  });

  loadButton.addEventListener("click", async () => {
    const subject = document.getElementById("flashcardSubject").value;
    const topic = document.getElementById("flashcardTopic").value;

    loadButton.disabled = true;
    loadButton.textContent = "Loading...";
    try {
      const questions = await getAllQuestions();
      deck = questions.filter(
        (q) =>
          (!subject || q.classification.subject === subject) &&
          (!topic || q.classification.topic === topic)
      );
      index = 0;
      showingBack = false;
      render();
      if (deck.length === 0) {
        hint.textContent = "No questions match these filters.";
      }
    } finally {
      loadButton.disabled = false;
      loadButton.textContent = "Load flashcards";
    }
  });
}

/* ---------------- Quiz ---------------- */

function initQuiz() {
  const setupSection = document.getElementById("quizSetup");
  const runningSection = document.getElementById("quizRunning");
  const resultsSection = document.getElementById("quizResults");
  const startButton = document.getElementById("quizStartButton");
  const setupStatus = document.getElementById("quizSetupStatus");
  const progressLabel = document.getElementById("quizProgressLabel");
  const scoreLabel = document.getElementById("quizRunningScore");
  const dnaChipsEl = document.getElementById("quizDnaChips");
  const questionTextEl = document.getElementById("quizQuestionText");
  const feedbackEl = document.getElementById("quizFeedback");
  const finalScoreEl = document.getElementById("quizFinalScore");

  let quizQuestions = [];
  let quizIndex = 0;
  let correctCount = 0;

  function shuffle(array) {
    const copy = [...array];
    for (let i = copy.length - 1; i > 0; i--) {
      const j = Math.floor(Math.random() * (i + 1));
      [copy[i], copy[j]] = [copy[j], copy[i]];
    }
    return copy;
  }

  function showQuestion() {
    const question = quizQuestions[quizIndex];
    progressLabel.textContent = `Question ${quizIndex + 1} of ${quizQuestions.length}`;
    scoreLabel.textContent = `Score: ${correctCount}`;
    dnaChipsEl.innerHTML = dnaChipsHtml(question.classification);
    questionTextEl.textContent = question.text;
    feedbackEl.textContent = "";
    feedbackEl.className = "quiz-feedback";
  }

  async function answer(isCorrect) {
    const question = quizQuestions[quizIndex];
    if (isCorrect) correctCount += 1;
    feedbackEl.textContent = isCorrect ? "Marked correct." : "Marked incorrect -- review this topic later.";
    feedbackEl.className = `quiz-feedback ${isCorrect ? "is-correct" : "is-incorrect"}`;

    await recordProgressEvent({
      activity_type: "quiz",
      question_id: question.question_id,
      is_correct: isCorrect,
    });

    setTimeout(() => {
      quizIndex += 1;
      if (quizIndex >= quizQuestions.length) {
        finishQuiz();
      } else {
        showQuestion();
      }
    }, 500);
  }

  function finishQuiz() {
    runningSection.hidden = true;
    resultsSection.hidden = false;
    const pct = Math.round((correctCount / quizQuestions.length) * 100);
    finalScoreEl.textContent = `${correctCount}/${quizQuestions.length} -- ${pct}%`;
  }

  document.getElementById("quizMarkCorrect").addEventListener("click", () => answer(true));
  document.getElementById("quizMarkIncorrect").addEventListener("click", () => answer(false));

  document.getElementById("quizRestartButton").addEventListener("click", () => {
    resultsSection.hidden = true;
    setupSection.hidden = false;
  });

  startButton.addEventListener("click", async () => {
    const subject = document.getElementById("quizSubject").value;
    const topic = document.getElementById("quizTopic").value;
    const difficulty = document.getElementById("quizDifficulty").value;
    const count = parseInt(document.getElementById("quizCount").value, 10);

    startButton.disabled = true;
    setupStatus.textContent = "Loading questions...";
    try {
      const questions = await getAllQuestions();
      const matching = questions.filter(
        (q) =>
          (!subject || q.classification.subject === subject) &&
          (!topic || q.classification.topic === topic) &&
          (!difficulty || q.classification.difficulty === difficulty)
      );

      if (matching.length === 0) {
        setupStatus.textContent = "No questions match these filters. Try widening them.";
        setupStatus.classList.add("visible-error");
        return;
      }

      quizQuestions = shuffle(matching).slice(0, count);
      quizIndex = 0;
      correctCount = 0;
      setupStatus.textContent = "";
      setupStatus.classList.remove("visible-error");
      setupSection.hidden = true;
      runningSection.hidden = false;
      showQuestion();
    } finally {
      startButton.disabled = false;
    }
  });
}

/* ---------------- Ask a Tutor (ported verbatim from the old intelligence.js) ---------------- */

function initTutorPanel() {
  const form = document.getElementById("intelligenceForm");
  const input = document.getElementById("intelligenceQuery");
  const submitButton = document.getElementById("intelligenceSubmit");
  const statusEl = document.getElementById("intelligenceStatus");
  const answerSection = document.getElementById("intelligenceAnswer");
  const answerText = document.getElementById("intelligenceAnswerText");
  const sourcesList = document.getElementById("intelligenceSources");
  const sourcesSection = document.getElementById("intelligenceSourcesSection");

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const query = input.value.trim();
    if (!query) return;

    submitButton.disabled = true;
    submitButton.textContent = "Thinking...";
    statusEl.textContent = "Querying the agent -- this can take a while on local Ollama.";
    statusEl.classList.remove("visible-error");
    answerSection.hidden = true;
    sourcesSection.hidden = true;

    try {
      const result = await window.PyqApi.postJson("/intelligence/query", { query });
      renderAnswer(answerText, answerSection, sourcesList, sourcesSection, result);
      statusEl.textContent = result.grounded
        ? `Answered using ${result.tool_calls_made} tool call(s).`
        : "The agent could not ground this answer in retrieved evidence.";
    } catch (error) {
      statusEl.textContent = `Could not reach the AI Intelligence service: ${error.message}`;
      statusEl.classList.add("visible-error");
    } finally {
      submitButton.disabled = false;
      submitButton.textContent = "Ask";
    }
  });
}

/* ---------------- Shared progress recording ---------------- */

async function recordProgressEvent(payload) {
  try {
    await window.PyqApi.postJson("/progress/events", {
      user_name: window.PyqAuth.getUserName(),
      ...payload,
    });
  } catch (err) {
    // Progress tracking is best-effort -- never block the learning flow on it.
  }
}
