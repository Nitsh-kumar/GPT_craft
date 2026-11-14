---
name: GPTCraft Modern Studio
description: High-precision Personal Agent SaaS workbench with dual theme, crisp slate alabaster palette, and electric cobalt accent
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

GPTCraft's "Modern Studio / Precision Atelier" design system supports an operator-hosted Personal Agent workbench. Defined in [`frontend/src/index.css`](frontend/src/index.css), it balances crisp architectural structure, high-contrast typography, and clear visual hierarchy for live agent telemetry, Human-in-the-Loop (HITL) approval gates, and persistent personalization.

## Colors & Semantic Tokens

- **Canvas & Surface**: Crisp alabaster (`--canvas: #f8fafc`, `--surface: #ffffff`, `--sunken: #f1f5f9`) in light mode; deep obsidian (`--canvas: #090d16`, `--surface: #0f172a`, `--raised: #182234`, `--sunken: #05080e`) in dark mode.
- **Ink (Text) & Hairlines**: Midnight-to-muted slate hierarchy (`--ink`, `--ink-2`, `--ink-3`) and 1px structural borders (`--line`, `--line-strong`).
- **Signature Accent (Cobalt)**: Electric cobalt (`--accent: #2563eb` light / `#3b82f6` dark, with `--accent-hover`, `--accent-soft`, `--on-accent`, plus legacy `--ember*` aliases) for active modes, primary actions, and running agent highlights.
- **Functional Status**: Forest green (`--ok`), amber ochre (`--warn`), and crimson (`--danger` / `--danger-soft`) for quota thresholds, HITL capability gates, diff additions/deletions, and execution outcomes.

## Typography

- **Headings & Brand**: `Outfit` geometric sans (`font-display`) with tight tracking (`-0.03em`).
- **Interface & Reading**: `Inter` sans-serif with `tabular-nums` for quota counters and `.prose-craft` markdown rendering.
- **Code & Telemetry**: `JetBrains Mono` (`font-mono`) for code blocks, unified diffs, terminal command viewers, model identifiers, and latency tags.

## Layout & Surfaces

- **Studio Workbench Empty State** ([`MessageList.tsx`](frontend/src/components/chat/MessageList.tsx)): Displays the active model indicator, greeting, 4 v1 Craft Mode starter tiles (`Deep Architect`, `Code Craft`, `Brainstorm`, `Standard Craft`), and a full-width featured `Agent Studio` card.
- **Message Stream** ([`MessageBubble.tsx`](frontend/src/components/chat/MessageBubble.tsx)): Separates right-aligned user prompts from structured assistant cards featuring a metadata header (brand mark, model chip, mode/AGENT badge, copy button), collapsible `TelemetryDrawer`, `.prose-craft` markdown output, and inline `ApprovalCard` when interrupted.
- **Input Cockpit** ([`ChatInput.tsx`](frontend/src/components/chat/ChatInput.tsx)): Elevated command dock (`rounded-2xl border-line-strong bg-raised shadow-lift`) housing the auto-resizing prompt textarea, model selector, mode switcher (including `Agent Studio` with `STUDIO` badge), memory status indicator, and send/stop controls.
- **Sidebar & Personalization Entry** ([`MainLayout.tsx`](frontend/src/components/layout/MainLayout.tsx)): Responsive conversation drawer with new-conversation action, history list, delete controls, and modal trigger for `PersonalizationModal`.

## Elevation & Shapes

- **Subtle Elevation**: `shadow-lift` and `shadow-float` utilities without heavy blur halos.
- **Structural Lines & Radii**: 1px crisp borders (`--line`, `--line-strong`), `rounded-xl` / `rounded-2xl` containers, and `rounded-full` pill selectors.

## Personal Agent & Workbench Components

- **Agent Studio Workbench & Input** ([`MessageList.tsx`](frontend/src/components/chat/MessageList.tsx), [`ChatInput.tsx`](frontend/src/components/chat/ChatInput.tsx)): Mode selection and starter prompts bridging v1 Craft Modes and Agent Studio execution.
- **ApprovalCard** ([`ApprovalCard.tsx`](frontend/src/components/chat/ApprovalCard.tsx)): Inline Tier 2+ HITL gate card (`border-warn/40 bg-surface/80`) rendering tool identifier, `Tier {tier} HITL` badge, rationale, target path or shell command pill, collapsible preview (line-numbered unified diff viewer with `--ok`/`--danger` highlights or copyable terminal command viewer), and three decision modes: `Reject with Feedback`, `Modify Diff` / `Modify Command`, and `Approve & Run`.
- **TelemetryDrawer** ([`TelemetryDrawer.tsx`](frontend/src/components/chat/TelemetryDrawer.tsx)): Collapsible per-turn execution inspector showing a summary bar (running/failed/completed badge, tool call & thought counts, capability tier chips, aggregated latency) and expandable sections for numbered `Model Reasoning Trace` and per-action `Workspace Tool Executions` (tier badge, duration, exit/status badge, JSON parameters, copyable stdout/stderr).
- **PersonalizationModal** ([`PersonalizationModal.tsx`](frontend/src/components/chat/PersonalizationModal.tsx)): Two-tab dialog (`Custom Instructions` with profile/style textareas and preset chips; `Remembered Facts` with master `Persistent Memory Active` toggle, categorized add-memory form for `general`/`tech_stack`/`project`/`preference`, per-item delete, and `Clear all memories`).
- **QuotaDisplay** ([`QuotaDisplay.tsx`](frontend/src/components/chat/QuotaDisplay.tsx)): Tabular daily remaining request and token counter with `--warn` and `--danger` threshold styling.
- **ThemeSwitcher** ([`ThemeSwitcher.tsx`](frontend/src/components/layout/ThemeSwitcher.tsx)): Segmented Light / Dark / System radio pill triggering ink-spread theme transitions.

## Do's and Don'ts

- **Do** use semantic CSS variables from [`frontend/src/index.css`](frontend/src/index.css) and verify WCAG contrast in both light and dark modes.
- **Do** surface agent rationale, capability tiers, and tool outputs transparently via `ApprovalCard` and `TelemetryDrawer`.
- **Don't** document unimplemented agent UI screens (such as a credential vault UI or integrations marketplace) as shipped surfaces until built.
- **Don't** use decorative glowing text shadows or oversized blur halos.
