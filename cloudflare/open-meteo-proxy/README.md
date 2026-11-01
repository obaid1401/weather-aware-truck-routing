# Open-Meteo Proxy (Cloudflare Worker)

A small Cloudflare Worker that forwards the backend's hourly-forecast requests to the public Open-Meteo API. It is used in deployment when the backend's host (Render) shares its outbound IP addresses and hits Open-Meteo's per-IP limit ("Daily API request limit exceeded"). Local development calls Open-Meteo directly and does not need it.

The backend uses it when `OPEN_METEO_BASE_URL` and `OPEN_METEO_PROXY_TOKEN` are set (see the root README).

## What it accepts

It is not an open proxy. A request is forwarded only if all of these hold:

- The `X-Proxy-Token` header matches the Worker secret `PROXY_TOKEN`. This is checked first, so callers without the token learn nothing else.
- The request is `GET /v1/forecast`.
- The query has exactly the parameters the backend sends, each once: `latitude`, `longitude`, `hourly`, `timezone`, `timeformat`, `start_hour`, `end_hour`.
- `latitude` and `longitude` are comma-separated decimals in range (±90, ±180), with the same count, and at most 100 locations.
- `hourly` is exactly `wind_speed_10m,precipitation,snowfall`, `timezone` is `GMT`, `timeformat` is `unixtime`, and `start_hour`/`end_hour` are real times such as `2026-11-05T08:00`, with the start not after the end.

The request always goes to `https://api.open-meteo.com/v1/forecast`; the caller can never choose the destination. Only the validated query is sent, with the Worker's own `Accept` and `User-Agent` headers: no incoming header, and never the token. Open-Meteo's status and body are returned unchanged, with only `Content-Type` and `Retry-After` passed back. No CORS headers are added (only the backend calls it), and nothing is logged.

| Response | When |
|---|---|
| Open-Meteo's status and body | The request was forwarded (for example 200, or 429 when Open-Meteo's own limit is reached) |
| 400 | The query is not exactly what the backend sends |
| 401 | The token is missing or wrong |
| 404 / 405 | Any other path / method |
| 500 | The `PROXY_TOKEN` secret is not set |
| 502 / 504 | Open-Meteo could not be reached / did not answer within 14 seconds |

Errors use Open-Meteo's format, `{"error": true, "reason": "..."}`.

The token comparison hashes both values with SHA-256 and compares the digests with the Workers runtime's `crypto.subtle.timingSafeEqual`, so it neither stops at the first different byte nor reveals the secret's length. The tests run in Node.js, which lacks that function; there a byte-by-byte comparison without early exit is used, without a constant-time guarantee.

## Files

| File | Purpose |
|---|---|
| `src/index.js` | The Worker |
| `test/index.test.js` | Tests (Node.js built-in test runner, no dependencies) |
| `wrangler.toml` | Worker name, entry point, and compatibility date |
| `.dev.vars.example` | Template for the local secret used by `wrangler dev` |

## Tests

Requires Node.js 20 or later. From this directory:

```bash
npm test
```

Upstream calls are replaced by a stub, so the tests never contact Open-Meteo.

## Create a token

Use a long random value. In PowerShell (Windows PowerShell 5.1 or PowerShell 7):

```powershell
$rng = [System.Security.Cryptography.RandomNumberGenerator]::Create(); $bytes = New-Object byte[] 32; $rng.GetBytes($bytes); -join ($bytes | ForEach-Object { $_.ToString('x2') })
```

This prints 64 hexadecimal characters (256 random bits). Use the same value for the Worker's `PROXY_TOKEN` and the backend's `OPEN_METEO_PROXY_TOKEN`. Keep it out of the repository, chat, and logs.

## Run locally

Wrangler, Cloudflare's CLI, runs through `npx`; nothing is installed in this project.

```bash
cp .dev.vars.example .dev.vars   # Windows: copy .dev.vars.example .dev.vars; then set PROXY_TOKEN
npx wrangler@4.151.1 dev
```

The Worker runs at `http://localhost:8787`. Check it from PowerShell (replace `<token>`):

```powershell
Invoke-WebRequest "http://localhost:8787/v1/forecast?latitude=39.73920&longitude=-104.99030&hourly=wind_speed_10m,precipitation,snowfall&timezone=GMT&timeformat=unixtime&start_hour=2026-11-05T08:00&end_hour=2026-11-05T10:00" -Headers @{ "X-Proxy-Token" = "<token>" }
```

Use today's date or later for `start_hour` and `end_hour`. Without the header the answer is 401.

To try it with the backend, set `OPEN_METEO_BASE_URL=http://localhost:8787` and `OPEN_METEO_PROXY_TOKEN=<token>` in `backend/.env` (plain HTTP is accepted only for `localhost`), and remove them again afterwards.

## Deploy

1. In `wrangler.toml`, make `name` match the Worker created in the Cloudflare dashboard. Deploying replaces that Worker's code (the Hello World example).
2. Log in and store the token as a secret. Wrangler prompts for the value, so it never appears in your shell history:

   ```bash
   npx wrangler@4.151.1 login
   npx wrangler@4.151.1 secret put PROXY_TOKEN
   ```

3. Deploy:

   ```bash
   npx wrangler@4.151.1 deploy
   ```

   Wrangler prints the Worker URL, such as `https://weather-aware-truck-routing-proxy.<your-subdomain>.workers.dev`.

4. Check it: a request without the token returns 401, and the PowerShell request above (with the deployed URL and token) returns 200.
5. On Render, set `OPEN_METEO_BASE_URL` to the Worker URL and `OPEN_METEO_PROXY_TOKEN` to the token, then redeploy the backend.

To change the token later, run `secret put PROXY_TOKEN` again and update Render.

## Notes

- **Shared limits may still apply.** Open-Meteo limits requests per IP address, and Cloudflare Workers also send from addresses shared with other customers. Watch for 429 responses after deploying.
- **Terms.** Open-Meteo's free API is for non-commercial use; check its current terms for this use.
- **Cloudflare logging.** The Worker logs nothing itself. If you turn on Workers Logs or Logpush in the dashboard, check what request data they record, since requests carry the token header.
- **Free plan.** Cloudflare's free Workers plan has a daily request allowance; each backend weather batch (up to 100 locations) is one request.
