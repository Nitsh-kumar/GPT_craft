---
name: GPTCraft Modern Studio
description: High-precision atelier and conversational workbench with dual theme, crisp slate alabaster palette, and electric cobalt accent
colors:
  primary: "#2563eb"
  primary-hover: "#1d4ed8"
  canvas-light: "#f8fafc"
  canvas-dark: "#090d16"
  surface-light: "#ffffff"
  surface-dark: "#0f172a"
  raised-light: "#ffffff"
  raised-dark: "#182234"
  ink-light: "#0f172a"
  ink-dark: "#f8fafc"
  line-light: "#e2e8f0"
  line-dark: "#1e293b"
typography:
  display:
    fontFamily: "Outfit, Inter, -apple-system, sans-serif"
    fontSize: "clamp(2rem, 4vw, 2.75rem)"
    fontWeight: 650
    lineHeight: 1.15
    letterSpacing: "-0.03em"
  body:
    fontFamily: "Inter, -apple-system, BlinkMacSystemFont, sans-serif"
    fontSize: "0.95rem"
    fontWeight: 400
    lineHeight: 1.68
    letterSpacing: "normal"
  code:
    fontFamily: "JetBrains Mono, ui-monospace, monospace"
    fontSize: "0.85rem"
rounded:
  sm: "6px"
  md: "10px"
  lg: "14px"
  full: "9999px"
spacing:
  xs: "4px"
  sm: "8px"
  md: "16px"
  lg: "24px"
  xl: "32px"
components:
  button-primary:
    backgroundColor: "{colors.primary}"
    textColor: "#ffffff"
    rounded: "{rounded.lg}"
    padding: "10px 20px"
---

## Overview

GPTCraft's "Modern Studio / Precision Atelier" system is designed for power users, engineers, and creators who need a high-performance, distraction-free AI workbench. Rejecting generic paper metaphors and neon cyber-slop alike, it balances crisp architectural structure with high-contrast precision.

## Colors

- **Canvas & Surface**: Crisp alabaster (`#f8fafc` / `#ffffff`) in light mode; deep studio obsidian (`#090d16` / `#0f172a`) in dark mode.
- **Ink (Text)**: Slate hierarchy. Deep midnight slate (`#0f172a` light / `#f8fafc` dark) meeting WCAG AAA contrast (>12:1). Secondary text (`--ink-2`) and muted metadata (`--ink-3`) maintain minimum 4.5:1 ratio.
- **Signature Accent (Cobalt)**: Electric hyper-cobalt (`#2563eb` light, `#3b82f6` dark) used for active modes, primary send trigger, and active indicators.
- **Functional Status**: Forest green (`--ok`), amber ochre (`--warn`), and red crimson (`--danger`).

## Typography

- **Headings & Brand**: `Outfit` geometric sans with tight tracking (`-0.03em`) and crisp architectural punch.
- **Interface & Reading**: `Inter` sans-serif with tabular numerals for metrics and high-readability `.prose-craft` styling.
- **Code & Telemetry**: `JetBrains Mono` for code blocks, model identifiers, and Groq LPU latency tags.

## Layout

- **Studio Workbench Empty State**: 4 interactive Craft Mode workbench tiles (Deep Architect, Code Craft, Brainstorm, Standard Craft) with direct sample prompts and speed/capability indicators.
- **Message Stream**: Clear separation between prompt and response; assistant responses feature a dedicated meta header with model name, mode badge, and one-click copy.
- **Input Cockpit**: Elevated command dock with integrated mode tabs, fast model selector, and responsive textarea.

## Elevation & Depth

- **Subtle Elevation**: `shadow-lift` and `shadow-float` for tactile distinction without muddy blur halos.
- **Structural Lines**: 1px crisp borders (`--line` and `--line-strong`) delineating workbench panels and code blocks.

## Shapes

- Rounded pill controls for segmented mode selectors and theme toggles.
- Clean 10px-14px corner radii for workbench cards and message containers.

## Components

- **ThemeSwitcher**: Segmented Light / Dark / System control with circular ink-spread view transitions.
- **MessageBubble**: Assistant responses with structured metadata header and code inspection container.
- **MessageList**: Interactive Craft Mode studio workbench.
- **ChatInput**: Minimalist dock with model dropdown and mode filters.
- **QuotaDisplay**: Tabular real-time usage counter.

## Do's and Don'ts

- **Do** maintain strict WCAG AAA contrast for all body copy.
- **Do** showcase model information, mode context, and telemetry clearly.
- **Don't** use warm sepia/terracotta paper aesthetics that mimic Claude.
- **Don't** use decorative glowing text shadows or oversized blur halos.
