import { forwardRef, useImperativeHandle, useMemo, useRef } from 'react'
import MapLibreMap, {
  Layer,
  NavigationControl,
  Source,
  type MapLayerMouseEvent,
  type MapRef,
  type ViewStateChangeEvent,
} from 'react-map-gl/maplibre'
import type { FilterSpecification, StyleSpecification } from 'maplibre-gl'
import type { Bbox, EntityType } from './api'

const PLAN_IGN = 'https://data.geopf.fr/wmts?SERVICE=WMTS&REQUEST=GetTile&VERSION=1.0.0&LAYER=GEOGRAPHICALGRIDSYSTEMS.PLANIGNV2&STYLE=normal&FORMAT=image/png&TILEMATRIXSET=PM&TILEMATRIX={z}&TILEROW={y}&TILECOL={x}'
const ORTHOPHOTO_IGN = 'https://data.geopf.fr/wmts?SERVICE=WMTS&REQUEST=GetTile&VERSION=1.0.0&LAYER=ORTHOIMAGERY.ORTHOPHOTOS&STYLE=normal&FORMAT=image/jpeg&TILEMATRIXSET=PM&TILEMATRIX={z}&TILEROW={y}&TILECOL={x}'

const BASE_STYLE: StyleSpecification = {
  version: 8,
  name: 'Immo real map v1',
  sources: {},
  layers: [{ id: 'background', type: 'background', paint: { 'background-color': '#eef1eb' } }],
}

export type MapView = { longitude: number; latitude: number; zoom: number }

export type RealMapHandle = {
  fitBounds: (bbox: Bbox) => void
  flyTo: (longitude: number, latitude: number, zoom?: number) => void
}

type Props = {
  initialView: MapView
  orthophoto: boolean
  selected: { type: EntityType; id: string } | null
  selectedOpportunity?: string | null
  onViewport: (bbox: Bbox, view: MapView) => void
  onSelect: (type: EntityType, id: string) => void
  onOpportunitySelect?: (id: string) => void
  onError: () => void
}

const RealMap = forwardRef<RealMapHandle, Props>(function RealMap({
  initialView, orthophoto, selected, selectedOpportunity, onViewport, onSelect,
  onOpportunitySelect, onError,
}, forwardedRef) {
  const mapRef = useRef<MapRef>(null)

  useImperativeHandle(forwardedRef, () => ({
    fitBounds: (bbox) => mapRef.current?.fitBounds([[bbox[0], bbox[1]], [bbox[2], bbox[3]]], { padding: 72, maxZoom: 18, duration: 700 }),
    flyTo: (longitude, latitude, zoom = 17) => mapRef.current?.flyTo({ center: [longitude, latitude], zoom, duration: 700 }),
  }))

  const selectedParcelFilter = useMemo<FilterSpecification>(() => [
    '==', ['get', 'id'], selected?.type === 'parcel' ? selected.id : '',
  ], [selected])
  const selectedBuildingFilter = useMemo<FilterSpecification>(() => [
    '==', ['get', 'id'], selected?.type === 'building' ? selected.id : '',
  ], [selected])
  const selectedOpportunityFilter = useMemo<FilterSpecification>(() => [
    '==', ['get', 'id'], selectedOpportunity ?? '',
  ], [selectedOpportunity])

  const emitViewport = (event: ViewStateChangeEvent) => {
    const bounds = event.target.getBounds()
    const center = event.target.getCenter()
    onViewport(
      [bounds.getWest(), bounds.getSouth(), bounds.getEast(), bounds.getNorth()],
      { longitude: center.lng, latitude: center.lat, zoom: event.target.getZoom() },
    )
  }

  const handleClick = (event: MapLayerMouseEvent) => {
    const feature = event.features?.[0]
    const id = feature?.properties?.id
    if (!feature || typeof id !== 'string') return
    if (feature.layer.id.startsWith('opportunit')) {
      onOpportunitySelect?.(id)
      return
    }
    onSelect(feature.layer.id.startsWith('building') ? 'building' : 'parcel', id)
  }

  return (
    <MapLibreMap
      ref={mapRef}
      initialViewState={initialView}
      mapStyle={BASE_STYLE}
      minZoom={7}
      maxZoom={22}
      onLoad={(event) => emitViewport(event as unknown as ViewStateChangeEvent)}
      onMoveEnd={emitViewport}
      onClick={handleClick}
      onError={onError}
      interactiveLayerIds={['opportunities-fill', 'parcels-fill', 'buildings-fill']}
      attributionControl={{ compact: true }}
      cursor="crosshair"
      reuseMaps
    >
      <Source
        id="ign-background"
        type="raster"
        tiles={[orthophoto ? ORTHOPHOTO_IGN : PLAN_IGN]}
        tileSize={256}
        attribution="© IGN · Géoplateforme"
      >
        <Layer id="ign-background" type="raster" minzoom={0} maxzoom={20} paint={{ 'raster-opacity': orthophoto ? 0.88 : 0.76 }} />
      </Source>
      <Source id="parcels" type="vector" tiles={['/tiles/v1/parcels/{z}/{x}/{y}.mvt']} minzoom={13} maxzoom={22} attribution="Etalab · DGFiP">
        <Layer id="parcels-fill" source-layer="parcels" type="fill" minzoom={13} paint={{ 'fill-color': '#d8e6c7', 'fill-opacity': 0.24 }} />
        <Layer id="parcels-line" source-layer="parcels" type="line" minzoom={13} paint={{ 'line-color': '#547564', 'line-width': ['interpolate', ['linear'], ['zoom'], 13, 0.4, 18, 1.4] }} />
        <Layer id="parcel-selected" source-layer="parcels" type="line" minzoom={13} filter={selectedParcelFilter} paint={{ 'line-color': '#d17b25', 'line-width': 3.5 }} />
      </Source>
      <Source id="buildings" type="vector" tiles={['/tiles/v1/buildings/{z}/{x}/{y}.mvt']} minzoom={15} maxzoom={22} attribution="Etalab · DGFiP">
        <Layer id="buildings-fill" source-layer="buildings" type="fill" minzoom={15} paint={{ 'fill-color': '#3f5d51', 'fill-opacity': 0.64 }} />
        <Layer id="buildings-line" source-layer="buildings" type="line" minzoom={16} paint={{ 'line-color': '#263e35', 'line-width': 0.6 }} />
        <Layer id="building-selected" source-layer="buildings" type="line" minzoom={15} filter={selectedBuildingFilter} paint={{ 'line-color': '#d17b25', 'line-width': 3 }} />
      </Source>
      <Source id="opportunities" type="vector" tiles={['/tiles/v1/opportunities/{z}/{x}/{y}.mvt']} minzoom={10} maxzoom={22}>
        <Layer id="opportunities-fill" source-layer="opportunities" type="fill" minzoom={10} paint={{ 'fill-color': ['interpolate', ['linear'], ['coalesce', ['get', 'score'], 0], 0, '#9ca9a2', 50, '#e3c34e', 75, '#4a8e65'], 'fill-opacity': 0.58 }} />
        <Layer id="opportunities-line" source-layer="opportunities" type="line" minzoom={10} paint={{ 'line-color': '#173f34', 'line-width': 1.4 }} />
        <Layer id="opportunity-selected" source-layer="opportunities" type="line" minzoom={10} filter={selectedOpportunityFilter} paint={{ 'line-color': '#d16c25', 'line-width': 4 }} />
      </Source>
      <NavigationControl position="bottom-right" showCompass={false} visualizePitch={false} />
    </MapLibreMap>
  )
})

export default RealMap
