> Status update 2026-05-18: план исходного MVP выполнен и затем заменён Google Sheet-каталогом без админки и без объектных фото. Текущая схема описана в `README.md`.

# Real Estate Landing Catalog Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extend the existing static GitHub Pages MVP into a real-estate agency landing page with a demo mini-catalog.

**Architecture:** Keep the MVP dependency-free: one `index.html` file with embedded CSS/JS, plus a Python validation script. Demo listings are static HTML cards marked with `data-listing-card` so they can later be migrated into JSON/Google-Sheet-backed rendering.

**Tech Stack:** Static HTML/CSS/JS, Python stdlib validation, GitHub Pages root deployment.

---

### Task 1: Regression validation for mini-catalog

**Files:**
- Create: `tests/validate_site.py`
- Read: `index.html`

- [ ] Step 1: Write validation script that requires `#catalog`, at least 6 `data-listing-card` cards, WhatsApp/Instagram links, and demo disclaimer.
- [ ] Step 2: Run `python tests/validate_site.py` and confirm it fails before catalog implementation.

### Task 2: Implement mini-catalog in static HTML

**Files:**
- Modify: `index.html`
- Modify: `README.md`

- [ ] Step 1: Add nav link to `#catalog`.
- [ ] Step 2: Add catalog CSS for cards, badges, prices, metadata, and responsive layout.
- [ ] Step 3: Replace generic objects section with a mini-catalog section of 6 demo properties.
- [ ] Step 4: Add direct WhatsApp CTAs for each listing.
- [ ] Step 5: Update README with note that demo objects are temporary and can later be replaced/Google-Sheet-managed.

### Task 3: Verify GitHub Pages MVP

**Files:**
- Read: `index.html`, `README.md`, `.nojekyll`, `robots.txt`

- [ ] Step 1: Run `python tests/validate_site.py` and confirm PASS.
- [ ] Step 2: Run a static link check for required files and key URLs.
- [ ] Step 3: Report changed files and remaining next step: replace demo listings through Google Sheet.
