// Vite's client types come from "types" in tsconfig.app.json; this only types our variables.
interface ImportMetaEnv {
  /** Base URL of the Django backend, for example http://127.0.0.1:8000. Required. */
  readonly VITE_API_BASE_URL?: string
}
