# Blitzy Slide Taxonomy

Reference for constructing C-suite-ready reveal.js presentations. Every presentation MUST use these slide types exclusively. Each type specifies its CSS class, required visual elements, and content density limits.

---

## 1. Title Slide

| Property | Value |
|----------|-------|
| CSS class | `slide-title` |
| Background | Hero gradient (automatic via CSS class) |
| Text color | White (automatic via CSS class) |
| Required elements | Presentation title (h1), subtitle or one-line description, date, presenter/team name |
| Visual element | The gradient background itself counts; optionally add a Lucide icon (icon-2xl) |
| Max text | Title + subtitle + date. No bullets. No paragraphs. |
| Position | MUST be slide 1 |

**Lucide icon suggestions:** `rocket`, `layers`, `shield-check`, `activity`, `bar-chart-3`

---

## 2. Agenda / Overview

| Property | Value |
|----------|-------|
| CSS class | (default content slide) |
| Background | White |
| Required elements | Numbered list with one Lucide icon per item |
| Visual element | Icon per agenda item (inline, `icon-lg`, `icon-purple`) |
| Max items | 7 |
| Max words per item | 8 |

**Structure:** Each item is a `<div>` with an inline Lucide icon + short label. Use a numbered grid or vertical list.

---

## 3. Section Divider

| Property | Value |
|----------|-------|
| CSS class | `slide-divider` |
| Background | Dark navy (automatic via CSS class) |
| Text color | White, teal accent for section number |
| Required elements | `.section-number` (large numeral), section title (h2) |
| Visual element | The section number itself is the visual anchor |
| Max text | Section number + title + optional one-line subtitle |
| Position | MUST appear between each major topic |

**Optional:** Add a `.section-label` (e.g., "SECTION TWO") above the title.

---

## 4. Key Metric / KPI

| Property | Value |
|----------|-------|
| CSS class | (default content slide) |
| Layout | `.kpi-grid` containing 2–4 `.kpi-card` elements |
| Required elements | `.kpi-value` (large number), `.kpi-label`, `.kpi-trend` with Lucide `trending-up` / `trending-down` / `minus` icon |
| Visual element | The metric cards themselves |
| Max cards | 4 per slide |
| Max text | Card label only (3–5 words each). No paragraphs outside cards. |

**Color coding:** Use `.kpi-trend.up` (green), `.kpi-trend.down` (red), `.kpi-trend.neutral` (gray).

---

## 5. Content + Visual (Split Layout)

| Property | Value |
|----------|-------|
| CSS class | (default content slide) |
| Layout | `.split` or `.split-60-40` |
| Required elements | Left: h3 + max 4 bullets. Right: Mermaid diagram, chart, or icon composition |
| Visual element | Right column MUST contain a diagram, chart, or visual — never just text |
| Max bullets | 4 |
| Max words per bullet | 15 |
| Max total body text | 40 words (excluding the visual) |

**This is the workhorse slide type.** Use for any point that benefits from a supporting diagram.

---

## 6. Timeline / Roadmap

| Property | Value |
|----------|-------|
| CSS class | (default content slide) |
| Layout options | `.timeline` CSS utility OR Mermaid Gantt chart |
| Required elements | Phase names, date ranges or milestones, status indicators |
| Visual element | The timeline or Gantt IS the visual |
| Max phases | 6 (use Mermaid Gantt for more complex timelines) |
| Max text | Phase labels + optional one-line descriptions |

**For `.timeline` CSS utility:** Use `.timeline-step` with `.active` / `.complete` state classes. Each step gets a `.timeline-dot` and `.timeline-label`.

**For Mermaid Gantt:** Brand colors applied automatically via CSS overrides.

---

## 7. Before / After (Comparison)

| Property | Value |
|----------|-------|
| CSS class | (default content slide) |
| Layout | `.comparison` containing `.before` + `.after` columns |
| Required elements | `.label` ("BEFORE" / "AFTER"), contrasting content in each column |
| Visual element | The dual-column contrast layout. Optionally add a Mermaid diagram in one or both columns. |
| Max bullets per column | 4 |
| Max words per column | 30 |

**Use for:** Architecture changes, process improvements, migration before/after states.

---

## 8. Risk Matrix

| Property | Value |
|----------|-------|
| CSS class | (default content slide) |
| Layout | `.risk-grid` containing `.risk-card` elements |
| Required elements | `.risk-label` + description per card. Use `.critical` / `.warning` / `.ok` modifier classes. |
| Visual element | Color-coded risk cards with Lucide icons (`alert-triangle`, `shield-check`, `alert-circle`) |
| Max cards | 4 per slide |
| Max words per card | 25 |

**Severity mapping:**
- `.critical` — red background, `alert-circle` icon
- `.warning` — amber background, `alert-triangle` icon
- `.ok` — green background, `shield-check` icon

---

## 9. Summary / Next Steps

| Property | Value |
|----------|-------|
| CSS class | (default content slide) |
| Layout | Numbered list or table |
| Required elements | Action items with owner and deadline. Use Lucide `check-circle` / `circle` for status. |
| Visual element | Status icons per item, or a small progress timeline |
| Max items | 6 |
| Max words per item | 15 |

**Structure each item as:** `[status icon] Action description — Owner — Deadline`

---

## 10. Closing Slide

| Property | Value |
|----------|-------|
| CSS class | `slide-closing` |
| Background | Feature gradient (automatic via CSS class) |
| Text color | White (automatic via CSS class) |
| Required elements | Closing statement or CTA (h2), optional contact/team info |
| Visual element | The gradient background itself. Optionally add a single Lucide icon (icon-2xl). |
| Max text | Title + one line. No bullets. No paragraphs. |
| Position | MUST be the last slide |

---

## General Constraints

| Constraint | Limit |
|------------|-------|
| Slide count (standard briefing) | 8–20 slides |
| Max bullets per content slide | 4 |
| Max body text per content slide | 40 words |
| Emojis | PROHIBITED — use Lucide SVG icons only |
| Text-only slides | PROHIBITED — every slide needs at least one visual element |
| Font usage | Inter (body), Space Grotesk (headings), Fira Code (code) |
| Speaker notes | REQUIRED on every slide |

## Lucide Icon Reference

Load via CDN: `https://unpkg.com/lucide@latest`

**Recommended categories by slide type:**

| Slide Type | Recommended Icons |
|------------|-------------------|
| Title | `rocket`, `layers`, `zap`, `sparkles` |
| Agenda | `check-circle`, `target`, `list-checks`, `compass` |
| KPI | `trending-up`, `trending-down`, `minus`, `bar-chart-3`, `activity` |
| Content | `git-branch`, `database`, `server`, `code-2`, `workflow` |
| Timeline | `clock`, `calendar`, `milestone`, `flag` |
| Risk | `alert-triangle`, `alert-circle`, `shield-check`, `shield-alert` |
| Summary | `check-circle`, `circle`, `arrow-right`, `clipboard-list` |
| Closing | `heart`, `handshake`, `mail`, `external-link` |
