/* Shared navigation and accessible media behavior for research pages. */
document.querySelectorAll("a[href]").forEach((link) => {
  const href = link.getAttribute("href") || "";
  if (!/^https?:\/\//i.test(href)) return;
  const url = new URL(href, window.location.href);
  if (url.origin === window.location.origin) return;
  link.target = "_blank";
  link.rel = "noopener noreferrer";
});

const projectMenu = document.querySelector(".project-menu");
document.addEventListener("click", (event) => {
  if (projectMenu && !projectMenu.contains(event.target))
    projectMenu.open = false;
});
document.addEventListener("keydown", (event) => {
  if (event.key === "Escape" && projectMenu?.open) {
    projectMenu.open = false;
    projectMenu.querySelector("summary").focus();
  }
});
