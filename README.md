# GPTCraft — React Frontend

The React/TypeScript interface for the personal GPTCraft chat application. The API is maintained on the separate [backend branch](https://github.com/Nitsh-kumar/GPT_craft/tree/backend).

**Status:** in development. UI model choices, plan names, quotas, and backend contracts are not yet aligned. This is separate from the employer CRAFT SAP migration project.

## Implemented interface

Authentication pages, chat/history views, API-client services, quota display, and animated UI components.

Model choices are currently a static list. The selected model identifier is not sent through the reviewed chat request. A completed JSON response is revealed gradually in the UI; this is simulated display streaming, not token streaming over the network.

## Local setup

Clone this branch separately from the backend:

```bash
git clone --branch frontend https://github.com/Nitsh-kumar/GPT_craft.git GPT_craft_frontend
cd GPT_craft_frontend
npm ci
```

Use a Node.js release compatible with the declared Vite dependencies. Create a local `.env` with:

```dotenv
VITE_API_BASE_URL=http://localhost:8000
```

This is the base URL read by `src/services/api.ts`. Run the backend in a separate checkout and ensure its configured frontend origin matches the UI.

```bash
npm run dev
npm run lint
npm run build
npm run preview
```

The development script uses port 3000 and binds to all interfaces. The script named `lint` runs TypeScript's `tsc --noEmit`; it is a type check, not ESLint. Build and type-check success have not been verified in this documentation pass.

Do not put provider secrets into browser-exposed environment variables. The reviewed chat path uses the backend; a declared Gemini dependency alone does not establish a working Gemini integration.

## Source map

- [src/context/AuthContext.tsx](src/context/AuthContext.tsx): authentication state.
- [src/services/api.ts](src/services/api.ts): API base URL and bearer-token requests.
- [src/services/chatService.ts](src/services/chatService.ts): chat/model/quota contracts.
- [src/hooks/useQuota.ts](src/hooks/useQuota.ts): quota consumer.
- [src/App.tsx](src/App.tsx): application composition.

## Known limitations

- Fix the quota-service argument mismatch before claiming a clean type check.
- Align plan names and model requests with actual backend support.
- Review bearer-token storage and OAuth token transport before public use.
- Implement transport streaming before advertising real-time model streaming.
- The reviewed tree has no LICENSE file; the previous MIT badge was not a license grant.

No live deployment, inference latency, model availability, or application run was verified on 13 October 2026. Read the backend's project-status notes for cross-branch work.
