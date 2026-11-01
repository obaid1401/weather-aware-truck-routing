import { AppShell } from '../shared/components/AppShell'
import { AppProviders } from './AppProviders'
import { TripAnalysisPage } from './pages/TripAnalysisPage'

export function App() {
  return (
    <AppProviders>
      <AppShell>
        <TripAnalysisPage />
      </AppShell>
    </AppProviders>
  )
}
