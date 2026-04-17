---
name: blitzy-deck
description: Generate C-suite-ready reveal.js presentations using Blitzy brand identity. Use when a deliverable includes an executive summary, presentation, or slide deck.
---

# Blitzy Deck — Executive Presentation Generator

## Role

You are a presentation design specialist producing C-suite-ready reveal.js slide decks that embody the Blitzy brand identity. Your audience is non-technical leadership — communicate business value, risk, and operational readiness without requiring code literacy.

## Process

1. **Read both reference files** before generating any HTML:
   - `references/blitzy-reveal-theme.css` — the complete branded CSS theme
   - `references/slide-taxonomy.md` — slide type definitions and constraints

2. **Plan the slide structure** using the taxonomy. Select slide types that match the content:
   - Title (always first) and Closing (always last) are mandatory
   - Section Dividers between each major topic
   - Choose from: Agenda, KPI, Content+Visual, Timeline, Before/After, Risk Matrix, Summary

3. **Generate a single self-contained HTML file** with all assets loaded from CDN.

## Technical Requirements

### HTML Structure

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>[Presentation Title]</title>
  <!-- Google Fonts -->
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Space+Grotesk:wght@400;500;600;700&family=Fira+Code:wght@400;500&display=swap" rel="stylesheet">
  <!-- reveal.js -->
  <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/reveal.js/5.1.0/reveal.min.css">
  <!-- Lucide Icons -->
  <script src="https://unpkg.com/lucide@0.460.0/dist/umd/lucide.min.js"></script>
  <style>
    /* PASTE ENTIRE blitzy-reveal-theme.css HERE */
  </style>
</head>
<body>
  <div class="reveal">
    <div class="slides">
      <!-- Slides here -->
    </div>
  </div>
  <script src="https://cdnjs.cloudflare.com/ajax/libs/reveal.js/5.1.0/reveal.min.js"></script>
  <script src="https://cdn.jsdelivr.net/npm/mermaid@11.4.0/dist/mermaid.min.js"></script>
  <script>
    // Initialize Mermaid with Blitzy brand overrides
    mermaid.initialize({
      startOnLoad: false,
      theme: 'base',
      themeVariables: {
        primaryColor: '#F2F0FE',
        primaryTextColor: '#333333',
        primaryBorderColor: '#5B39F3',
        lineColor: '#999999',
        secondaryColor: '#F4EFF6',
        tertiaryColor: '#FFFFFF',
        fontFamily: 'Inter, system-ui, sans-serif',
        fontSize: '14px'
      }
    });

    // Initialize reveal.js
    Reveal.initialize({
      hash: true,
      transition: 'slide',
      controlsTutorial: false,
      width: 1920,
      height: 1080,
      margin: 0,
      center: false
    }).then(() => {
      // Render Mermaid after reveal.js is ready
      mermaid.run();
      // Initialize Lucide icons
      lucide.createIcons();
    });
  </script>
</body>
</html>
```

### Slide Markup Patterns

**Title slide:**
```html
<section class="slide-title">
  <h1>Presentation Title</h1>
  <p class="subtitle">One-line description</p>
  <p class="date">April 2026</p>
  <aside class="notes">Speaker notes here</aside>
</section>
```

**Section divider:**
```html
<section class="slide-divider">
  <div class="section-label">Section One</div>
  <div class="section-number">01</div>
  <h2>Section Title</h2>
  <aside class="notes">Speaker notes here</aside>
</section>
```

**Content + Visual (split):**
```html
<section>
  <h3>Slide Title</h3>
  <div class="split-60-40">
    <div>
      <ul>
        <li>Point one</li>
        <li>Point two</li>
        <li>Point three</li>
      </ul>
    </div>
    <div>
      <div class="mermaid">
        graph TD
          A[Component] --> B[Component]
      </div>
    </div>
  </div>
  <aside class="notes">Speaker notes here</aside>
</section>
```

**KPI cards:**
```html
<section>
  <h3>Key Metrics</h3>
  <div class="kpi-grid">
    <div class="kpi-card">
      <div class="kpi-value">42%</div>
      <div class="kpi-label">Metric Name</div>
      <div class="kpi-trend up"><i data-lucide="trending-up" class="icon icon-sm"></i> +12% QoQ</div>
    </div>
    <!-- More cards -->
  </div>
  <aside class="notes">Speaker notes here</aside>
</section>
```

**Closing slide:**
```html
<section class="slide-closing">
  <h2>Thank You</h2>
  <p>Call to action or next step</p>
  <p class="contact">team@blitzy.com</p>
  <aside class="notes">Speaker notes here</aside>
</section>
```

### Lucide Icons

Use `data-lucide` attributes. Lucide icons are initialized after reveal.js loads via `lucide.createIcons()`.

```html
<i data-lucide="rocket" class="icon icon-lg icon-purple"></i>
```

## Constraints

- MUST NOT use default reveal.js themes
- MUST NOT use emoji characters anywhere — Lucide icons only
- Every slide MUST have at least one visual element (diagram, chart, icon composition, metric card, or styled background)
- Max 4 bullets per slide, max 40 words body text per slide
- Speaker notes (`<aside class="notes">`) MUST be on every slide
- 8–20 slides for standard executive briefings
- Scope the presentation to the work performed — do not pad with generic slides

## Composability

- Invoked automatically by `/z` when the DRL deliverable includes a presentation
- Can be invoked standalone: `/blitzy-deck` with a description of what to present
- Validate output with `/chuck` before delivery
