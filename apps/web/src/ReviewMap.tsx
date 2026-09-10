import { useEffect, useMemo, useRef } from 'react'
import MapLibreMap, { Layer, NavigationControl, Source, type MapRef } from 'react-map-gl/maplibre'
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
 * **Le fond n'est jamais le Plan IGN.** Signalé pendant la revue : « les polygones sont bons
 * mais le référentiel derrière n'est pas bon, il est décalé, c'est perturbant ». C'est exact —
 * PLANIGNV2 est un produit *cartographique*, généralisé et déplacé pour la lisibilité, pas une
 * référence géométrique. Superposer des géométries précises dessus produit un décalage visible
 * qui n'existe pas dans les données, et qui fait douter d'un appariement pourtant juste.
 *
 * Deux fonds seulement, tous deux géométriquement fiables :
 *
 * - l'**orthophoto** IGN, orthorectifiée, qui montre le bâtiment réel ;
 * - nos **propres parcelles**, servies par Martin depuis la même base que les géométries du cas,
 *   donc alignées par construction.
 *
 * Aucune décision du moteur n'est représentée. Les deux couleurs distinguent les deux objets,
 * elles ne disent rien de ce qu'il en a conclu.
 */

const ORTHOPHOTO_IGN =
  'https://data.geopf.fr/wmts?SERVICE=WMTS&REQUEST=GetTile&VERSION=1.0.0&LAYER=ORTHOIMAGERY.ORTHOPHOTOS&STYLE=normal&FORMAT=image/jpeg&TILEMATRIXSET=PM&TILEMATRIX={z}&TILEROW={y}&TILECOL={x}'

const BASE_STYLE: StyleSpecification = {
  version: 8,
  name: 'Immo review map v1',
  sources: {},
  layers: [{ id: 'background', type: 'background', paint: { 'background-color': '#eef1eb' } }],
}

/** Une source vide plutôt qu'aucune source : voir la note d'ordre de pile ci-dessous. */
const EMPTY = { type: 'FeatureCollection' as const, features: [] }

type Props = {
  leftGeoJson: string | null
  rightGeoJson: string | null
  longitude: number
  latitude: number
  /** `true` : orthophoto IGN. `false` : nos propres parcelles sur fond neutre. */
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
  const mapRef = useRef<MapRef>(null)
  const left = useMemo(() => feature(leftGeoJson), [leftGeoJson])
  const right = useMemo(() => feature(rightGeoJson), [rightGeoJson])

  // L'étendue des deux objets réunis, pour cadrer dessus.
  const bounds = useMemo(() => {
    const points: number[][] = []
    const walk = (node: unknown) => {
      if (!Array.isArray(node)) return
      if (typeof node[0] === 'number' && typeof node[1] === 'number') {
        points.push(node as number[])
        return
      }
      for (const child of node) walk(child)
    }
    for (const shape of [left, right]) if (shape) walk((shape.geometry as { coordinates: unknown }).coordinates)
    if (points.length === 0) return null
    const xs = points.map((point) => point[0])
    const ys = points.map((point) => point[1])
    return [
      [Math.min(...xs), Math.min(...ys)],
      [Math.max(...xs), Math.max(...ys)],
    ] as [[number, number], [number, number]]
  }, [left, right])

  // `initialViewState` ne s'applique qu'au montage. Comme la carte reste montée d'un cas au
  // suivant — remonter un contexte WebGL à chaque verdict serait coûteux — la caméra restait
  // sur le cas précédent pendant que les emprises, elles, changeaient.
  //
  // Cadrer sur l'étendue des deux objets plutôt qu'à un zoom fixe : un abri de 57 m² et une
  // parcelle de 3 616 m² n'appellent pas le même cadrage, et un zoom 18 imposé obligeait le
  // relecteur à dézoomer à la main — quand il y pensait.
  //
  // `duration: 0` : d'un cas à l'autre il n'y a aucune continuité à montrer, et une animation
  // ne ferait qu'attendre.
  useEffect(() => {
    const map = mapRef.current
    if (!map) return
    if (bounds) {
      // `maxZoom` évite de coller au ras d'un objet minuscule ; le padding laisse voir le
      // voisinage, qui est souvent ce qui permet de trancher.
      // Marge modérée et zoom max à 20 : sur une carte de 280 px, un bâtiment de 90 m² tenait
      // dans une trentaine de pixels au zoom 19 avec 60 px de marge de chaque côté.
      map.fitBounds(bounds, { padding: 36, maxZoom: 20, duration: 0 })
    } else {
      map.jumpTo({ center: [longitude, latitude], zoom: 18 })
    }
  }, [bounds, longitude, latitude])

  return (
    <div className="review-map">
      <MapLibreMap
        ref={mapRef}
        mapStyle={BASE_STYLE}
        initialViewState={{ longitude, latitude, zoom: 18 }}
        attributionControl={{ compact: true }}
        style={{ width: '100%', height: '100%' }}
      >
        {/* Les deux fonds restent montés en permanence et on bascule leur visibilité.
            Monter/démonter une source la place en **fin** de pile : en basculant sur
            « Parcelles », le remplissage des parcelles passait au-dessus des géométries du cas
            et n'en laissait voir que la part débordant du parcellaire — un mince trait sur un
            bord. MapLibre ne charge pas les tuiles d'une couche `visibility: none`, donc rien
            n'est téléchargé pour le fond caché, et son attribution disparaît avec lui. */}
        <Source id="review-base" type="raster" tiles={[ORTHOPHOTO_IGN]} tileSize={256} attribution="IGN · Géoplateforme">
          <Layer id="review-base-layer" type="raster" layout={{ visibility: orthophoto ? 'visible' : 'none' }} />
        </Source>
        <Source id="review-parcels" type="vector" tiles={['/tiles/v1/parcels/{z}/{x}/{y}.mvt']} minzoom={13} maxzoom={22} attribution="Etalab · DGFiP">
          <Layer id="review-parcels-fill" source-layer="parcels" type="fill" layout={{ visibility: orthophoto ? 'none' : 'visible' }} paint={{ 'fill-color': '#f7f8f3', 'fill-opacity': 0.9 }} />
          <Layer id="review-parcels-line" source-layer="parcels" type="line" layout={{ visibility: orthophoto ? 'none' : 'visible' }} paint={{ 'line-color': '#8b7bb8', 'line-width': 1 }} />
        </Source>

        {/* L'objet de droite dessous, celui de gauche par-dessus : sur un cas BD TOPO les deux
            emprises se recouvrent presque, et l'ordre décide de ce qu'on voit.

            Ces trois sources restent montées même sans géométrie, avec une collection vide.
            Un `{left && <Source>}` remonterait la source de gauche en fin de pile dès qu'un cas
            en apporte une après un cas qui n'en avait pas, et le contour de droite passerait
            alors dessous. */}
        <Source id="review-right" type="geojson" data={right ?? EMPTY}>
          <Layer id="review-right-fill" type="fill" paint={{ 'fill-color': '#1f8a4c', 'fill-opacity': 0.25 }} />
        </Source>
        <Source id="review-left" type="geojson" data={left ?? EMPTY}>
          <Layer id="review-left-fill" type="fill" paint={{ 'fill-color': '#b7791f', 'fill-opacity': 0.3 }} />
          <Layer id="review-left-line" type="line" paint={{ 'line-color': '#b7791f', 'line-width': 2 }} />
          <Layer id="review-left-point" type="circle" filter={['==', ['geometry-type'], 'Point']} paint={{ 'circle-radius': 7, 'circle-color': '#b7791f', 'circle-stroke-color': 'white', 'circle-stroke-width': 2 }} />
        </Source>

        {/* Le contour de droite passe **au-dessus** de la surface de gauche, en tireté large.
            Sur un cas BD TOPO correct les deux emprises sont identiques : dessiné dessous, il
            disparaissait entièrement et le relecteur ne voyait qu'une forme, sans pouvoir dire
            si la seconde était superposée ou absente. */}
        <Source id="review-right-outline" type="geojson" data={right ?? EMPTY}>
          <Layer id="review-right-line" type="line" paint={{ 'line-color': '#0d5c31', 'line-width': 3, 'line-dasharray': [2, 2] }} />
        </Source>

        <NavigationControl position="bottom-right" showCompass={false} />
      </MapLibreMap>
    </div>
  )
}
