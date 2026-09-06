/* One accessible motion preference for every ambient video on a page. */
(() => {
  "use strict";
  const videos = [...document.querySelectorAll("video")];
  if (!videos.length) return;
  const motionPreference = window.matchMedia(
    "(prefers-reduced-motion: reduce)",
  );
  let userPaused = motionPreference.matches;
  let interacted = false;
  const visible = new WeakMap();
  const manuallyPaused = new WeakSet();
  const automaticPauses = new WeakSet();
  const control = document.createElement("button");
  control.type = "button";
  control.className = "motion-control";
  document.body.append(control);
  function updateLabel() {
    const paused =
      userPaused || videos.every((video) => manuallyPaused.has(video));
    control.textContent = paused ? "Play motion" : "Pause motion";
    control.dataset.paused = String(paused);
    control.setAttribute(
      "aria-label",
      paused ? "Play background animations" : "Pause background animations",
    );
  }
  function updateVideo(video) {
    if (
      userPaused ||
      manuallyPaused.has(video) ||
      document.hidden ||
      visible.get(video) === false
    ) {
      if (!video.paused) {
        automaticPauses.add(video);
        video.pause();
      }
    } else
      video.play().catch((error) => {
        if (error.name === "NotAllowedError") {
          userPaused = true;
          updateAll();
        }
      });
  }
  function updateAll() {
    videos.forEach(updateVideo);
    updateLabel();
  }
  for (const video of videos) {
    video.muted = true;
    video.playsInline = true;
    video.preload = "metadata";
    const rect = video.getBoundingClientRect();
    visible.set(video, rect.bottom > 0 && rect.top < window.innerHeight);
    video.addEventListener("pause", () => {
      if (automaticPauses.has(video)) automaticPauses.delete(video);
      else if (!video.ended) manuallyPaused.add(video);
      updateLabel();
    });
    video.addEventListener("play", () => {
      manuallyPaused.delete(video);
      if (userPaused) {
        interacted = true;
        userPaused = false;
      }
      updateLabel();
    });
  }
  if ("IntersectionObserver" in window) {
    const observer = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          visible.set(entry.target, entry.isIntersecting);
          updateVideo(entry.target);
        }
      },
      { threshold: 0.03 },
    );
    videos.forEach((video) => observer.observe(video));
  }
  control.addEventListener("click", () => {
    interacted = true;
    userPaused = control.dataset.paused !== "true";
    if (!userPaused) videos.forEach((video) => manuallyPaused.delete(video));
    updateAll();
  });
  document.addEventListener("visibilitychange", updateAll);
  motionPreference.addEventListener("change", (event) => {
    if (!interacted) {
      userPaused = event.matches;
      updateAll();
    }
  });
  updateAll();
})();
