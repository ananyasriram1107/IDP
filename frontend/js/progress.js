document.addEventListener("DOMContentLoaded", async () => {
  window.PyqAuth.initProtectedPage();
  const userName = window.PyqAuth.getUserName();

  const [summaryResult, trendsResult, topicsResult] = await Promise.allSettled([
    window.PyqApi.getJson(`/progress/${encodeURIComponent(userName)}`),
    window.PyqApi.getJson("/exam/trends"),
    window.PyqApi.getJson("/exam/important-topics?limit=5"),
  ]);

  renderReadiness(summaryResult);
  renderCorpusCard(trendsResult, topicsResult);
});

function renderReadiness(summaryResult) {
  const content = document.getElementById("readinessContent");
  const xpBadge = document.getElementById("xpBadge");

  if (summaryResult.status !== "fulfilled") {
    content.innerHTML = `<p style="color:var(--error);font-size:13px;">Could not load your progress: ${summaryResult.reason.message}</p>`;
    return;
  }

  const summary = summaryResult.value;
  xpBadge.innerHTML = `${summary.total_xp}<span class="xp-badge-unit">XP</span>`;

  if (summary.total_attempted === 0) {
    content.innerHTML = `
      <p style="color:var(--text-muted);font-size:13px;margin-bottom:14px;">
        You haven't attempted any questions yet.
      </p>
      <a class="btn btn-primary" href="learn.html">Go to Learn</a>
    `;
    return;
  }

  const overallPct = Math.round(summary.accuracy * 100);
  let html = `
    <ul class="progress-list">
      <li class="progress-row">
        <div class="progress-row-top"><span>Overall accuracy</span><span>${overallPct}%</span></div>
        <div class="progress-bar-track"><div class="progress-bar-fill" style="width:${overallPct}%"></div></div>
      </li>
  `;
  summary.by_subject.slice(0, 4).forEach((s) => {
    const pct = Math.round(s.accuracy * 100);
    html += `
      <li class="progress-row">
        <div class="progress-row-top"><span>${s.subject}</span><span>${pct}%</span></div>
        <div class="progress-bar-track"><div class="progress-bar-fill" style="width:${pct}%"></div></div>
      </li>
    `;
  });
  html += "</ul>";

  if (summary.unlocked_checkpoints.length > 0) {
    html += `<div style="margin-top:16px;">${summary.unlocked_checkpoints
      .map((c) => `<span class="checkpoint-badge">&#10003; ${c}</span>`)
      .join("")}</div>`;
  }

  if (summary.recent_activity.length > 0) {
    html += '<ul class="recent-list" style="margin-top:18px;">';
    summary.recent_activity.slice(0, 6).forEach((activity) => {
      const icon = activity.is_correct === true ? "&#10003;" : activity.is_correct === false ? "&#10007;" : "&#9679;";
      html += `
        <li class="recent-item">
          <span>
            <p class="recent-item-title">${icon} ${activity.activity_type}${activity.topic ? ` -- ${activity.topic}` : ""}</p>
            <p class="recent-item-meta">${new Date(activity.recorded_at).toLocaleString()}</p>
          </span>
        </li>
      `;
    });
    html += "</ul>";
  }

  content.innerHTML = html;
}

function renderCorpusCard(trendsResult, topicsResult) {
  const summaryEl = document.getElementById("corpusSummary");
  const listEl = document.getElementById("hotTopicsList");

  if (trendsResult.status === "fulfilled") {
    const t = trendsResult.value;
    const yearRange = t.min_year && t.max_year ? `${t.min_year}-${t.max_year}` : "unknown years";
    summaryEl.textContent = `${t.total_questions} questions across ${yearRange}.`;
  } else {
    summaryEl.textContent = "Could not load exam trends.";
  }

  if (topicsResult.status === "fulfilled") {
    listEl.innerHTML = topicsResult.value
      .map(
        (topic) =>
          `<li class="trend-row" title="${topic.reason}"><span>${topic.topic}</span><span class="trend-row-count">${topic.total_count}</span></li>`
      )
      .join("");
  } else {
    listEl.innerHTML = '<li class="trend-row">Could not load important topics.</li>';
  }
}
