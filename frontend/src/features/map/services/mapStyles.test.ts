import { describe, expect, it } from 'vitest'

import { RISK_DISPLAY } from '../../risk/services/riskDisplay'
import { checkpointMarkerStyle, heatmapCellStyle, heatmapRadiusMeters } from './mapStyles'

describe('heatmap', () => {
  it('uses a radius of half the checkpoint interval', () => {
    expect(heatmapRadiusMeters(25)).toBeCloseTo(20_116.8)
    expect(heatmapRadiusMeters(10)).toBeCloseTo(8_046.72)
  })

  it("colours a cell with the backend risk's colour", () => {
    expect(heatmapCellStyle('SEVERE')).toMatchObject({
      fillColor: RISK_DISPLAY.SEVERE.color,
      stroke: false,
      className: 'heatmap-cell risk-severe',
    })
  })

  it('draws unknown risk as a dashed grey cell, never in the low-risk colour', () => {
    const style = heatmapCellStyle('UNKNOWN')

    expect(style.fillColor).toBe(RISK_DISPLAY.UNKNOWN.color)
    expect(style.fillColor).not.toBe(RISK_DISPLAY.LOW.color)
    expect(style).toMatchObject({ stroke: true, dashArray: '4 4', className: 'heatmap-cell risk-unknown' })
  })
})

describe('checkpoint markers', () => {
  it('mark the selected checkpoint', () => {
    expect(checkpointMarkerStyle('HIGH', true).className).toBe('checkpoint-marker risk-high selected')
    expect(checkpointMarkerStyle('HIGH', false).className).toBe('checkpoint-marker risk-high')
  })

  it('give unknown risk a dashed outline', () => {
    expect(checkpointMarkerStyle('UNKNOWN', false).dashArray).toBe('3 2')
    expect(checkpointMarkerStyle('LOW', false).dashArray).toBeUndefined()
  })
})
