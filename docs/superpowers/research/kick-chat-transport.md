# Kick chat transport research

**Checked:** 2026-10-06
**Decision:** GO — use the official Kick Public API; no browser window is required for sending chat messages.

## Findings

- Kick documents `POST https://api.kick.com/public/v1/chat` for sending a message as a user or bot.
- The endpoint requires a User Access Token with the `chat:write` scope.
- To send as a user, the request requires `broadcaster_user_id`; the moderator's account must be authorized for that channel by Kick. Authorization as a moderator alone should not be assumed to grant API permission; confirm by obtaining the required OAuth grant and performing a controlled test.
- The request body uses `{"content":"$capturar","type":"user","broadcaster_user_id":<id>}`. A successful response includes `data.is_sent` and `data.message_id`; handle `401`, `403`, and `429` distinctly.
- The message limit is 500 user-perceived characters and 2048 UTF-8 bytes. The planned message is well below those limits.
- Kick documents `GET https://api.kick.com/public/v1/channels` with a `slug` query parameter to retrieve `broadcaster_user_id`. This endpoint accepts an App Access Token, so channel lookup can use the app's `client_credentials` token without adding `channel:read` to the user's OAuth scopes.
- App Access Tokens are obtained from `POST https://id.kick.com/oauth/token` with `grant_type=client_credentials`, `client_id`, and `client_secret`.
- OAuth uses Kick's authorization server at `https://id.kick.com`. The documented authorization-code flow uses PKCE and requests scopes; token exchange documentation also lists `client_id`, `client_secret`, redirect URI, and code verifier. Refresh-token exchange is documented.
- Kick app setup requires creating a developer app, which provides a Client ID, Client Secret, and registered redirect URL. For a local-only application, use a loopback/localhost redirect as supported by the OAuth documentation.
- Official docs list HTTP 429 for chat send but do not specify a concrete per-account/per-channel posting interval on the endpoint page. The planned 305-second interval is conservative relative to this endpoint documentation; still surface 429 and honor `Retry-After` if present.

## Implementation decision

Use the documented REST API over HTTPS, not browser automation or an undocumented chat websocket. Obtain and refresh a user token with `chat:write`, send as `type: user` to the explicit broadcaster ID, and confirm `data.is_sent` before considering a send successful. Store refresh/access credentials using Windows Credential Manager. Never embed a developer Client Secret in distributed client code; for a personal local build, document the app-registration/configuration requirement and keep sensitive values in secure local storage where possible. If Kick's OAuth setup cannot securely support the local app without exposing its client secret, stop before shipping and revisit the authorization architecture.

## Sources

- Kick Chat API: https://docs.kick.com/apis/chat.md
- Kick Channels API: https://docs.kick.com/apis/channels.md
- Kick OAuth 2.1: https://docs.kick.com/getting-started/generating-tokens-oauth2-flow.md
- Kick App Setup: https://docs.kick.com/getting-started/kick-apps-setup.md
- Kick API FAQs: https://docs.kick.com/apis/faqs.md

## Remaining validation before live use

1. Create a Kick developer app with a redirect URI accepted for a local desktop flow.
2. Obtain a user grant for `chat:write` using the authorized moderator account.
3. Test one `$capturar` against the intended channel and confirm `data.is_sent` is true.
4. Confirm behavior for token refresh, missing channel authorization, and API throttling before enabling the repeating scheduler.
