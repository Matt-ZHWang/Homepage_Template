/**
 * Background connections, adapted from canvas-nest.js v1.0.1.
 * Copyright (c) 2016 hustcc
 * Source: https://github.com/hustcc/canvas-nest.js
 * License: MIT
 *
 * Permission is hereby granted, free of charge, to any person obtaining a copy
 * of this software and associated documentation files (the "Software"), to deal
 * in the Software without restriction, including without limitation the rights
 * to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
 * copies of the Software, and to permit persons to whom the Software is
 * furnished to do so, subject to the following conditions:
 * The above copyright notice and this permission notice shall be included in
 * all copies or substantial portions of the Software.
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
 * IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
 * FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
 * AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
 * LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
 * OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
 * THE SOFTWARE.
 */
(() => {
  "use strict";
  if (document.querySelector("canvas.background-lines")) return;

  const canvas = document.createElement("canvas");
  canvas.className = "background-lines";
  canvas.setAttribute("aria-hidden", "true");
  const context = canvas.getContext("2d");
  if (!context) return;
  document.body.prepend(canvas);

  const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)");
  const hoverPointer = window.matchMedia(
    "(any-hover: hover) and (any-pointer: fine)",
  );
  const control = document.createElement("button");
  control.type = "button";
  control.className = "motion-control lines-control";
  document.body.append(control);

  const particles = [];
  const pointer = { x: null, y: null };
  let width = 0;
  let height = 0;
  let frame = null;
  let lastTime = null;
  // null means the device/accessibility preference still governs playback.
  let explicitPlaying = null;

  function isPlaying() {
    return explicitPlaying ?? (!reducedMotion.matches && hoverPointer.matches);
  }

  function updateControl() {
    const paused = !isPlaying();
    control.textContent = paused ? "Play lines" : "Pause lines";
    control.dataset.paused = String(paused);
    control.setAttribute(
      "aria-label",
      paused ? "Play background lines" : "Pause background lines",
    );
  }

  function clearPointer() {
    pointer.x = null;
    pointer.y = null;
  }

  function drawLine(x1, y1, x2, y2, strength, mouseLink = false) {
    context.beginPath();
    context.lineWidth = mouseLink
      ? 0.35 + strength * 0.45
      : 0.15 + strength * 0.4;
    context.strokeStyle = `rgba(255,255,255,${Math.min(1, strength + 0.2)})`;
    context.moveTo(x1, y1);
    context.lineTo(x2, y2);
    context.stroke();
  }

  function render() {
    context.clearRect(0, 0, width, height);
    context.fillStyle = "rgba(255,255,255,0.8)";
    const linkDistanceSquared = 110 * 110;
    const pointerDistanceSquared = 210 * 210;
    particles.forEach((particle, index) => {
      context.fillRect(particle.x - 0.5, particle.y - 0.5, 1, 1);
      for (let next = index + 1; next < particles.length; next += 1) {
        const other = particles[next];
        const distanceSquared =
          (particle.x - other.x) ** 2 + (particle.y - other.y) ** 2;
        if (distanceSquared < linkDistanceSquared) {
          drawLine(
            particle.x,
            particle.y,
            other.x,
            other.y,
            1 - distanceSquared / linkDistanceSquared,
          );
        }
      }
      if (pointer.x !== null && pointer.y !== null) {
        const distanceSquared =
          (particle.x - pointer.x) ** 2 + (particle.y - pointer.y) ** 2;
        if (distanceSquared < pointerDistanceSquared) {
          drawLine(
            particle.x,
            particle.y,
            pointer.x,
            pointer.y,
            1 - distanceSquared / pointerDistanceSquared,
            true,
          );
        }
      }
    });
  }

  function update(delta) {
    const pull = 1 - Math.exp(-2.4 * delta);
    for (const particle of particles) {
      particle.x += particle.vx * delta;
      particle.y += particle.vy * delta;
      if (pointer.x !== null && pointer.y !== null) {
        const dx = pointer.x - particle.x;
        const dy = pointer.y - particle.y;
        const distanceSquared = dx * dx + dy * dy;
        // Like canvas-nest, gather nearby points into a loose halo around the
        // cursor rather than accelerating them permanently or collapsing them.
        if (distanceSquared < 210 * 210 && distanceSquared > 42 * 42) {
          particle.x += dx * pull;
          particle.y += dy * pull;
        }
      }
      if (particle.x < 0 || particle.x > width) {
        particle.vx *= -1;
        particle.x = Math.max(0, Math.min(width, particle.x));
      }
      if (particle.y < 0 || particle.y > height) {
        particle.vy *= -1;
        particle.y = Math.max(0, Math.min(height, particle.y));
      }
    }
  }

  function tick(timestamp) {
    frame = null;
    if (document.hidden || !isPlaying()) {
      lastTime = null;
      return;
    }
    const delta =
      lastTime === null ? 0 : Math.min((timestamp - lastTime) / 1000, 0.05);
    lastTime = timestamp;
    update(delta);
    render();
    frame = requestAnimationFrame(tick);
  }

  function syncPlayback() {
    if (frame !== null) cancelAnimationFrame(frame);
    frame = null;
    lastTime = null;
    updateControl();
    if (!document.hidden && isPlaying()) frame = requestAnimationFrame(tick);
  }

  function resize() {
    const previousWidth = width || 1;
    const previousHeight = height || 1;
    width = Math.max(1, window.innerWidth);
    height = Math.max(1, window.innerHeight);
    const ratio = Math.min(window.devicePixelRatio || 1, 2);
    canvas.width = Math.round(width * ratio);
    canvas.height = Math.round(height * ratio);
    canvas.style.width = `${width}px`;
    canvas.style.height = `${height}px`;
    context.setTransform(ratio, 0, 0, ratio, 0, 0);
    for (const particle of particles) {
      particle.x = (particle.x / previousWidth) * width;
      particle.y = (particle.y / previousHeight) * height;
    }
    const count = width >= 760 ? 120 : 64;
    particles.length = Math.min(particles.length, count);
    while (particles.length < count) {
      particles.push({
        x: Math.random() * width,
        y: Math.random() * height,
        vx: (Math.random() * 2 - 1) * 42,
        vy: (Math.random() * 2 - 1) * 42,
      });
    }
    clearPointer();
    render();
  }

  window.addEventListener(
    "pointermove",
    (event) => {
      if (!isPlaying() || document.hidden || event.pointerType === "touch")
        return;
      pointer.x = event.clientX;
      pointer.y = event.clientY;
    },
    { passive: true },
  );
  window.addEventListener(
    "pointerout",
    (event) => {
      if (!event.relatedTarget) clearPointer();
    },
    { passive: true },
  );
  window.addEventListener("blur", clearPointer);
  window.addEventListener("resize", resize, { passive: true });
  document.addEventListener("visibilitychange", () => {
    clearPointer();
    syncPlayback();
  });
  for (const preference of [reducedMotion, hoverPointer]) {
    preference.addEventListener("change", () => {
      clearPointer();
      syncPlayback();
    });
  }
  control.addEventListener("click", () => {
    explicitPlaying = !isPlaying();
    clearPointer();
    syncPlayback();
    render();
  });

  resize();
  syncPlayback();
})();
