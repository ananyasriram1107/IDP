document.addEventListener("DOMContentLoaded", () => {
  window.PyqAuth.initProtectedPage();

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

      answerText.textContent = result.answer;
      answerSection.hidden = false;

      sourcesList.innerHTML = "";
      if (result.sources && result.sources.length > 0) {
        result.sources.forEach((source) => {
          const li = document.createElement("li");
          li.className = "recent-item";
          li.textContent = `${source.file} -- page ${source.page}, Q${source.question_number}`;
          sourcesList.appendChild(li);
        });
        sourcesSection.hidden = false;
      }

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
});
