import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'

import { App } from './app/App'
import { ConfigurationError, readApiBaseUrl } from './app/config'
import { ConfigurationErrorScreen } from './shared/components/ConfigurationErrorScreen'

const root = createRoot(document.getElementById('root')!)

// Check required configuration once, at startup, and say clearly what is missing.
let configurationError: string | null = null
try {
  readApiBaseUrl()
} catch (error) {
  if (!(error instanceof ConfigurationError)) throw error
  configurationError = error.message
}

root.render(
  <StrictMode>
    {configurationError ? <ConfigurationErrorScreen message={configurationError} /> : <App />}
  </StrictMode>,
)
