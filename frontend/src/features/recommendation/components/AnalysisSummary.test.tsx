import { render, screen, within } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { analysisResponse } from '../../../shared/test/fixtures'
import { AnalysisSummary } from './AnalysisSummary'

afterEach(() => {
  vi.restoreAllMocks()
})

describe('AnalysisSummary', () => {
  it('shows every warning, including repeated messages, without React key warnings', () => {
    const consoleError = vi.spyOn(console, 'error').mockImplementation(() => {})
    const repeated = 'Weather data is unavailable for part of Route A.'

    render(
      <AnalysisSummary
        analysis={{
          ...analysisResponse,
          recommendation: { ...analysisResponse.recommendation!, warnings: [repeated, repeated] },
          provider_warnings: [repeated, repeated],
        }}
      />,
    )

    const lists = screen.getAllByRole('list')
    expect(lists).toHaveLength(2)
    for (const list of lists) {
      expect(within(list).getAllByText(repeated)).toHaveLength(2)
    }
    expect(consoleError).not.toHaveBeenCalled()
  })
})
