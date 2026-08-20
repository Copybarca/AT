# Realtime monitoring requirements

Status: **APPROVED FOR OPTIONAL REALTIME WITH MANUAL-REFRESH FALLBACK**

The frontend requires live monitoring, but a WebSocket client must not be
implemented until the server endpoint and event schema are approved.

## Recommended ownership

Use one public realtime endpoint owned by `trans-api`. The browser should not
open sockets to `PDF-extractor`, `trans-flow`, or `document-builder`.
`trans-api` already owns persistent process state and can publish a consistent
view across all stages.

Before committing to WebSocket, record why bidirectional transport is needed.
If monitoring is strictly server-to-client, compare WebSocket with SSE. If the
product requirement remains WebSocket, define the contract below.

## Required server contract

- public endpoint and protocol version, for example `/api/v1/ws`;
- origin checks and TLS requirements;
- authentication mechanism; do not put a long-lived bearer token in a URL;
- authorization for each subscribed `bookId`;
- subscribe/unsubscribe commands and subscription limits;
- heartbeat/ping behavior and idle timeout;
- maximum frame size, rate limits, and backpressure behavior;
- monotonically usable event cursor or sequence number;
- ordering and duplicate-delivery guarantees;
- resume/replay behavior after reconnect;
- retention window and response when a cursor is too old;
- versioned event schema and compatibility policy;
- graceful server shutdown/redeploy signal;
- documented polling fallback using
  `GET /api/v1/books/{bookId}/processes?targetLanguage=...`.

## Proposed event envelope

This is a discussion draft, not an implementation contract:

```json
{
  "schemaVersion": 1,
  "eventId": "opaque-monotonic-cursor",
  "type": "translation.progress.changed",
  "occurredAt": "2026-08-20T12:00:00Z",
  "bookId": 42,
  "processId": 11,
  "payload": {}
}
```

Required event families should cover:

- initial authorized snapshot;
- extraction status changes;
- translation count/progress changes;
- build status changes;
- `FAILED`, retry, and recovery transitions;
- translated PDF availability;
- permission/subscription errors;
- resync required.

## Required frontend service behavior

Define an interface before implementation that owns:

- exactly one connection per browser tab/application instance;
- typed subscriptions independent from UI components;
- connection states: disconnected, connecting, connected, reconnecting,
  degraded-to-polling, and unauthorized;
- exponential backoff with jitter and an upper bound;
- cursor persistence and duplicate suppression;
- visibility/network-awareness without missing events;
- snapshot-first reconciliation: HTTP truth wins over an isolated event;
- cleanup on unsubscribe/logout and protection from stale component updates;
- telemetry for reconnects, gaps, malformed events, and fallback usage.

UI components must consume a typed monitoring store/service. They must not call
the browser `WebSocket` constructor directly.

## Questions blocking implementation

1. Does `trans-api` implement WebSocket, SSE, or both?
2. Which backend transaction publishes each event, and is delivery durable?
3. How does a client resume after missing events?
4. What is the authentication/session model?
5. What update rate is expected for large books and concurrent users?
6. Is polling an accepted permanent fallback or emergency degradation only?
7. When is the translated PDF download URL announced and how long is it valid?
