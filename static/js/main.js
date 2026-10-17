// main.js — students will add JavaScript here as features are built

document.addEventListener("DOMContentLoaded", () => {
    document.querySelectorAll(".password-toggle").forEach((button) => {
        button.addEventListener("click", () => {
            const input = document.getElementById(button.dataset.target);
            if (!input) return;
            const isHidden = input.type === "password";
            input.type = isHidden ? "text" : "password";
            button.setAttribute("aria-label", isHidden ? "Hide password" : "Show password");
            button.textContent = isHidden ? "🙈" : "👁";
        });
    });

    const navToggle = document.querySelector(".nav-toggle");
    const navMenu = document.getElementById("main-nav");

    if (!navToggle || !navMenu) return;

    const closeNav = (restoreFocus = false) => {
        navToggle.setAttribute("aria-expanded", "false");
        navToggle.classList.remove("is-open");
        navMenu.classList.remove("is-open");
        if (restoreFocus) navToggle.focus();
    };

    const toggleNav = () => {
        const isOpen = navToggle.getAttribute("aria-expanded") === "true";
        navToggle.setAttribute("aria-expanded", String(!isOpen));
        navToggle.classList.toggle("is-open", !isOpen);
        navMenu.classList.toggle("is-open", !isOpen);
    };

    navToggle.addEventListener("click", toggleNav);

    navMenu.addEventListener("click", (event) => {
        if (event.target.closest("a")) closeNav();
    });

    document.addEventListener("click", (event) => {
        if (!event.target.closest(".nav-inner")) closeNav();
    });

    document.addEventListener("keydown", (event) => {
        if (event.key === "Escape" && navToggle.getAttribute("aria-expanded") === "true") {
            closeNav(true);
        }
    });

    window.addEventListener("resize", () => {
        if (window.innerWidth >= 900) closeNav();
    });
});
