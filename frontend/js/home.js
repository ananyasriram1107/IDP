document.addEventListener("DOMContentLoaded", () => {
  window.PyqAuth.initProtectedPage();
  const userName = window.PyqAuth.getUserName();

  const viewport = document.getElementById("mapViewport");
  const canvas = document.getElementById("mapCanvas");
  const image = document.getElementById("mapImage");
  const avatar = document.getElementById("mapAvatar");
  const checkpointsLayer = document.getElementById("mapCheckpoints");

  const zoneTargets = {
    materials: "materials.html",
    learn: "learn.html",
    explorer: "pyq-explorer.html",
    progress: "progress.html",
  };

  const panZoom = initPanZoom(viewport, canvas);
  initImageSizing(image, canvas, panZoom);
  initHotspots(avatar, zoneTargets);
  loadBadgesAndCheckpoints(userName, checkpointsLayer);
});

/** Reads the real artwork's natural size once loaded so the canvas's
 * aspect ratio (and therefore every percentage-positioned hotspot)
 * stays accurate at any viewport width, then fits it edge-to-edge in
 * the full-bleed viewport (like object-fit: cover). There is no
 * interactive zoom -- this is purely responsive sizing. */
function initImageSizing(image, canvas, panZoom) {
  function applySizing() {
    if (!image.naturalWidth || !image.naturalHeight) return;
    canvas.style.aspectRatio = `${image.naturalWidth} / ${image.naturalHeight}`;
    requestAnimationFrame(() => panZoom.fitToViewport(image.naturalWidth / image.naturalHeight));
  }

  if (image.complete && image.naturalWidth) {
    applySizing();
  }

  image.addEventListener("load", applySizing);

  image.addEventListener("error", () => {
    console.error(`Learning World map artwork failed to load: ${image.src}`);
  });

  // Coalesce rapid-fire resize events (e.g. a dragged window edge) into
  // one recalculation per animation frame, so refitting stays smooth.
  let resizeScheduled = false;
  window.addEventListener("resize", () => {
    if (!image.naturalWidth || resizeScheduled) return;
    resizeScheduled = true;
    requestAnimationFrame(() => {
      resizeScheduled = false;
      panZoom.fitToViewport(image.naturalWidth / image.naturalHeight);
    });
  });
}

function initPanZoom(viewport, canvas) {
  let scale = 1;
  let x = 0;
  let y = 0;
  let isPanning = false;
  let lastX = 0;
  let lastY = 0;
  let currentAspectRatio = null;

  // Not a meaningful zoom limit (there's no interactive zoom) -- just a
  // sanity ceiling. Must stay generous: a tall narrow viewport against
  // this wide image can genuinely need 3-4x+ scale to fully cover, and
  // under-covering would expose blank space, which is the one thing
  // this implementation must never do.
  const MAX_SCALE = 8;
  // Rendered deliberately larger than strict "cover" fit so the canvas
  // overflows the viewport on BOTH axes, not just whichever axis the
  // image's aspect ratio happens to overflow naturally. Without this,
  // an axis that exactly matched the viewport at cover-scale would have
  // zero real overflow -- exactly the "pans into empty space" bug.
  const PAN_MARGIN = 1.3;

  function apply() {
    canvas.style.transform = `translate(${x}px, ${y}px) scale(${scale})`;
  }

  /** Clamps panning to the map's *actual* rendered overflow -- never
   * further. `.map-canvas` has `transform-origin: 0 0` and sits at the
   * viewport's own top-left before any transform, so the valid range
   * per axis is asymmetric: x/y of 0 means "canvas's own top-left
   * edge," which already touches the viewport's top-left edge with
   * zero slack -- 0 is therefore the *maximum* (any more positive
   * exposes blank space top/left). The *minimum* is however far
   * negative shifts the canvas until its far edge exactly reaches the
   * viewport's far edge: `viewportSize - renderedSize` (negative,
   * since renderedSize > viewportSize). The valid range is
   * [viewportSize - renderedSize, 0] -- NOT a symmetric [-n, n]. */
  function clamp() {
    const rect = viewport.getBoundingClientRect();
    if (!currentAspectRatio || !rect.width || !rect.height) {
      x = 0;
      y = 0;
      return;
    }

    const renderedWidth = rect.width * scale;
    const renderedHeight = (rect.width / currentAspectRatio) * scale;

    const minX = Math.min(0, rect.width - renderedWidth);
    const minY = Math.min(0, rect.height - renderedHeight);

    x = Math.max(minX, Math.min(0, x));
    y = Math.max(minY, Math.min(0, y));
  }

  viewport.addEventListener("pointerdown", (event) => {
    isPanning = true;
    viewport.classList.add("is-panning");
    lastX = event.clientX;
    lastY = event.clientY;
    viewport.setPointerCapture(event.pointerId);
  });

  viewport.addEventListener("pointermove", (event) => {
    if (!isPanning) return;
    x += event.clientX - lastX;
    y += event.clientY - lastY;
    lastX = event.clientX;
    lastY = event.clientY;
    clamp();
    apply();
  });

  function endPan(event) {
    isPanning = false;
    viewport.classList.remove("is-panning");
    if (event && event.pointerId !== undefined) {
      try {
        viewport.releasePointerCapture(event.pointerId);
      } catch (err) {
        // pointer may already be released; safe to ignore
      }
    }
  }

  viewport.addEventListener("pointerup", endPan);
  viewport.addEventListener("pointercancel", endPan);

  /** Computes a scale so the canvas covers the viewport on both axes
   * with real margin to spare (see PAN_MARGIN), then re-clamps the
   * current pan position into the new bounds -- recalculated on load
   * and on every resize, per the requirement that pan limits track
   * viewport/zoom changes. The first call (initial load) centers the
   * view; later calls (resize) preserve the existing pan position
   * where the new bounds still allow it, only pulling it back in if
   * the window shrank enough to make it invalid. */
  function fitToViewport(imageAspectRatio) {
    const rect = viewport.getBoundingClientRect();
    if (!rect.width || !rect.height) return;

    const isFirstFit = currentAspectRatio === null;
    currentAspectRatio = imageAspectRatio;

    // Canvas is CSS-sized to width:100% (so renderedWidth == rect.width
    // at scale 1 always); only the height needs a ratio check to know
    // how much scale-up covers the viewport vertically too.
    const baselineHeight = rect.width / imageAspectRatio;
    const coverScale = Math.max(1, rect.height / baselineHeight);
    scale = Math.min(MAX_SCALE, coverScale * PAN_MARGIN);

    if (isFirstFit) {
      const renderedWidth = rect.width * scale;
      const renderedHeight = baselineHeight * scale;
      x = (rect.width - renderedWidth) / 2;
      y = (rect.height - renderedHeight) / 2;
    }

    clamp();
    apply();
  }

  return { fitToViewport };
}

/** Click a hotspot -> avatar glides to it -> navigate once the glide
 * finishes (or immediately if the user prefers reduced motion). */
function initHotspots(avatar, zoneTargets) {
  const prefersReducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  document.querySelectorAll(".map-hotspot").forEach((hotspot) => {
    hotspot.addEventListener("click", () => {
      const zone = hotspot.dataset.zone;
      const target = zoneTargets[zone];
      if (!target) return;

      const left = hotspot.style.left;
      const top = hotspot.style.top;

      if (prefersReducedMotion) {
        window.location.href = target;
        return;
      }

      avatar.style.left = left;
      avatar.style.top = top;

      const onDone = () => {
        avatar.removeEventListener("transitionend", onDone);
        window.location.href = target;
      };
      avatar.addEventListener("transitionend", onDone);
      // Safety net in case transitionend doesn't fire (e.g. no visible change).
      setTimeout(onDone, 700);
    });
  });
}

async function loadBadgesAndCheckpoints(userName, checkpointsLayer) {
  setBadge("materials", "...");
  setBadge("learn", "...");
  setBadge("explorer", "...");
  setBadge("progress", "...");

  const [trends, topics, materials, pdfs, summary] = await Promise.allSettled([
    window.PyqApi.getJson("/exam/trends"),
    window.PyqApi.getJson("/exam/important-topics?limit=3"),
    window.PyqApi.getJson("/materials"),
    window.PyqApi.getJson("/pdf"),
    window.PyqApi.getJson(`/progress/${encodeURIComponent(userName)}`),
  ]);

  if (trends.status === "fulfilled") {
    setBadge("explorer", `${trends.value.total_questions} Qs`);
  } else {
    setBadge("explorer", "--");
  }

  if (pdfs.status === "fulfilled" && materials.status === "fulfilled") {
    setBadge("materials", `${pdfs.value.length + materials.value.length} files`);
  } else {
    setBadge("materials", "--");
  }

  if (topics.status === "fulfilled" && topics.value.length > 0) {
    setBadge("learn", topics.value[0].topic);
  } else {
    setBadge("learn", "Explore");
  }

  if (summary.status === "fulfilled") {
    const s = summary.value;
    setBadge("progress", s.total_attempted > 0 ? `${Math.round(s.accuracy * 100)}%` : "Start");
    renderCheckpoints(checkpointsLayer, topics.status === "fulfilled" ? topics.value : [], s.unlocked_checkpoints);
  } else {
    setBadge("progress", "--");
    renderCheckpoints(checkpointsLayer, topics.status === "fulfilled" ? topics.value : [], []);
  }
}

function setBadge(zone, text) {
  const el = document.querySelector(`[data-badge-text="${zone}"]`);
  if (el) el.textContent = text;
}

/** Topic checkpoints: a small flag per important topic, scattered
 * through the garden area, filled in once "unlocked" (per My Progress). */
function renderCheckpoints(layer, topics, unlocked) {
  layer.innerHTML = "";
  const unlockedSet = new Set(unlocked || []);
  const basePositions = [
    { left: "11%", top: "58%" },
    { left: "22%", top: "78%" },
    { left: "33%", top: "60%" },
  ];

  topics.slice(0, 3).forEach((topic, index) => {
    const position = basePositions[index] || basePositions[0];
    const isUnlocked = unlockedSet.has(topic.topic);

    const el = document.createElement("div");
    el.className = `map-checkpoint${isUnlocked ? " is-unlocked" : ""}`;
    el.style.left = position.left;
    el.style.top = position.top;
    el.innerHTML = `
      <span class="map-checkpoint-marker">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M5 3v18"/><path d="M5 4h11l-2 4 2 4H5"/>
        </svg>
      </span>
      <span class="map-checkpoint-label">${topic.topic}</span>
    `;
    layer.appendChild(el);
  });
}
