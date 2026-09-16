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

/** Les parcelles ne sont servies qu'à partir de ce zoom (Martin, `minzoom`). En dessous, la carte
 *  est vide par construction, et l'Explorer doit le dire. */
export const PARCELS_MIN_ZOOM = 13

/**
 * **Pas de Plan IGN sous les vecteurs.** PLANIGNV2 est un produit *cartographique* — généralisé
 * et déplacé pour la lisibilité — pas une référence géométrique. Superposé à nos géométries il
 * produisait une translation visible (numéros de parcelle en double, décalés) qui n'existe pas
 * dans les données. Signalé sur la revue puis sur l'Explorer.
 *
 * Le fond « Parcelles » n'est donc plus un raster du tout : ce sont nos propres parcelles et
 * bâtiments vectoriels, issus de la base qui sert aussi les fiches, donc alignés par
 * construction. Seule l'orthophoto, orthorectifiée, reste un fond image acceptable.
 */
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
  onViewport: (view: MapView) => void
  onSelect: (type: EntityType, id: string) => void
  onError: () => void
}

const RealMap = forwardRef<RealMapHandle, Props>(function RealMap({
  initialView, orthophoto, selected, onViewport, onSelect, onError,
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

  const emitViewport = (event: ViewStateChangeEvent) => {
    const center = event.target.getCenter()
    onViewport({ longitude: center.lng, latitude: center.lat, zoom: event.target.getZoom() })
  }

  const handleClick = (event: MapLayerMouseEvent) => {
    const feature = event.features?.[0]
    const id = feature?.properties?.id
    if (!feature || typeof id !== 'string') return
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
      interactiveLayerIds={['parcels-fill', 'buildings-fill']}
      attributionControl={{ compact: true }}
      cursor="crosshair"
      reuseMaps
    >
      {/* Monté en permanence, masqué quand on est sur « Parcelles » : une source ajoutée
          après coup se place en fin de pile et l'orthophoto recouvrirait alors les vecteurs.
          Une couche `visibility: none` ne télécharge aucune tuile et n'affiche pas son
          attribution. */}
      <Source id="ign-background" type="raster" tiles={[ORTHOPHOTO_IGN]} tileSize={256} attribution="© IGN · Géoplateforme">
        <Layer id="ign-background" type="raster" minzoom={0} maxzoom={20} layout={{ visibility: orthophoto ? 'visible' : 'none' }} paint={{ 'raster-opacity': 0.88 }} />
      </Source>
      <Source id="parcels" type="vector" tiles={['/tiles/v1/parcels/{z}/{x}/{y}.mvt']} minzoom={PARCELS_MIN_ZOOM} maxzoom={22} attribution="Etalab · DGFiP">
        <Layer id="parcels-fill" source-layer="parcels" type="fill" minzoom={PARCELS_MIN_ZOOM} paint={{ 'fill-color': '#d8e6c7', 'fill-opacity': orthophoto ? 0.24 : 0.6 }} />
        <Layer id="parcels-line" source-layer="parcels" type="line" minzoom={PARCELS_MIN_ZOOM} paint={{ 'line-color': '#547564', 'line-width': ['interpolate', ['linear'], ['zoom'], 13, 0.4, 18, 1.4], 'line-opacity': orthophoto ? 0.9 : 1 }} />
        <Layer id="parcel-selected" source-layer="parcels" type="line" minzoom={PARCELS_MIN_ZOOM} filter={selectedParcelFilter} paint={{ 'line-color': '#d17b25', 'line-width': 3.5 }} />
      </Source>
      <Source id="buildings" type="vector" tiles={['/tiles/v1/buildings/{z}/{x}/{y}.mvt']} minzoom={15} maxzoom={22} attribution="Etalab · DGFiP">
        <Layer id="buildings-fill" source-layer="buildings" type="fill" minzoom={15} paint={{ 'fill-color': '#3f5d51', 'fill-opacity': 0.64 }} />
        <Layer id="buildings-line" source-layer="buildings" type="line" minzoom={16} paint={{ 'line-color': '#263e35', 'line-width': 0.6 }} />
        <Layer id="building-selected" source-layer="buildings" type="line" minzoom={15} filter={selectedBuildingFilter} paint={{ 'line-color': '#d17b25', 'line-width': 3 }} />
      </Source>
      <NavigationControl position="bottom-right" showCompass={false} visualizePitch={false} />
    </MapLibreMap>
  )
})

export default RealMap
