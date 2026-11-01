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

/** One row of the forecast table as [at arrival, at the selected hour]. */
function row(label: string): string[] {
  const table = within(screen.getByRole('table', { name: 'Forecast at this checkpoint' }))
  const header = table.getByRole('rowheader', { name: label })
  return within(header.closest('tr')!)
    .getAllByRole('cell')
    .map((cell) => cell.textContent ?? '')
}

describe('CheckpointDetails', () => {
  it('asks the user to select a checkpoint', () => {
    renderDetails(null)

    expect(screen.getByText(/select a checkpoint on the map/i)).toBeInTheDocument()
  })

  it('compares the forecast at arrival with the forecast at the selected hour', () => {
    renderDetails(origin, 6)

    expect(screen.getByRole('heading', { name: 'Origin at 0.0 mi' })).toBeInTheDocument()
    expect(screen.getByRole('columnheader', { name: /^At arrival/ })).toHaveTextContent('Used for ranking')
    expect(screen.getByRole('columnheader', { name: /^At \+6 h/ })).toBeInTheDocument()
    expect(row('Overall risk')).toEqual(['Low', 'Severe'])
    expect(row('Wind')).toEqual(['20.0 mphLow', '12.3 mphSevere'])
    expect(row('Rain')).toEqual(['0.12 in/hrLow', '0.04 in/hrLow'])
    expect(row('Data')).toEqual(['Complete', 'Complete'])
  })

  it('shows unknown values as unavailable, never as zero or low', () => {
    renderDetails(end, 0)

    for (const factor of ['Wind', 'Rain', 'Snowfall']) {
      expect(row(factor)).toEqual(['UnavailableUnavailable', 'UnavailableUnavailable'])
    }
    expect(row('Overall risk')).toEqual(['Unavailable', 'Unavailable'])
    expect(row('Forecast for')).toEqual(['Unavailable', 'Unavailable'])
    expect(screen.getByText('Weather data is unavailable for this checkpoint.')).toBeInTheDocument()
    expect(screen.queryByText('Low')).not.toBeInTheDocument()
  })

  it('says when the selected hour has no forecast entry', () => {
    renderDetails(middle, 48)

    expect(row('Wind')).toEqual(['20.0 mphLow', 'Unavailable'])
    expect(row('Overall risk')).toEqual(['Moderate', 'Unavailable'])
    expect(
      screen.getByText('No forecast for +48 h at this checkpoint, so its risk at that hour is unknown.'),
    ).toBeInTheDocument()
  })
})
