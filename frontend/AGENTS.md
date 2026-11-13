# GPTCraft Frontend — Agent Rules (`frontend/`)

## Stack & Conventions
- **Core**: React 19, TypeScript (~5.8), Vite 6, React Router 7.
- **Styling**: Tailwind CSS v4 (`@tailwindcss/vite`), `clsx` + `tailwind-merge` (`src/utils/cn.ts`), Framer Motion (`motion`), Lucide Icons (`lucide-react`).
- **State & Networking**: `AuthContext` (`src/context/AuthContext.tsx`), custom hooks (`useChat`, `useQuota`), and native `fetch` wrapper (`src/services/api.ts`).

## Strict Engineering Rules
1. **API & Secrets**:
   - All backend requests must use `VITE_API_BASE_URL` via `src/services/api.ts` (`apiFetch`) or `src/services/chatService.ts`.
   - Never add AI provider SDKs or secret API keys to the frontend bundle.
2. **Type Safety**:
   - Keep `src/types/index.ts` strictly aligned with `backend/app/schemas/auth.py` and `backend/app/schemas/chat.py`.
   - Avoid `any` types. Always run `npm run lint` (`tsc --noEmit`) after modifying TypeScript files.
3. **Component Architecture**:
   - Keep page components (`src/pages/`) thin; delegate state management to hooks (`src/hooks/`) and reusable UI primitives (`src/components/`).
   - Handle loading, empty, error, and abort (`AbortController`) states gracefully in all chat and quota interactions.
4. **Agent Studio & SSE Envelope Parsing**:
   - All streaming responses must be parsed through `src/utils/sseParser.ts` (`parseSseBuffer`), which normalizes both typed Agent Studio envelopes (`thought`, `action_call`, `approval_required`, `action_result`, `token`, `done`) and legacy conversational frames.
   - Always run `npm run test:unit` and `npm run lint` after modifying streaming parsers, hooks, or Agent Studio components.
