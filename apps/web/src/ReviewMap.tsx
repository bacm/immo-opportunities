import { useMemo } from 'react'
import MapLibreMap, { Layer, NavigationControl, Source } from 'react-map-gl/maplibre'
import type { StyleSpecification } from 'maplibre-gl'

/**
 * Les deux objets d'un cas de revue, sur la carte réelle.
 *
 * L'aperçu SVG répond à « ces deux formes se recouvrent-elles ? » mais pas à « où est-ce ? ».
 * La revue du 10 septembre 2026 a montré que ça ne suffit pas : sur la strate BD TOPO, la
 * moitié des cas est ressortie `undecidable` avec pour motif « je n'arrive pas à trouver le
 * bâtiment ». Un bâtiment sans adresse ni libellé n'existe pour le relecteur que s'il le voit
 * dans son environnement.
 *
 * Le fond est celui de l'Explorer, orthophoto par défaut : c'est la vue aérienne que le
 * relecteur allait chercher sur Google Maps pour chaque cas.
 *
 * Aucune décision du moteur n'est représentée. Les deux couleurs distinguent les deux objets,
 * elles ne disent rien de ce qu'il en a conclu.
 */

const ORTHOPHOTO_IGN =
  'https://data.geopf.fr/wmts?SERVICE=WMTS&REQUEST=GetTile&VERSION=1.0.0&LAYER=ORTHOIMAGERY.ORTHOPHOTOS&STYLE=normal&FORMAT=image/jpeg&TILEMATRIXSET=PM&TILEMATRIX={z}&TILEROW={y}&TILECOL={x}'
const PLAN_IGN =
  'https://data.geopf.fr/wmts?SERVICE=WMTS&REQUEST=GetTile&VERSION=1.0.0&LAYER=GEOGRAPHICALGRIDSYSTEMS.PLANIGNV2&STYLE=normal&FORMAT=image/png&TILEMATRIXSET=PM&TILEMATRIX={z}&TILEROW={y}&TILECOL={x}'

const BASE_STYLE: StyleSpecification = {
  version: 8,
  name: 'Immo review map v1',
  sources: {},
  layers: [{ id: 'background', type: 'background', paint: { 'background-color': '#eef1eb' } }],
}

type Props = {
  leftGeoJson: string | null
  rightGeoJson: string | null
  longitude: number
  latitude: number
  orthophoto: boolean
}

function feature(raw: string | null) {
  if (!raw) return null
  try {
    return { type: 'Feature' as const, properties: {}, geometry: JSON.parse(raw) as object }
  } catch {
    return null
  }
}

export default function ReviewMap({ leftGeoJson, rightGeoJson, longitude, latitude, orthophoto }: Props) {
  const left = useMemo(() => feature(leftGeoJson), [leftGeoJson])
  const right = useMemo(() => feature(rightGeoJson), [rightGeoJson])

  return (
    <div className="review-map">
      <MapLibreMap
        mapStyle={BASE_STYLE}
        initialViewState={{ longitude, latitude, zoom: 18 }}
        attributionControl={{ compact: true }}
        style={{ width: '100%', height: '100%' }}
      >
        <Source id="review-base" type="raster" tiles={[orthophoto ? ORTHOPHOTO_IGN : PLAN_IGN]} tileSize={256} attribution="IGN · Géoplateforme">
          <Layer id="review-base-layer" type="raster" />
        </Source>

        {/* L'objet de droite dessous, celui de gauche par-dessus : sur un cas BD TOPO les deux
            emprises se recouvrent presque, et l'ordre décide de ce qu'on voit. */}
        {right && <Source id="review-right" type="geojson" data={right}>
          <Layer id="review-right-fill" type="fill" paint={{ 'fill-color': '#1f8a4c', 'fill-opacity': 0.25 }} />
          <Layer id="review-right-line" type="line" paint={{ 'line-color': '#1f8a4c', 'line-width': 2 }} />
        </Source>}
        {left && <Source id="review-left" type="geojson" data={left}>
          <Layer id="review-left-fill" type="fill" paint={{ 'fill-color': '#b7791f', 'fill-opacity': 0.3 }} />
          <Layer id="review-left-line" type="line" paint={{ 'line-color': '#b7791f', 'line-width': 2 }} />
          <Layer id="review-left-point" type="circle" filter={['==', ['geometry-type'], 'Point']} paint={{ 'circle-radius': 7, 'circle-color': '#b7791f', 'circle-stroke-color': 'white', 'circle-stroke-width': 2 }} />
        </Source>}

        <NavigationControl position="bottom-right" showCompass={false} />
      </MapLibreMap>
    </div>
  )
}
