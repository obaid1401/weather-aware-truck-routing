import 'leaflet/dist/leaflet.css'

import { divIcon, latLngBounds, type LatLngExpression } from 'leaflet'
import { Circle, CircleMarker, MapContainer, Marker, Pane, Polyline, TileLayer, Tooltip } from 'react-leaflet'

import type { AnalyzedRoute, GeocodedLocation } from '../../analysis/types/api'
import { checkpointName } from '../../checkpoints/services/checkpointLabel'
import { RISK_DISPLAY } from '../../risk/services/riskDisplay'
import { forecastAtHour } from '../../weather/services/hourlyForecast'
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
  onSelectRoute: (routeId: string) => void
  onSelectCheckpoint: (checkpointId: string) => void
}

const OSM_ATTRIBUTION =
  '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'

function endpointIcon(letter: string, color: string) {
  return divIcon({
    className: 'route-endpoint',
    html:
      `<span style="display:flex;align-items:center;justify-content:center;width:28px;height:28px;` +
      `border-radius:50%;background:${color};color:#fff;font:700 14px system-ui,sans-serif;` +
      `border:2px solid #fff;box-shadow:0 1px 4px rgba(0,0,0,.4)">${letter}</span>`,
    iconSize: [28, 28],
    iconAnchor: [14, 14],
  })
}

const ORIGIN_ICON = endpointIcon('A', '#2e7d32')
const DESTINATION_ICON = endpointIcon('B', '#1a2230')

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
  onSelectRoute,
  onSelectCheckpoint,
}: RouteMapProps) {
  const selectedRoute = routes.find((route) => route.id === selectedRouteId)
  const alternates = routes.filter((route) => route !== selectedRoute)
  const originPoint: LatLngExpression = [origin.latitude, origin.longitude]
  const destinationPoint: LatLngExpression = [destination.latitude, destination.longitude]
  const bounds = latLngBounds([originPoint, destinationPoint, ...routes.flatMap((r) => r.geometry)])
  const radius = heatmapRadiusMeters(checkpointIntervalMiles)

  return (
    <MapContainer
      bounds={bounds}
      boundsOptions={{ padding: [24, 24] }}
      scrollWheelZoom={false}
      style={{ height: '100%', width: '100%' }}
    >
      <TileLayer url="https://tile.openstreetmap.org/{z}/{x}/{y}.png" attribution={OSM_ATTRIBUTION} />

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
