import { describe, expect, it } from 'vitest'

import { analysisResponse, multiRouteAnalysis } from '../../../shared/test/fixtures'
import { InvalidAnalysisResponseError, parseAnalysisResponse } from './analysisResponse'

/** A deep copy of the two-route fixture with one change applied. */
function withChange(change: (data: typeof multiRouteAnalysis) => void): unknown {
  const data = structuredClone(multiRouteAnalysis)
  change(data)
  return data
}

describe('parseAnalysisResponse', () => {
  it('accepts responses shaped like the backend serializers, including unknown weather', () => {
    expect(parseAnalysisResponse(analysisResponse)).toBe(analysisResponse)
    expect(parseAnalysisResponse(multiRouteAnalysis)).toBe(multiRouteAnalysis)
  })

  it.each([
    ['a risk level the UI does not know', (d: typeof multiRouteAnalysis) => {
      ;(d.routes[0].checkpoints[1].hourly_forecasts[3] as { final_risk: string }).final_risk = 'EXTREME'
    }],
    ['a checkpoint without its hourly series', (d: typeof multiRouteAnalysis) => {
      delete (d.routes[0].checkpoints[0] as Partial<(typeof d.routes)[0]['checkpoints'][0]>).hourly_forecasts
    }],
    ['an hourly entry without a target time', (d: typeof multiRouteAnalysis) => {
      ;(d.routes[1].checkpoints[0].hourly_forecasts[0] as { target_time: unknown }).target_time = null
    }],
    ['a checkpoint without coordinates', (d: typeof multiRouteAnalysis) => {
      ;(d.routes[0].checkpoints[2] as { latitude: unknown }).latitude = '40.0'
    }],
    ['a malformed route geometry', (d: typeof multiRouteAnalysis) => {
      ;(d.routes[1].geometry as unknown[]).push([39.7])
    }],
    ['a missing departure time', (d: typeof multiRouteAnalysis) => {
      ;(d.trip as { departure_time: unknown }).departure_time = undefined
    }],
  ])('rejects %s', (_name, change) => {
    expect(() => parseAnalysisResponse(withChange(change))).toThrow(InvalidAnalysisResponseError)
  })
})
