# MiroFish UI/UX Review — End-to-End Findings

**Date:** 2026-04-03
**Scope:** Full frontend audit across all pages, components, and layouts
**Status:** ✅ Remediated (All 6 Phases Complete)

---

## Critical Issues

| # | Issue | Location | Impact |
|---|-------|----------|--------|
| 1 | **Modal missing `role="dialog"` and focus trap** | `components/ui/Modal.tsx:61-67` | Screen readers can't identify modal; focus escapes to background |
| 2 | **Silent API failures everywhere** — `console.error()` with no user feedback | Dashboard `:51`, Monitor `:123`, Chat `:131`, Playbooks `:31` | Users see empty/broken UI with no explanation |
| 3 | **AgentCard uses `<div onClick>` instead of `<button>`** | `components/simulation/AgentCard.tsx:39-49` | Not keyboard-navigable, invisible to screen readers |
| 4 | **No error boundaries on any page** | All pages | Single component crash takes down entire page |
| 5 | **API keys generated with `Math.random()`** | `app/api-keys/page.tsx:45` | Not cryptographically secure — security risk |

---

## High Priority — UX Degradation

| # | Issue | Location |
|---|-------|----------|
| 6 | **2-second polling interval** on dashboard + monitor (stacks to 4 concurrent polls) | `app/page.tsx:58`, `app/simulations/[id]/page.tsx:90` |
| 7 | **No empty states** on dashboard when `simulations.length === 0` | `app/page.tsx` |
| 8 | **Hardcoded Slate colors** instead of design tokens across AgentCard, SimulationFeed, Modal | `AgentCard.tsx`, `SimulationFeed.tsx`, `Modal.tsx` |
| 9 | **Loading states are bare text** ("Loading...") with no spinner on all 9 simulation sub-pages | All `app/simulations/[id]/*` pages |
| 10 | **Sidebar fixed at 256px** — leaves only 119px for content on iPhone SE (375px) | `components/Sidebar.tsx:91` |
| 11 | **No delete confirmation** on persona designer — permanent loss with one click | `app/personas/designer/page.tsx:423` |
| 12 | **Playbook "Use Template" link doesn't pre-select** the playbook in wizard | `app/playbooks/page.tsx:144-148` |
| 13 | **Chat has no message persistence** — conversation lost on reload | `app/simulations/[id]/chat/page.tsx` |
| 14 | **SimulationFeed missing `aria-live="polite"`** — new messages not announced to screen readers | `components/simulation/SimulationFeed.tsx:73-79` |
| 15 | **No pagination/sorting** on simulations table, reports list, API keys list | Dashboard, Reports, API Keys pages |

---

## Medium Priority — Polish & Consistency

| # | Issue | Location |
|---|-------|----------|
| 16 | **Inconsistent nav item padding** — `py-2.5` vs `py-2` across sidebar sections | `components/Sidebar.tsx:126,158,191` |
| 17 | **Header not sticky** — scrolls away on mobile, wastes re-scroll effort | `components/Header.tsx:60` |
| 18 | **Missing focus ring styling** on sidebar navigation links | `components/Sidebar.tsx:121-140` |
| 19 | **Native `<select>` dropdowns** in persona designer don't match design system | `app/personas/designer/page.tsx:198-225` |
| 20 | **Timestamps in ISO format** on fine-tuning page instead of relative ("2h ago") | `app/fine-tuning/page.tsx:303-306` |
| 21 | **No breadcrumbs** on any simulation sub-page — users lose navigation context | All `app/simulations/[id]/*` pages |
| 22 | **Negative margins (`-m-4 md:-m-6`)** on multiple pages risk mobile overflow | Monitor, Attribution, Voice, and others |
| 23 | **Network graph fixed at 1200px** — overflows on mobile with no scroll indicator | `app/simulations/[id]/network/page.tsx:209-220` |
| 24 | **ZOPA position bars** use overlapping elements that obscure meaning | `app/simulations/[id]/zopa/page.tsx:299-322` |
| 25 | **Wizard has no "Save Draft"** — navigating away loses all progress | `app/simulations/new/page.tsx` |
| 26 | **`alert()` used instead of toast notifications** in voice page | `app/simulations/[id]/voice/page.tsx:102,115,152` |
| 27 | **Button loading state not announced** to screen readers (`aria-busy` missing) | `components/ui/Button.tsx:50` |
| 28 | **Input error messages not associated** via `aria-describedby` | `components/ui/Input.tsx:47-49` |
| 29 | **No max-width constraint** on main content — stretches on ultra-wide monitors | `components/ClientLayout.tsx:15-23` |
| 30 | **Sidebar section headers** use `<div>` instead of semantic `<h3>` tags | `components/Sidebar.tsx:145-147` |

---

## Low Priority — Nice to Have

| # | Issue | Location |
|---|-------|----------|
| 31 | No localStorage persistence for simulation wizard draft state | `app/simulations/new/page.tsx` |
| 32 | No cost breakdown in wizard review step (just a single number) | `app/simulations/new/page.tsx:179-180` |
| 33 | No help/info tooltips explaining metrics (fairness scores, ZOPA, sensitivity) | Fairness, ZOPA, Sensitivity pages |
| 34 | No keyboard shortcuts documentation anywhere in the app | Global |
| 35 | Reports empty state says "View Simulations" — should say "Create Simulation" | `app/reports/page.tsx:94-104` |
| 36 | Fine-tuning page is entirely mock with no actual API integration | `app/fine-tuning/page.tsx:51-65` |
| 37 | Cross-simulation analytics toggle lacks accessible label and ARIA attributes | `app/analytics/cross-simulation/page.tsx:158-168` |
| 38 | Audit trail hash truncation (`substring(0,8)`) should use monospace font | `app/simulations/[id]/audit-trail/page.tsx:300-301` |
| 39 | Card hover `-translate-y-1` transition can feel janky on low-end devices | `components/ui/Card.tsx:34` |
| 40 | No collapsible legend on network graph page — legend is very long | `app/simulations/[id]/network/page.tsx:303-357` |

---

## Page-by-Page Detail

### Dashboard (`app/page.tsx`)

- **Polling:** 2-second interval is too aggressive — recommend 5-10 seconds
- **Empty state:** No UI for `simulations.length === 0` — users can't tell if data failed or none exist
- **Error handling:** Only `console.error()` at line 51 — users see nothing on failure
- **Table:** No sorting, filtering, or pagination on Recent Simulations (6 columns, no mobile optimization)
- **Progress bar:** Hardcoded width calc `(currentRound / totalRounds) * 100` shows misleading 100% for incomplete rounds
- **Scrollable table:** `overflow-x-auto` with no visual scroll indicator on mobile

### New Simulation Wizard (`app/simulations/new/page.tsx`)

- **Validation:** Only checks simulation name at parameter step — no comprehensive field validation
- **Checkboxes:** Browser-default styling, inconsistent with design system
- **Upload simulation:** Hardcoded 400ms intervals don't reflect real network conditions
- **Launch feedback:** Spinner appears but no status messages during `api.createSimulation()`
- **No draft persistence:** All wizard data lost on navigation away
- **Cost display:** Single number with no breakdown of what's included

### Simulation Monitor (`app/simulations/[id]/page.tsx`)

- **Dual polling:** 2-second polling + elapsed timer creates race conditions on pause/resume
- **Feature cards:** 8 navigation buttons linking to sub-pages with no validation they exist
- **Mobile:** Control buttons have small tap targets; agent sidebar truncated at `max-h-48` with no scroll indicator
- **Speed control:** Shows 4 speeds but no visual feedback for which is "normal"
- **No breadcrumbs:** Users don't know where they are in the hierarchy

### Chat (`app/simulations/[id]/chat/page.tsx`)

- **Parallel API calls:** Three calls with no individual error handling — one failure breaks all
- **No persistence:** Conversation lost on reload (no localStorage fallback)
- **No typing indicator:** When agent is responding, no visual feedback
- **Input shifting:** Dynamic placeholder text ("Message {agent}..." vs "Message all agents...") causes layout shift
- **Timestamps:** Tiny and hard to read

### Playbooks (`app/playbooks/page.tsx`)

- **Silent failure:** API error caught with no user feedback — empty library shown
- **Search:** No results count or "no results" message
- **Card details:** Missing agent count, rounds, duration on card surface — requires click to see
- **Icon mapping:** Emoji-based icons not accessible for screen readers
- **Template link:** "Use Template" navigates to wizard without pre-selecting the playbook

### Reports (`app/reports/page.tsx`)

- **Error state:** Error is set but never displayed to user
- **No sorting/filtering/pagination:** List grows unbounded
- **No download:** Despite "export" mentions in the description
- **Empty state CTA:** "View Simulations" instead of "Create Simulation"

### Persona Designer (`app/personas/designer/page.tsx`)

- **No confirmation:** Delete action is immediate and irreversible
- **Deprecated API:** `onKeyPress` used instead of `onKeyDown` at line 324
- **Native dropdowns:** `<select>` elements don't match custom design system
- **Slider context:** Authority level and Coalition Tendencies show numbers but no meaning (what does 5/10 mean?)
- **Layout:** 3-column layout on lg — saved personas sidebar may be too narrow for long names

### Behavioral Axioms (`app/personas/axioms/page.tsx`)

- **Mock delays:** 2-second simulated API calls with no actual error handling
- **No editing:** Extracted axioms are view-only — can't modify results
- **No export:** Can't save axiom results outside the UI
- **Confidence scores:** Percentage shown without context of what "good" looks like
- **Holdout accuracy:** 82% shown with no interpretation guidance

### Cross-Simulation Analytics (`app/analytics/cross-simulation/page.tsx`)

- **Insufficient data state:** No indication of how many simulations are needed
- **Toggle accessibility:** Custom toggle switch lacks ARIA label and attributes
- **Table semantics:** Headers are `<div>` not `<th>` — not screen-reader friendly
- **Mobile:** Table requires horizontal scroll with no indicator

### API Keys (`app/api-keys/page.tsx`)

- **Insecure generation:** `Math.random()` is not cryptographically secure
- **Key display:** Truncated to 12 chars — too short to verify ownership
- **No regeneration:** Only revoke and create new
- **Permission descriptions:** Missing explanations for each permission
- **Webhook events:** Show event names ("annotation.added") with no human-readable descriptions

### Fine-Tuning (`app/fine-tuning/page.tsx`)

- **Entirely mock:** Form submits create mock jobs with no API integration
- **Hardcoded params:** Learning rate fixed at 0.0001 despite appearing configurable
- **No file picker:** Data source is a plain text field
- **Progress:** Progress bar never actually updates (mock data)
- **Timestamps:** Full ISO format instead of relative time

---

## Simulation Sub-Pages (Shared Issues)

All 9 sub-pages under `app/simulations/[id]/` share these patterns:

| Issue | Details |
|-------|---------|
| **Loading state** | Identical bare text "Loading..." with no spinner |
| **Negative margins** | All use `-m-4 md:-m-6` creating mobile overflow risk |
| **Empty states** | Inconsistently implemented — some have icons + buttons, others are bare text |
| **Back navigation** | All have back button but missing breadcrumbs |
| **No error boundaries** | No retry mechanisms for failed API calls |
| **No ARIA attributes** | No accessibility labels on interactive elements |

### Sub-Page Specific Issues

- **Attribution:** PieChart icon used but no actual pie chart displayed; confidence scores lack context
- **Audit Trail:** Export handlers lack feedback; filter buttons have no active state indicator; hash display not monospaced
- **Fairness:** Circular score display hard to read; p-value column shows raw floats with no interpretation; score thresholds (0.8, 0.6) hardcoded with no explanation
- **Market Intel:** Stock cards break on mobile (3-column grid); volume formatting lacks unit labels (B/M/K); data appears static with no refresh
- **Network:** Fixed 1200px graph width overflows mobile; round selector dropdown has no label; legend is long and not collapsible
- **Sensitivity:** TornadoChart uses fixed 900px width; "Low (-)" / "High (+)" notation is confusing; impact column missing direction indicator
- **Timeline:** Redundant round selection (dropdown + slider); agent stance bars hard to interpret; no color legend
- **Voice:** Uses `alert()` instead of toasts; recording starts without verifying agent selection; agent colors may not match network graph
- **ZOPA:** Position bars use overlapping elements that obscure meaning; red line markers at arbitrary percentages; flexibility score visualization unclear

---

## Component-Level Issues

### Modal (`components/ui/Modal.tsx`)

- Missing `role="dialog"` and `aria-modal="true"`
- No `aria-labelledby` referencing the title
- No focus trap — focus escapes to background elements
- Close button lacks `aria-label="Close modal"`
- No open/close transition animation
- Uses `bg-slate-800` instead of `bg-background-secondary` token

### Button (`components/ui/Button.tsx`)

- Loading state missing `aria-busy="true"` and `aria-disabled="true"`
- Icon-only buttons don't require `aria-label` prop
- Disabled state only changes opacity, not text color
- Focus ring offset blends with dark background

### Input (`components/ui/Input.tsx`)

- Error state missing `aria-invalid="true"`
- Error message not associated via `aria-describedby`
- Helper text also lacks `aria-describedby` association

### Sidebar (`components/Sidebar.tsx`)

- Fixed `w-64` (256px) breaks on small devices
- Section headers (`<div>`) should be `<h3>` for semantics
- Inconsistent padding: `py-2.5` (main nav) vs `py-2` (other sections)
- Missing `focus-visible` ring styling on links
- Closes on every route change — no state persistence

### Header (`components/Header.tsx`)

- Notification button lacks `aria-label`
- Breadcrumbs missing `aria-current="page"` and `<nav>` wrapper
- Not sticky — scrolls away on mobile
- No text truncation for long simulation names

### AgentCard (`components/simulation/AgentCard.tsx`)

- Clickable `<div>` should be `<button>` with keyboard support
- Status dot (green/gray) lacks semantic meaning — needs `aria-label`
- Agent color as text color may not meet WCAG AA contrast requirements
- Hardcoded Slate colors instead of design tokens

### SimulationFeed (`components/simulation/SimulationFeed.tsx`)

- Missing `aria-live="polite"` for auto-appending messages
- Round headers should have `role="separator"` with `aria-label`
- Timestamps not wrapped in `<time>` element
- Hardcoded Slate colors instead of design tokens

---

## Recommended Fix Order

### Phase 1: Accessibility (Critical)
- [x] Add `role="dialog"`, `aria-modal`, focus trap to Modal
- [x] Replace `<div onClick>` with `<button>` on AgentCard
- [x] Add `aria-live="polite"` to SimulationFeed
- [x] Add `aria-busy`, `aria-invalid`, `aria-describedby` to Button and Input
- [x] Wrap breadcrumbs in `<nav>` with `aria-current`

### Phase 2: Error Handling (Critical)
- [x] Replace all `console.error()` with user-visible error toast/banner component
- [x] Add error boundaries to all page layouts
- [x] Add retry mechanisms for failed API calls

### Phase 3: Design Token Migration (High)
- [x] Replace hardcoded Slate colors in AgentCard, SimulationFeed, Modal with theme tokens
- [x] Unify spacing (consistent `py-2` or `py-2.5` in sidebar)
- [x] Replace native `<select>` with custom components matching design system

### Phase 4: Loading & Empty States (High)
- [x] Create shared `<Spinner>` and `<EmptyState>` components
- [x] Apply consistent loading states across all pages
- [x] Add meaningful empty states with CTAs

### Phase 5: Responsive Fixes (Medium)
- [x] Make sidebar responsive (collapsible or narrower on small screens)
- [x] Fix network graph and tornado chart overflow on mobile
- [x] Remove negative margins or contain overflow
- [x] Make header sticky on mobile

### Phase 6: Interaction Improvements (Medium)
- [x] Increase polling intervals to 5-10 seconds
- [x] Add pagination and sorting to tables
- [x] Replace `alert()` calls with toast notifications
- [x] Add wizard draft persistence via localStorage
- [x] Replace `Math.random()` with `crypto.getRandomValues()` for API keys

---

## Verification

This section ties each **Recommended Fix Order** phase to the numbered items in **Critical Issues**, **High Priority — UX Degradation**, and **Medium Priority — Polish & Consistency**, and records how work was validated. **Pull request links and before/after artifacts are placeholders** until they are backfilled from your Git host (replace `<ORG>/<REPO>` and PR numbers, or paste full `https://github.com/.../pull/N` URLs).

### Traceability legend

| Phase | Primary sources in this document |
|-------|----------------------------------|
| Phase 1 | **Critical Issues** #1, #3; **High** #14; **Recommended Fix Order** — Phase 1; **Component-Level Issues** — Modal, Button, Input, parts of Sidebar/Header |
| Phase 2 | **Critical Issues** #2, #4; **High** #15 (partial); **Recommended Fix Order** — Phase 2 |
| Phase 3 | **High** #8, #9 (partial styling), #19; **Medium** #16, #18; **Recommended Fix Order** — Phase 3 |
| Phase 4 | **High** #7, #9; **Recommended Fix Order** — Phase 4; **Page-by-Page** — Dashboard, Wizard, shared sub-page loading |
| Phase 5 | **High** #10, #23; **Medium** #17, #22; **Recommended Fix Order** — Phase 5; **Simulation Sub-Pages** — Network, Sensitivity, etc. |
| Phase 6 | **Critical Issues** #5; **High** #6, #12, #13 (partial), #26, #15; **Medium** #25, #31; **Recommended Fix Order** — Phase 6 |

### Pull requests and implementation links

| Phase | Remediation scope (maps to tables above) | PR / merge request | Notes |
|-------|--------------------------------------------|----------------------|-------|
| 1 | Modal a11y (#1), AgentCard semantics (#3), SimulationFeed live region (#14), Button/Input ARIA, nav semantics | _Add:_ `https://github.com/<ORG>/<REPO>/pull/<N>` | Replace when the accessibility batch is merged. |
| 2 | User-visible errors (#2), error boundaries (#4), retries | _Add PR link_ | If split across PRs, list multiple rows or use a tracking issue. |
| 3 | Design tokens (#8), sidebar spacing (#16), custom Select (#19), focus rings (#18) | _Add PR link_ | |
| 4 | Spinner/EmptyState (#7, #9), empty/loading consistency | _Add PR link_ | |
| 5 | Responsive sidebar (#10), chart overflow (#23, Medium #22), sticky header (#17) | _Add PR link_ | |
| 6 | Polling (#6), tables (#15), toasts vs `alert()` (#26), wizard draft (#25, Low #31), API key RNG (#5) | _Add PR link_ | May align with branch `feat/optimize-post-sim-pipeline` or successor; confirm in git history. |

### Per-phase verification record

#### Phase 1: Accessibility (Critical)

| Remediation (from **Recommended Fix Order**) | Issue # (from **Critical Issues** / **High**) | Manual QA checklist | Automated / tooling | A11y metrics (optional) |
|-----------------------------------------------|-----------------------------------------------|----------------------|----------------------|-------------------------|
| Modal: `role="dialog"`, focus trap, labelling | #1 | Open modal → Tab stays inside → Esc closes → focus returns | Component/e2e where Modal is covered | Lighthouse “Accessibility” score; axe DevTools on modal open |
| AgentCard: real `<button>`, keyboard | #3 | Tab to card → Enter/Space activates | E2E if AgentCard is exercised | — |
| SimulationFeed: `aria-live` | #14 | Turn on screen reader; append message; verify announcement | — | — |
| Button/Input ARIA | — (Component-Level) | Loading state, invalid input announced | Unit tests for `Button`/`Input` if present | — |
| Breadcrumbs `<nav>` + `aria-current` | — (Header / Medium #21 context) | Tab through breadcrumb; current page indicated | — | — |

**Before / after:** _Screenshots:_ `docs/research/ui-verification/phase-1-modal-before.png` → `.../phase-1-modal-after.png` _(paths TBD — add to repo or link to design tool)._  
**Metric diff example:** _Lighthouse accessibility score: before `__` → after `__` (same URL, same throttling)._  

#### Phase 2: Error Handling (Critical)

| Remediation | Issue # | Manual QA checklist | Automated / tooling |
|-------------|---------|----------------------|------------------------|
| Toasts/banners instead of silent `console.error` | #2 | Disconnect API; confirm visible error on Dashboard, Monitor, Chat, Playbooks | E2E global-setup + targeted routes |
| Error boundaries | #4 | Throw in a child component; page shows boundary UI, not white screen | `frontend` error boundary tests if any |
| Retry on failed API | #2 | Trigger failure then retry control | — |

**Before / after:** _Screenshot:_ empty/broken UI vs toast + recovery. _PR:_ _link above._

#### Phase 3: Design Token Migration (High)

| Remediation | Issue # | Manual QA checklist | Automated / tooling |
|-------------|---------|----------------------|------------------------|
| Tokens vs Slate in AgentCard, SimulationFeed, Modal | #8 | Visual regression on key pages | `npm run build`; optional Percy/Chromatic |
| Sidebar padding consistency | #16 | Compare nav blocks at same breakpoint | — |
| Custom `<Select>` in persona designer | #19 | Keyboard open/close/select | — |

**Before / after:** _Side-by-side or design-token diff in Figma/Git._

#### Phase 4: Loading & Empty States (High)

| Remediation | Issue # | Manual QA checklist | Automated / tooling |
|-------------|---------|----------------------|------------------------|
| Shared Spinner + EmptyState | #7, #9 | Dashboard with zero sims; each `[id]` sub-route loading | E2E smoke on `/`, `/simulations/[id]/*` |
| CTAs in empty states | #7 | Click CTA routes correctly | — |

**Before / after:** _“Loading...” text vs Spinner component (screenshot); empty dashboard before/after._

#### Phase 5: Responsive Fixes (Medium)

| Remediation | Issue # | Manual QA checklist | Automated / tooling |
|-------------|---------|----------------------|------------------------|
| Sidebar behavior on small viewports | #10 | iPhone SE width: content usable | Manual + optional Playwright viewport |
| Network graph / Tornado overflow | #23, Sensitivity detail | Horizontal scroll or responsive canvas | — |
| Negative margins / overflow | #22 | Spot-check Monitor, Attribution, Voice | — |
| Sticky header | #17 | Scroll long page on mobile | — |

**Before / after:** _Viewport screenshots 375px vs 1280px; Network page scroll._

#### Phase 6: Interaction Improvements (Medium)

| Remediation | Issue # | Manual QA checklist | Automated / tooling |
|-------------|---------|----------------------|------------------------|
| Polling interval 5–10s | #6 | Network tab: interval between polls | — |
| Pagination / sorting on tables | #15 | Sort columns; next page | Unit/integration if table helpers tested |
| Toasts vs `alert()` on Voice | #26 | Complete action; toast only | E2E Voice page |
| Wizard draft (localStorage) | #25, #31 | Refresh mid-wizard; state restored | E2E or manual |
| API keys: `crypto.getRandomValues` | #5 | Generate key; inspect entropy / no `Math.random` in bundle for that path | Code review + quick runtime check |

**Before / after:** _Lighthouse performance (polling impact); security note for #5 in PR description._

### Consolidated test and audit commands

Run from repo root after starting the app (`./start.sh` or `npm run dev`), unless noted:

| Check | Command / action |
|-------|------------------|
| Frontend lint | `cd frontend && npm run lint` |
| Frontend typecheck | `cd frontend && npx tsc --noEmit` |
| Frontend production build | `cd frontend && npm run build` |
| E2E (needs app up) | `npm run test:e2e` or `npm run test:e2e:p0` |
| Lighthouse (manual) | Chrome DevTools → Lighthouse → Accessibility & Best Practices on key routes |

### Screenshot and metric storage (for reviewers)

| Artifact type | Suggested location | What to capture |
|---------------|-------------------|-----------------|
| Before/after screenshots | `docs/research/` (or your design system folder) | Modal, dashboard empty, mobile sidebar, network graph |
| Lighthouse HTML / JSON | Attach to PR or CI artifact | Same URL pre/post merge |
| A11y | axe report export optional | Full page scan on `/`, `/simulations`, wizard |

**Maintainers:** When a phase ships, add one row to **Pull requests and implementation links**, drop in the PR URL, and attach or link the before/after pair so reviewers can trace **Critical Issues** → **Recommended Fix Order** → **Verification** → **PR** → **evidence**.
