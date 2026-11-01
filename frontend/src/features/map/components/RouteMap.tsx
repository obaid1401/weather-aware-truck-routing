import 'leaflet/dist/leaflet.css'

import { divIcon, latLngBounds, type LatLngBounds, type LatLngExpression } from 'leaflet'
import { useEffect, useMemo, useRef } from 'react'
import {
  Circle,
  CircleMarker,
  MapContainer,
  Marker,
  Pane,
  Polyline,
  TileLayer,
  Tooltip,
  useMap,
} from 'react-leaflet'

import type { AnalyzedRoute, GeocodedLocation } from '../../analysis/types/api'
import { checkpointName } from '../../checkpoints/services/checkpointLabel'
import { RISK_DISPLAY } from '../../risk/services/riskDisplay'
import { forecastAtHour } from '../../weather/services/hourlyForecast'
import { tokens } from '../../../shared/theme/theme'
import { OSM_ATTRIBUTION, OSM_TILE_URL } from '../services/baseMap'
import {
  ALTERNATE_ROUTE_COLOR,
  SELECTED_ROUTE_COLOR,
  checkpointMarkerStyle,
  heatmapCellStyle,
  heatmapRadiusMeters,
} from '../services/mapStyles'

interface RouteMapProps {
  routes: AnalyzedRoute[]
  origin: GeocodedLocation
  destination: GeocodedLocation
  selectedRouteId: string
  selectedCheckpointId: string | null
  /** Hour after departure selected on the forecast slider; colours the heatmap. */
  hour: number
  checkpointIntervalMiles: number
  /** Space to keep clear at the bottom when fitting the routes, for a panel floating over the
   * map. */
  bottomInset?: number
  onSelectRoute: (routeId: string) => void
  onSelectCheckpoint: (checkpointId: string) => void
}

// Origin and destination are square, ink-coloured signs: never a risk colour, and a different
// shape from the round checkpoint markers.
function endpointIcon(letter: string) {
  return divIcon({
    className: 'route-endpoint',
    html:
      `<span style="display:flex;align-items:center;justify-content:center;width:26px;height:26px;` +
      `border-radius:4px;background:${tokens.ink};color:#fff;font:800 14px Overpass,system-ui,sans-serif;` +
      `border:2px solid #fff;box-shadow:0 1px 3px rgba(27,37,48,.45)">${letter}</span>`,
    iconSize: [26, 26],
    iconAnchor: [13, 13],
  })
}

const ORIGIN_ICON = endpointIcon('A')
const DESTINATION_ICON = endpointIcon('B')

/** Keeps every route in view and clear of the panel floating over the bottom of the map: refits
 * when that panel's height changes, until the user pans, zooms, or clicks the map themselves. */
function FitRoutes({ bounds, bottomInset }: { bounds: LatLngBounds; bottomInset: number }) {
  const map = useMap()
  const userMoved = useRef(false)

  useEffect(() => {
    const container = map.getContainer()
    const markMoved = () => {
      userMoved.current = true
    }
    const events = ['pointerdown', 'wheel', 'keydown'] as const
    events.forEach((name) => container.addEventListener(name, markMoved))
    return () => events.forEach((name) => container.removeEventListener(name, markMoved))
  }, [map])

  useEffect(() => {
    if (userMoved.current) return
    map.fitBounds(bounds, {
      paddingTopLeft: [24, 24],
      paddingBottomRight: [24, bottomInset],
      animate: false,
    })
  }, [map, bounds, bottomInset])

  return null
}

/** Routes, checkpoints, and the weather heatmap on an OpenStreetMap base map. Shows data from
 * the analysis response only: it never requests data or calculates risk. */
export function RouteMap({
  routes,
  origin,
  destination,
  selectedRouteId,
  selectedCheckpointId,
  hour,
  checkpointIntervalMiles,
  bottomInset = 24,
  onSelectRoute,
  onSelectCheckpoint,
}: RouteMapProps) {
  const selectedRoute = routes.find((route) => route.id === selectedRouteId)
  const alternates = routes.filter((route) => route !== selectedRoute)
  const originPoint: LatLngExpression = [origin.latitude, origin.longitude]
  const destinationPoint: LatLngExpression = [destination.latitude, destination.longitude]
  // Stable for one analysis, so the map is refitted only when the inset changes.
  const bounds = useMemo(
    () =>
      latLngBounds([
        [origin.latitude, origin.longitude],
        [destination.latitude, destination.longitude],
        ...routes.flatMap((r) => r.geometry),
      ]),
    [routes, origin, destination],
  )
  const radius = heatmapRadiusMeters(checkpointIntervalMiles)

  return (
    <MapContainer
      bounds={bounds}
      boundsOptions={{ paddingTopLeft: [24, 24], paddingBottomRight: [24, bottomInset] }}
      scrollWheelZoom={false}
      style={{ height: '100%', width: '100%' }}
    >
      <TileLayer url={OSM_TILE_URL} attribution={OSM_ATTRIBUTION} />
      <FitRoutes bounds={bounds} bottomInset={bottomInset} />

      {/* Heatmap below the route lines; checkpoints above them. */}
      <Pane name="weather-heatmap" style={{ zIndex: 350 }}>
        {selectedRoute?.checkpoints.map((checkpoint) => {
          const risk = forecastAtHour(checkpoint, hour)?.final_risk ?? 'UNKNOWN'
          const style = heatmapCellStyle(risk)
          return (
            <Circle
              // Leaflet sets a path's class only when the layer is created, so the circle is
              // recreated when its risk changes.
              key={`${checkpoint.id}-${risk}`}
              center={[checkpoint.latitude, checkpoint.longitude]}
              radius={radius}
              pathOptions={style}
              className={style.className}
              interactive={false}
            />
          )
        })}
      </Pane>

      {alternates.map((route) => (
        <Polyline
          key={route.id}
          positions={route.geometry}
          pathOptions={{ color: ALTERNATE_ROUTE_COLOR, weight: 4, opacity: 0.75 }}
          className="route-line"
          eventHandlers={{ click: () => onSelectRoute(route.id) }}
        >
          <Tooltip sticky>{route.label}: select to show its checkpoints</Tooltip>
        </Polyline>
      ))}
      {/* Its own pane keeps the selected route above the alternates whatever order they were
          added in (the default overlay pane is z-index 400). */}
      <Pane name="selected-route" style={{ zIndex: 420 }}>
        {selectedRoute && (
          <Polyline
            key={selectedRoute.id}
            positions={selectedRoute.geometry}
            pathOptions={{ color: SELECTED_ROUTE_COLOR, weight: 6, opacity: 0.95 }}
            className="route-line selected"
          >
            <Tooltip sticky>{selectedRoute.label} (selected)</Tooltip>
          </Polyline>
        )}
      </Pane>

      <Pane name="checkpoints" style={{ zIndex: 450 }}>
        {selectedRoute?.checkpoints.map((checkpoint) => {
          const selected = checkpoint.id === selectedCheckpointId
          const style = checkpointMarkerStyle(checkpoint.final_risk, selected)
          return (
            <CircleMarker
              key={`${checkpoint.id}-${checkpoint.final_risk}-${selected}`}
              center={[checkpoint.latitude, checkpoint.longitude]}
              radius={selected ? 9 : 6}
              pathOptions={style}
              className={style.className}
              eventHandlers={{ click: () => onSelectCheckpoint(checkpoint.id) }}
            >
              <Tooltip>
                {checkpointName(selectedRoute.checkpoints, checkpoint)}: {RISK_DISPLAY[checkpoint.final_risk].label}{' '}
                risk at arrival
              </Tooltip>
            </CircleMarker>
          )
        })}
      </Pane>

      <Marker position={originPoint} icon={ORIGIN_ICON} title={`Origin: ${origin.label}`} alt={`Origin: ${origin.label}`} />
      <Marker
        position={destinationPoint}
        icon={DESTINATION_ICON}
        title={`Destination: ${destination.label}`}
        alt={`Destination: ${destination.label}`}
      />
    </MapContainer>
  )
}
