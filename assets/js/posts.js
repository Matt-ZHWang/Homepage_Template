(() => {
  "use strict";

  const menu = document.querySelector(".collection-menu");
  menu?.querySelectorAll("a").forEach((link) => {
    link.addEventListener("click", () => {
      menu.open = false;
    });
  });
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && menu?.open) {
      menu.open = false;
      menu.querySelector("summary").focus();
    }
  });

  const viewer = document.querySelector(".photo-viewer");
  if (!viewer || typeof viewer.showModal !== "function") return;
  const image = viewer.querySelector(".viewer-image");
  const caption = viewer.querySelector(".viewer-caption");
  const original = viewer.querySelector(".viewer-original");
  let photos = [];
  let index = 0;
  let albumName = "";
  let opener;

  function showPhoto() {
    const current = photos[index];
    image.src = current.href;
    image.alt = current.querySelector("img").alt;
    original.href = current.href;
    caption.textContent = `${albumName} / ${index + 1} of ${photos.length}`;
  }
  function step(direction) {
    index = (index + direction + photos.length) % photos.length;
    showPhoto();
  }
  document.querySelectorAll(".photo-grid a").forEach((link) => {
    link.addEventListener("click", (event) => {
      if (event.metaKey || event.ctrlKey || event.shiftKey || event.altKey)
        return;
      event.preventDefault();
      opener = link;
      photos = Array.from(link.closest(".photo-grid").querySelectorAll("a"));
      index = photos.indexOf(link);
      albumName = link.closest(".album").querySelector("h3").textContent;
      showPhoto();
      viewer.showModal();
      document.body.classList.add("viewer-open");
    });
  });
  viewer
    .querySelector(".viewer-close")
    .addEventListener("click", () => viewer.close());
  viewer
    .querySelector(".viewer-prev")
    .addEventListener("click", () => step(-1));
  viewer.querySelector(".viewer-next").addEventListener("click", () => step(1));
  viewer.addEventListener("keydown", (event) => {
    if (event.key === "ArrowLeft" || event.key === "ArrowRight") {
      event.preventDefault();
      step(event.key === "ArrowLeft" ? -1 : 1);
    }
  });
  viewer.addEventListener("close", () => {
    document.body.classList.remove("viewer-open");
    image.removeAttribute("src");
    opener?.focus({ preventScroll: true });
  });
})();
