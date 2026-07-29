---
name: opener-site
description: Edit the opener.se single-page site (index.html). Use whenever the user asks to change copy, layout, or styling on this site, or says things like "update the paragraph", "change the font size", "tighten the copy".
---

# Opener site editing

This is a single static page (`index.html`) for opener.se, an enterprise service-messaging consultancy. No build step — edit the file directly, commit, and push.

## Workflow

1. Read `index.html` before editing (required before any Edit call).
2. Make the change.
3. Commit with a short, specific message and push to `origin main` in the same turn, unless the user says otherwise. This project treats push-on-every-change as the default — don't ask permission each time.

```
git add index.html
git commit -m "<message>" 
git push origin main
```

## Copy voice

The site copy is the main lever here — it gets revised often. Rules, derived from direct feedback in this project:

- **Lead with the offer, not the problem.** Don't explain the client's pain point before stating what we provide. Open with the capability/deliverable.
- **No self-referential language.** Avoid "Opener is a consultancy that...", "We help brands...", "We design and build...". State the offer directly as a thing that exists, not as a sentence about the company doing something.
- **Matter-of-fact, Scandinavian business-engineer tone.** No marketing adjectives (vibrant, seamless, robust, cutting-edge). No persuasive framing. Value, stated plainly, in as few words as possible.
- **Tighten aggressively when asked.** "Tighten it" means cut every word that isn't carrying a fact. Prefer five short sentences over two long ones.
- Run final copy through the `humanizer` skill (installed at `~/.claude/skills/humanizer`) before committing — in particular, **no em dashes or en dashes**, ever, on this site.

## Design conventions

- Font: Uncut Sans, variable weight, self-hosted at `fonts/UncutSans-Variable.woff2` (loaded via `@font-face`, `font-weight: 100 900`).
- The body text element (`p`) is the focal point of the page — centered, both horizontally (`margin: 0 auto`) and vertically (`body { display: flex; align-items: center; }`).
- Widths are expressed in `vw`, not fixed px or %. The user favours proportionally meaningful numbers — e.g. golden ratio (`61.8vw`) over round numbers.
- Maintain responsive breakpoints at `1200px` and `768px`. Narrower viewports get wider relative text width and a smaller font-size, never the inverse.
- Check whatever the current font-size/line-height/letter-spacing is in the file before changing it — these get tuned incrementally (e.g. 16px → 20px → 35px, line-height 1.2 → 1.1 → 1.15) and the user may have already adjusted them outside the conversation (e.g. via IDE edits). Don't assume the values mentioned earlier in chat are still current — read the file first.

## SEO / structured data

`<title>`, meta description, Open Graph, Twitter card, and the JSON-LD `ProfessionalService` block should stay in sync with whatever the current paragraph copy says about Opener's positioning. When the visible paragraph changes meaningfully, check whether these need updating too — but don't auto-rewrite them on every micro-edit (e.g. a font-size tweak doesn't need a meta update).
