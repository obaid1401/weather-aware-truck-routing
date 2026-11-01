import { fireEvent, render } from '@testing-library/react'
import type { ComponentProps } from 'react'
import { describe, expect, it, vi } from 'vitest'

import { multiRouteAnalysis } from '../../../shared/test/fixtures'
import { RISK_DISPLAY } from '../../risk/services/riskDisplay'
import { RouteMap } from './RouteMap'

type Props = ComponentProps<typeof RouteMap>

function renderMap(overrides: Partial<Props> = {}) {
  const props: Props = {
    routes: multiRouteAnalysis.routes,
    origin: multiRouteAnalysis.origin,
    destination: multiRouteAnalysis.destination,
    selectedRouteId: 'route-1',
    selectedCheckpointId: null,
    hour: 0,
    checkpointIntervalMiles: 25,
    onSelectRoute: vi.fn(),
    onSelectCheckpoint: vi.fn(),
    ...overrides,
  }
  const view = render(<RouteMap {...props} />)
  return { ...view, props }
}

// Leaflet draws vector layers as SVG paths; their classes come from mapStyles.
const cells = (container: HTMLElement) => [...container.querySelectorAll('path.heatmap-cell')]
const riskClasses = (paths: Element[]) =>
  paths.map((path) => [...path.classList].find((c) => c.startsWith('risk-')))

describe('RouteMap', () => {
  it('draws every route, with the selected route styled differently', () => {
    const { container } = renderMap()

    expect(container.querySelectorAll('path.route-line')).toHaveLength(2)
    expect(container.querySelectorAll('path.route-line.selected')).toHaveLength(1)
  })

  it('keeps the selected route above the alternates after a route change', () => {
    const { container, rerender, props } = renderMap()

    rerender(<RouteMap {...props} selectedRouteId="route-2" />)

    const pane = (path: Element) => path.closest('.leaflet-pane:not(.leaflet-map-pane)')
    const selected = container.querySelector('path.route-line.selected')!
    const alternate = container.querySelector('path.route-line:not(.selected)')!
    expect(pane(selected)).toHaveClass('leaflet-selected-route-pane')
    expect(pane(alternate)).toHaveClass('leaflet-overlay-pane')
    expect(Number((pane(selected) as HTMLElement).style.zIndex)).toBeGreaterThan(400)
  })

  it('marks the origin and destination', () => {
    const { container } = renderMap()

    expect(container.querySelector('[title="Origin: Denver, CO, USA"]')).toBeInTheDocument()
    expect(container.querySelector('[title="Destination: Salt Lake City, UT, USA"]')).toBeInTheDocument()
  })

  it("shows the selected route's checkpoints coloured by their risk at arrival", () => {
    const { container } = renderMap()
    const markers = [...container.querySelectorAll('path.checkpoint-marker')]

    expect(riskClasses(markers)).toEqual(['risk-low', 'risk-moderate', 'risk-unknown'])
    expect(markers[1]).toHaveAttribute('fill', RISK_DISPLAY.MODERATE.color)
  })

  it('draws one heatmap circle per checkpoint, coloured by the selected hour', () => {
    const { container, rerender, props } = renderMap({ hour: 0 })

    expect(riskClasses(cells(container))).toEqual(['risk-low', 'risk-moderate', 'risk-unknown'])

    rerender(<RouteMap {...props} hour={6} />)
    // A circle whose risk changed is redrawn last, so compare without DOM order.
    expect(riskClasses(cells(container)).sort()).toEqual(['risk-moderate', 'risk-severe', 'risk-unknown'])
    expect(container.querySelector('path.heatmap-cell.risk-severe')).toHaveAttribute(
      'fill',
      RISK_DISPLAY.SEVERE.color,
    )
  })

  it('shows a missing or unknown hour as unavailable, never as low risk', () => {
    const { container } = renderMap({ hour: 48 })
    const [, missing, unknown] = cells(container)

    for (const cell of [missing, unknown]) {
      expect(cell).toHaveClass('risk-unknown')
      expect(cell).toHaveAttribute('fill', RISK_DISPLAY.UNKNOWN.color)
      expect(cell).toHaveAttribute('stroke-dasharray', '4 4')
    }
  })

  it('shows the heatmap for the selected route only', () => {
    const { container } = renderMap({ selectedRouteId: 'route-2' })

    expect(riskClasses(cells(container))).toEqual(['risk-low', 'risk-no_travel'])
  })

  it('selects a checkpoint or another route when clicked', () => {
    const { container, props } = renderMap()

    fireEvent.click(container.querySelectorAll('path.checkpoint-marker')[1])
    fireEvent.click(container.querySelector('path.route-line:not(.selected)')!)

    expect(props.onSelectCheckpoint).toHaveBeenCalledWith('route-1-cp-1')
    expect(props.onSelectRoute).toHaveBeenCalledWith('route-2')
  })

  it('credits OpenStreetMap', () => {
    const { container } = renderMap()

    expect(container.querySelector('.leaflet-control-attribution')).toHaveTextContent('OpenStreetMap')
  })
})
