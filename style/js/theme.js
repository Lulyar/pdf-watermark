// Script ini di-load dengan atribut `defer`, jadi DOM sudah siap saat kode dieksekusi
const STORAGE_KEY = "watermark-theme";

function applyTheme(theme) {
  const body = document.body;
  if (!body) return;
  body.classList.remove("theme-light", "theme-dark");
  body.classList.add(theme);
}

function getSystemTheme() {
  if (!window.matchMedia) return "theme-light";
  return window.matchMedia("(prefers-color-scheme: dark)").matches ? "theme-dark" : "theme-light";
}

function getInitialTheme() {
  const stored = localStorage.getItem(STORAGE_KEY);
  if (stored === "theme-light" || stored === "theme-dark") return stored;
  return getSystemTheme();
}

document.addEventListener("DOMContentLoaded", () => {
  // Set tema awal (ikut localStorage, kalau belum ada ikut mode sistem)
  applyTheme(getInitialTheme());

  const toggle = document.getElementById("theme-toggle");
  if (!toggle) return;

  toggle.addEventListener("click", () => {
    const body = document.body;
    const next = body.classList.contains("theme-dark") ? "theme-light" : "theme-dark";
    applyTheme(next);
    localStorage.setItem(STORAGE_KEY, next);
  });
});