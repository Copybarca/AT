# AT translation frontend

Runtime React application for document upload, translation monitoring, manual
fragment editing, and final PDF build/rebuild.

## Commands

```bash
npm install
npm run dev
npm run check
```

The application defaults to an in-memory deterministic demo repository. Set
`VITE_API_BASE_URL` to use the HTTP adapter and `VITE_WS_URL` to enable realtime
cache invalidation; manual refresh remains available without WebSocket.
