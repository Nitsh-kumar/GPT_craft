# GPTCraft Frontend — Agent Rules (`frontend/`)

## Stack & Conventions
- **Core**: React 19, TypeScript (~5.8), Vite 6, React Router 7.
- **Styling**: Tailwind CSS v4 (`@tailwindcss/vite`), `clsx` + `tailwind-merge` ([`src/utils/cn.ts`](src/utils/cn.ts)), Framer Motion (`motion`), Lucide Icons (`lucide-react`).
- **State & Networking**: [`AuthContext`](src/context/AuthContext.tsx), custom hooks ([`useChat`](src/hooks/useChat.ts), [`useQuota`](src/hooks/useQuota.ts)), and native `fetch` services ([`src/services/api.ts`](src/services/api.ts), [`src/services/chatService.ts`](src/services/chatService.ts), [`src/services/memoryService.ts`](src/services/memoryService.ts)).

## Strict Engineering Rules
1. **API & Secrets**:
   - All backend requests must route through `VITE_API_BASE_URL` via [`src/services/api.ts`](src/services/api.ts) (`apiFetch`), [`src/services/chatService.ts`](src/services/chatService.ts), or [`src/services/memoryService.ts`](src/services/memoryService.ts).
   - Never add AI provider SDKs, backend secrets, or Supabase service-role keys to the frontend bundle.
2. **Type & Contract Sync**:
   - Keep [`src/types/index.ts`](src/types/index.ts) strictly aligned with [`backend/app/schemas/auth.py`](../backend/app/schemas/auth.py), [`backend/app/schemas/chat.py`](../backend/app/schemas/chat.py), and [`backend/app/schemas/memory.py`](../backend/app/schemas/memory.py).
   - Follow HTTP/SSE casing and contract rules in [`docs/OPERATIONS.md`](../docs/OPERATIONS.md). Avoid `any` types and run `npm run lint` (`tsc --noEmit`) after TypeScript edits.
3. **Component Architecture**:
   - Keep page components (`src/pages/`) thin; delegate state management to hooks (`src/hooks/`) and reusable UI primitives (`src/components/`).
   - Handle loading, empty, error, and abort (`AbortController`) states gracefully across conversation, approval, personalization, and quota flows.
4. **Agent Studio & SSE Envelope Parsing**:
   - Parse all streaming responses through [`src/utils/sseParser.ts`](src/utils/sseParser.ts) (`parseSseBuffer`), which normalizes Agent Studio envelopes (`thought`, `action_call`, `approval_required`, `action_result`, `token`, `done`, `error`) and legacy v1 conversational frames (`start`, `chunk`, `done`, `error`).
   - Run `npm run test:unit`, `npm test`, `npm run lint`, and `npm run build` after modifying streaming parsers, hooks, types, or Agent Studio components (plus `npm run test:e2e` for Playwright browser contracts).
