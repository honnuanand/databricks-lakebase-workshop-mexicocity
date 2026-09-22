# assets/ — brand images

Databricks and Lakebase brand assets used in the workshop README and (later) journey docs.
Copied from `../lakebase-pitch/frontend/public/` so the workshop doesn't reference across repos.

> **Warning**
> These are Databricks-internal brand assets. Keep them internal. Do not publish this repo
> externally or to a public host with these files embedded.

## Files

| File                          | What it is                                        | Use on                    |
| ----------------------------- | ------------------------------------------------- | ------------------------- |
| `lakebase-lockup.png`         | Lakebase icon + "Lakebase" wordmark, dark ink     | Light backgrounds only    |
| `lakebase-icon.png`           | Square Lakebase icon (512×512)                    | Light or dark backgrounds |
| `databricks-primary-color.svg`| Databricks lockup (icon + wordmark), dark ink     | Light backgrounds         |
| `databricks-primary-white.svg`| Databricks lockup, white                          | Dark backgrounds          |
| `databricks-logo.svg`         | Databricks icon-only red glyph (tiny)             | Favicons / inline marks   |

## Rules (from the pitch app's brand setup)

- **Don't recolor or distort** the official lockups. Pick the variant that matches the
  background: color on light, white on dark.
- **There is no official Lakebase wordmark-on-dark asset and no Lakebase SVG** yet. For a dark
  background, compose `lakebase-icon.png` next to the text "Lakebase" in a theme color. Do not
  invent a Lakebase lockup.
- Databricks typeface is **DM Sans**. The pitch app also uses **Public Sans** and **DM Mono**.

## Palette (Databricks brand, from the pitch app's `--lb-*` CSS vars)

Primary accent is Databricks **red `#FF3621`**. Use one accent for primary actions; teal, amber,
and orange are semantic (status / meaning), not decoration.

| Role    | Brand     | Light (on white) |
| ------- | --------- | ---------------- |
| red     | `#FF3621` | `#E5321F`        |
| redDark | `#C8102E` |                  |
| orange  | `#FF7033` | `#D9541F`        |
| amber   | `#FBB300` | `#B77A00`        |
| teal    | `#00C7B7` | `#0A8F86`        |
| navy    | `#0B1B2B` |                  |

Dark theme ground: bg `#07131F`, elevated `#0E1E2E`, text `#F5F7FA`, dim `#9DB0C2`, line `#22415C`.
Light theme ground: bg `#F7F9FB`, elevated `#FFFFFF`, text `#0B1B2B`, dim `#4A5B6B`, line `#D3DCE5`.
