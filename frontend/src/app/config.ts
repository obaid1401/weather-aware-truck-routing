// Runtime configuration, read from Vite environment variables (frontend/.env).
// Required values have no fallback: a missing value is reported instead of guessed.

export class ConfigurationError extends Error {}

export function readApiBaseUrl(env: ImportMetaEnv = import.meta.env): string {
  const value = env.VITE_API_BASE_URL?.trim()
  if (!value) {
    throw new ConfigurationError(
      'VITE_API_BASE_URL is not set. Add it to frontend/.env (see .env.example).',
    )
  }
  return value.replace(/\/+$/, '')
}
