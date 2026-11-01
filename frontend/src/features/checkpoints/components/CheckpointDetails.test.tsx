import { render, screen, within } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { multiRouteAnalysis } from '../../../shared/test/fixtures'
import { CheckpointDetails } from './CheckpointDetails'

const checkpoints = multiRouteAnalysis.routes[0].checkpoints
const [origin, middle, end] = checkpoints

function renderDetails(checkpoint: (typeof checkpoints)[number] | null, hour = 0) {
  render(
    <CheckpointDetails
      checkpoints={checkpoints}
      checkpoint={checkpoint}
      hour={hour}
      hourTime="2026-11-05T21:00:00Z"
    />,
  )
}

const table = (name: string) => within(screen.getByRole('table', { name }))
const row = (name: string, factor: string) => table(name).getByRole('row', { name: new RegExp(`^${factor}`) })

describe('CheckpointDetails', () => {
  it('asks the user to select a checkpoint', () => {
    renderDetails(null)

    expect(screen.getByText(/select a checkpoint on the map or in the list/i)).toBeInTheDocument()
  })

  it('shows the forecast at arrival and at the selected hour separately', () => {
    renderDetails(origin, 6)

    expect(screen.getByRole('heading', { name: 'Origin · 0.0 mi' })).toBeInTheDocument()
    expect(row('Forecast at estimated arrival', 'Wind')).toHaveTextContent('20.0 mphLow')
    expect(row('Forecast at estimated arrival', 'Rain')).toHaveTextContent('0.12 in/hrLow')
    expect(row('Forecast at +6 hours', 'Wind')).toHaveTextContent('12.3 mphSevere')
    expect(screen.getByRole('heading', { name: /^At \+6 h:/ })).toBeInTheDocument()
  })

  it('shows unknown values as unavailable, never as zero or low', () => {
    renderDetails(end, 0)

    for (const name of ['Forecast at estimated arrival', 'Forecast at +0 hours']) {
      for (const factor of ['Wind', 'Rain', 'Snowfall']) {
        expect(row(name, factor)).toHaveTextContent('UnavailableUnavailable')
      }
    }
    expect(screen.getByText('Weather data is unavailable for this checkpoint.')).toBeInTheDocument()
    expect(screen.queryByText('Low')).not.toBeInTheDocument()
  })

  it('says when the selected hour has no forecast entry', () => {
    renderDetails(middle, 48)

    expect(screen.getByText('Forecast unavailable for this hour. The risk is unknown.')).toBeInTheDocument()
    expect(screen.queryByRole('table', { name: 'Forecast at +48 hours' })).not.toBeInTheDocument()
  })
})
