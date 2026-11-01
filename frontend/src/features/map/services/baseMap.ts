import type { LatLngExpression } from 'leaflet'

// Standard OpenStreetMap tiles, with the attribution their usage policy requires.
export const OSM_TILE_URL = 'https://tile.openstreetmap.org/{z}/{x}/{y}.png'
export const OSM_ATTRIBUTION =
  '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'

/** The contiguous United States, shown before a trip is analyzed. */
export const DEFAULT_CENTER: LatLngExpression = [39.5, -98.35]
export const DEFAULT_ZOOM = 4
