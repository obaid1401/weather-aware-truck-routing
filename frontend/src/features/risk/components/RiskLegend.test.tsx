import { render, screen, within } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { RiskLegend } from './RiskLegend'

describe('RiskLegend', () => {
  it('labels every risk level in text, including unavailable data', () => {
    render(<RiskLegend />)

    const items = within(screen.getByRole('list')).getAllByRole('listitem')
    expect(items.map((item) => item.querySelector('[data-risk]')?.textContent)).toEqual([
      'Low',
      'Moderate',
      'High',
      'Severe',
      'No travel',
      'Unavailable',
    ])
    expect(items[5]).toHaveTextContent('Never treated as low risk.')
  })
})
