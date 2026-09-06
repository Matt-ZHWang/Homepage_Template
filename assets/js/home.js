const hero = document.querySelector(".hero");
const stage = document.getElementById("home-stage");
const stageDragger = document.querySelector(".stage-dragger");
const stageStatus = document.querySelector(".stage-status");
const stageDragStatus = document.getElementById("stage-drag-status");
const stageProps = Array.from(document.querySelectorAll(".stage-prop"));
const dragClickThreshold = 6;
let activeDropProp = null;
let dragState = null;

function activateStageProp(prop) {
  stageProps.forEach((item) => {
    item.classList.toggle("is-lit", Boolean(prop) && item === prop);
  });
  if (hero && prop) {
    hero.style.setProperty("--spot-x", prop.dataset.x || "74%");
    hero.style.setProperty("--spot-y", prop.dataset.y || "34%");
  }
}

function setDragStatus(text, focused = false) {
  if (stageDragStatus) {
    stageDragStatus.textContent = text;
  }
  if (stageStatus) {
    stageStatus.classList.toggle("is-focused", focused);
    stageStatus.scrollTop = 0;
  }
}

function showRoomIntro(prop) {
  if (!prop) {
    setDragStatus("A small house, in an expanding universe.");
    return;
  }
  setDragStatus(
    prop.dataset.roomNote || prop.dataset.dropLabel || "room selected",
    true,
  );
}

function resetStageProp(prop, force = false) {
  if (prop.classList.contains("is-unlocked") && !force) {
    prop.classList.remove("is-cued", "is-lit");
    return;
  }
  const img = prop.querySelector("img");
  const label = prop.querySelector(".stage-label");
  if (img && prop.dataset.defaultSrc) {
    img.src = prop.dataset.defaultSrc;
  }
  if (label && prop.dataset.defaultLabel) {
    label.textContent = prop.dataset.defaultLabel;
  }
  prop.classList.remove("is-cued", "is-lit", "is-unlocked");
  prop.removeAttribute("aria-disabled");
}

function resetStagePreview() {
  stageProps.forEach((prop) => resetStageProp(prop));
  activeDropProp = null;
  activateStageProp(null);
  showRoomIntro(null);
}

function previewStageProp(prop) {
  stageProps.forEach((item) => {
    if (item !== prop) {
      resetStageProp(item);
    }
  });
  const img = prop.querySelector("img");
  if (img && prop.dataset.altSrc && !prop.classList.contains("is-unlocked")) {
    img.src = prop.dataset.altSrc;
  }
  prop.classList.add("is-cued");
  activeDropProp = prop;
  activateStageProp(prop);
  showRoomIntro(prop);
}

function unlockStageProp(prop) {
  stageProps.forEach((item) => {
    if (item !== prop) {
      resetStageProp(item);
    }
  });
  const img = prop.querySelector("img");
  const label = prop.querySelector(".stage-label");
  if (img && prop.dataset.altSrc) {
    img.src = prop.dataset.altSrc;
  }
  if (label && prop.dataset.dropLabel) {
    label.textContent = prop.dataset.dropLabel;
  }
  prop.classList.remove("is-cued", "is-lit");
  prop.classList.add("is-unlocked");
  prop.removeAttribute("aria-disabled");
  activeDropProp = null;
  activateStageProp(null);
  showRoomIntro(prop);
}

function cueDropProp(prop) {
  if (!prop) {
    resetStagePreview();
    return;
  }
  if (activeDropProp === prop) return;
  previewStageProp(prop);
}

function propAtPoint(clientX, clientY) {
  return (
    stageProps.find((prop) => {
      const rect = prop.getBoundingClientRect();
      return (
        clientX >= rect.left &&
        clientX <= rect.right &&
        clientY >= rect.top &&
        clientY <= rect.bottom
      );
    }) || null
  );
}

function propUnderDragger() {
  if (!stageDragger) return null;
  const rect = stageDragger.getBoundingClientRect();
  return propAtPoint(rect.left + rect.width / 2, rect.top + rect.height / 2);
}

function navigateToStageProp(prop) {
  const href = prop?.getAttribute("href");
  if (!href) return;
  window.location.href = href;
}

function exploreWorkingRooms() {
  const heading = document.querySelector("#projects .section-title");
  if (!heading) return;
  heading.tabIndex = -1;
  heading.focus({ preventScroll: true });
  document.getElementById("projects").scrollIntoView();
}

function moveDragger(event) {
  if (!dragState || !stage || !stageDragger) return;
  const moveX = event.clientX - dragState.startX;
  const moveY = event.clientY - dragState.startY;
  if (Math.hypot(moveX, moveY) > dragClickThreshold) {
    dragState.moved = true;
  }
  const stageRect = stage.getBoundingClientRect();
  const dragRect = stageDragger.getBoundingClientRect();
  const maxLeft = stageRect.width - dragRect.width - 8;
  const maxTop = stageRect.height - dragRect.height - 8;
  const left = Math.min(
    Math.max(event.clientX - stageRect.left - dragState.offsetX, 8),
    maxLeft,
  );
  const top = Math.min(
    Math.max(event.clientY - stageRect.top - dragState.offsetY, 8),
    maxTop,
  );
  stageDragger.style.left = `${left}px`;
  stageDragger.style.top = `${top}px`;
  stageDragger.style.right = "auto";
  stageDragger.style.bottom = "auto";

  const centerX = stageRect.left + left + dragRect.width / 2;
  const centerY = stageRect.top + top + dragRect.height / 2;
  cueDropProp(propAtPoint(centerX, centerY));
}

function stopDragging(event) {
  if (!dragState || !stageDragger) return;
  const droppedProp = activeDropProp;
  const isClick = !dragState.moved;
  const clickProp = dragState.startedUnlockedProp;
  stageDragger.classList.remove("is-dragging");
  if (stageDragger.hasPointerCapture?.(dragState.pointerId))
    stageDragger.releasePointerCapture(dragState.pointerId);
  stageDragger.removeEventListener("pointermove", moveDragger);
  stageDragger.removeEventListener("pointerup", stopDragging);
  stageDragger.removeEventListener("pointercancel", stopDragging);
  dragState = null;
  if (event.type === "pointercancel") {
    resetStagePreview();
  } else if (isClick && clickProp) {
    navigateToStageProp(clickProp);
  } else if (isClick) {
    exploreWorkingRooms();
  } else if (!isClick && droppedProp) {
    unlockStageProp(droppedProp);
  } else {
    resetStagePreview();
  }
}

function startDragging(event) {
  if (!stage || !stageDragger) return;
  if (event.button !== undefined && event.button !== 0) return;
  event.preventDefault();
  const stageRect = stage.getBoundingClientRect();
  const dragRect = stageDragger.getBoundingClientRect();
  const startingProp = propUnderDragger();
  dragState = {
    pointerId: event.pointerId,
    offsetX: event.clientX - dragRect.left,
    offsetY: event.clientY - dragRect.top,
    startX: event.clientX,
    startY: event.clientY,
    moved: false,
    startedUnlockedProp: startingProp?.classList.contains("is-unlocked")
      ? startingProp
      : null,
  };
  stageDragger.style.left = `${dragRect.left - stageRect.left}px`;
  stageDragger.style.top = `${dragRect.top - stageRect.top}px`;
  stageDragger.style.right = "auto";
  stageDragger.style.bottom = "auto";
  stageDragger.classList.add("is-dragging");
  stageDragger.setPointerCapture?.(event.pointerId);
  stageDragger.addEventListener("pointermove", moveDragger);
  stageDragger.addEventListener("pointerup", stopDragging);
  stageDragger.addEventListener("pointercancel", stopDragging);
  moveDragger(event);
}

stageProps.forEach((prop) => {
  const img = prop.querySelector("img");
  const label = prop.querySelector(".stage-label");
  if (img) {
    prop.dataset.defaultSrc = img.getAttribute("src") || "";
  }
  if (label) {
    prop.dataset.defaultLabel = label.textContent || "";
  }
  prop.removeAttribute("aria-disabled");
  prop.addEventListener("pointerenter", () => {
    if (!dragState) previewStageProp(prop);
  });
  prop.addEventListener("pointerleave", () => {
    if (!dragState) resetStagePreview();
  });
  prop.addEventListener("focus", () => previewStageProp(prop));
  prop.addEventListener("blur", () => {
    if (!dragState) resetStagePreview();
  });
});

if (stageDragger) {
  stageDragger.addEventListener("pointerdown", startDragging);
  stageDragger.addEventListener("click", (event) => {
    if (event.detail === 0) exploreWorkingRooms();
  });
}

document.querySelectorAll("a[href]").forEach((link) => {
  const href = link.getAttribute("href") || "";
  if (!/^https?:\/\//i.test(href)) return;
  const url = new URL(href, window.location.href);
  if (url.origin === window.location.origin) return;
  link.target = "_blank";
  link.rel = "noopener noreferrer";
});
document.getElementById("year").textContent = new Date().getFullYear();

const menuButton = document.querySelector(".menu-toggle");
const navLinks = document.querySelector(".nav-links");
document.documentElement.classList.add("navigation-ready");
function closeMenu() {
  menuButton?.setAttribute("aria-expanded", "false");
  navLinks?.classList.remove("is-open");
}
menuButton?.addEventListener("click", () => {
  const expanded = menuButton.getAttribute("aria-expanded") !== "true";
  menuButton.setAttribute("aria-expanded", String(expanded));
  navLinks.classList.toggle("is-open", expanded);
});
navLinks
  ?.querySelectorAll("a")
  .forEach((link) => link.addEventListener("click", closeMenu));
document.addEventListener("keydown", (event) => {
  if (event.key !== "Escape") return;
  if (menuButton?.getAttribute("aria-expanded") === "true") {
    closeMenu();
    menuButton.focus();
  }
  document.querySelectorAll(".nav-projects[open]").forEach((menu) => {
    menu.open = false;
    menu.querySelector("summary").focus();
  });
});
document.addEventListener("click", (event) => {
  document.querySelectorAll(".nav-projects[open]").forEach((menu) => {
    if (!menu.contains(event.target)) menu.open = false;
  });
});
