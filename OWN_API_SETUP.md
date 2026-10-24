# Own YouTube API access (done 2026-10-25)

Google Cloud project `simple-money-life-uploader` (account kederliolandagel@gmail.com), YouTube Data API v3 enabled,
OAuth app "Simple Money Life Uploader" (External, In production), Web client with redirect URI
`https://developers.google.com/oauthplayground`. Privacy policy: PRIVACY.md.

Credentials are stored ONLY in the Composio workbench private file `/mnt/files/sml/yt_creds.json`
(`client_id`, `client_secret`, `refresh_token`). Never commit them.

## Re-authorize (if token refresh fails)
1. https://developers.google.com/oauthplayground → ⚙️ → "Use your own OAuth credentials" → client ID + secret.
2. Scopes: `https://www.googleapis.com/auth/youtube.upload https://www.googleapis.com/auth/youtube.force-ssl` → Authorize APIs → pick the Simple Money Life channel → Allow.
3. "Exchange authorization code for tokens" → send the new refresh token to Claude, who updates the workbench file.
