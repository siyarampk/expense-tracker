# Comprehensive Technical Specification: Mobile Responsive UI Pass

## 1. Overview & Objectives
This specification provides a complete, detailed plan for converting Spendly's user interface into a fully responsive, mobile-first-friendly web application down to a minimum target width of **360px**. 

Currently, responsive styles are fragmented (`style.css` and `profile.css` have partial 900px/600px breakpoints, while `add_expense.css` and `analytics.css` have none). This initiative addresses layout overflow, navigation accessibility, button visibility (specifically login/signup buttons and actionable elements), touch-target optimization, and data presentation (tables and charts) without adding backend routes, changing business logic, or introducing third-party frameworks.

---

## 2. Dependencies & Prerequisites
- **Upstream Specs Completed:** `02-registration`, `03-login-logout`, `04-profile-page`, `05-backend-routes-profile`, `06-date-filter-profile`, `07-add-expense`, `08-edit-expense`.
- **Target Browser Viewports:** 
  - Mobile Small: 360px × 640px
  - Mobile Medium/Large: 480px × 800px
  - Tablet: 768px × 1024px
  - Desktop: 900px+

---

## 3. Structural & Component Specs

### 3.1 Navigation Bar & Header (`base.html`, `style.css`, `main.js`)
* **Problem:** On smaller viewports, navigation links and authentication action buttons (Login / Sign Up / Logout) wrap awkwardly, overlap with the brand logo, or spill out of the horizontal container.
* **Requirements:**
  1. **Header Layout:**
     - Header strictly maintains a single line at top (`height: 60px` or `min-height: 60px`) with space-between alignment for logo and hamburger toggle.
     - Brand logo/wordmark remains visible on the left.
  2. **Hamburger Toggle Button:**
     - Rendered inside `<nav>` in `templates/base.html`.
     - Button attributes: `type="button"`, `class="nav-toggle"`, `aria-label="Toggle navigation menu"`, `aria-expanded="false"`, `aria-controls="nav-menu"`.
     - Touch/Click area: Minimum `44px x 44px`.
     - Visible only on screen widths **< 900px**. Hidden on screens `≥ 900px`.
     - Keypress support: Operable via `Space` and `Enter` keys.
  3. **Mobile Nav Drawer / Collapsible Menu:**
     - Target container (`#nav-menu` or `.nav-links`).
     - Below **900px**, switches from inline horizontal flex to a top-down vertical overlay or expandable stack.
     - Complete nav items included: Navigation links (Dashboard, Analytics, Add Expense), User info/avatar, and **Auth Action Buttons** (Login, Sign Up, Logout).
     - When opened (`.is-open` or `aria-expanded="true"`):
       - Slide-down or fade-in transition.
       - Buttons (e.g., "Sign In" / "Sign Up") adapt to **full-width** buttons inside the expanded menu with standard padding and clear outline/fill styling.
     - When closed: hidden via `display: none` or vertical clip/transform to avoid blocking touch events on page content.

### 3.2 Landing & Auth Pages (`landing.html`, `auth.html` / `login.html`, `register.html`)
* **Requirements:**
  1. **Hero Section:** Hero text, subheadings, and primary Call To Action (CTA) buttons stack vertically below 768px.
  2. **Auth Forms:**
     - Form container width: `100%` with max-width `420px` centered.
     - Side margin padding: Minimum `16px` on left and right to prevent touching screen edges.
     - Input fields and primary action buttons span `100%` width.

### 3.3 Dashboard & Profile (`profile.html`, `dashboard.html`, `profile.css`)
* **Requirements:**
  1. **Stat Cards:**
     - Dynamic grid switching from 3–4 columns to 2 columns (<768px) and 1 full-width column (<480px).
  2. **Category Progress Bars & Summary Charts:**
     - Text labels and percentage values wrap neatly without clipping text.
  3. **Transactions List/Table:**
     - Below **600px**, table converts either to a responsive scrollable container (`overflow-x: auto` with smooth scrolling) OR stacks as individual transaction cards.
     - Table columns prioritize crucial info: Date, Category/Merchant, Amount. Secondary details collapse or hide if necessary.

### 3.4 Add & Edit Expense (`add_expense.html`, `edit_expense.html`, `add_expense.css`)
* **Requirements:**
  1. **Form Fields:** Stack single-column below 640px.
  2. **Inputs & Dropdowns:** `min-height: 44px`, `font-size: 16px` (prevents auto-zoom behavior on iOS Safari).
  3. **Action Buttons:** Save/Cancel buttons stack vertically on screens `< 480px` with full width.

### 3.5 Analytics Page (`analytics.html`, `analytics.css`)
* **Requirements:**
  1. **Grid Layout:** Chart grid containers collapse to single-column layout below 900px.
  2. **Chart Containers:** Dynamic width (`100%`), fixed aspect ratio or max-height to prevent vertical distortion.

---

## 4. File-by-File Changes Matrix

| File Path | Changes to Implement |
| :--- | :--- |
| `templates/base.html` | Add `<button class="nav-toggle" aria-expanded="false" aria-controls="main-nav">` with animated line spans or SVG icon. Wrap links & auth buttons inside `#main-nav`. |
| `static/js/main.js` | Add event listener for `.nav-toggle` to toggle `aria-expanded` and active class on `#main-nav`. Close menu on `Escape` key press or clicking outside. |
| `static/css/style.css` | Define CSS variables for spacing/breakpoints. Add hamburger menu styles (`@media (max-width: 899px)`). Force interactive tap targets to min `40px`-`44px`. Fix global container padding (`padding: 0 16px`). |
| `static/css/profile.css` | Add `@media (max-width: 768px)` and `@media (max-width: 600px)` for stat card stacking and transaction table horizontal scrolling/card styling. |
| `static/css/add_expense.css` | Add `@media (max-width: 640px)` breakpoint for full-width stacked inputs and bottom action button spacing. |
| `static/css/analytics.css` | Add `@media (max-width: 900px)` breakpoint to stack chart containers vertically and handle chart legend wrapping. |

---

## 5. Technical Rules & Constraints
1. **Zero External Libraries:** Pure CSS and vanilla ES6 JavaScript only. No Bootstrap, Tailwind, or jQuery.
2. **CSS Variables Only:** Colors, spacing, and typography must reference existing CSS variables (e.g., `var(--primary-color)`). No hardcoded hex values.
3. **No Database or Route Changes:** Presentational edits only.
4. **Preserve Desktop Design:** Visual structure for viewports `≥ 900px` must remain intact.
5. **iOS Zoom Fix:** All inputs, selects, and textareas must have a minimum `font-size` of `16px` on mobile viewports to prevent unwanted browser auto-zooming.

---

## 6. Definition of Done (Verification Checklist)

- [ ] **No Horizontal Overflow:** Zero horizontal scrollbars across all pages at 360px, 480px, and 768px viewports.
- [ ] **Navbar & Auth Buttons:** Navbar collapses under 900px. Hamburger opens/closes menu smoothly. Login, Sign Up, and Logout buttons are easily accessible and properly formatted within the mobile nav.
- [ ] **Accessibility:** Hamburger toggle has accurate `aria-expanded` attribute state changes and is operable via keyboard (`Tab`, `Space`, `Enter`).
- [ ] **Touch Targets:** All links, buttons, and form inputs meet the minimum ~40px–44px tap target size.
- [ ] **Form Usability:** Add/Edit Expense forms can be filled and submitted on a 360px viewport without horizontal scrolling or text clipping.
- [ ] **Table Data Accessibility:** Transactions on dashboard/profile can be read without breaking layout boundaries.
```

I have completed the detailed specification document covering all mobile responsive UI requirements, including navigation toggle mechanics, button visibility, form stacking, and table adaptation. Let me know if you would like me to adjust any specific breakpoints or styles!