import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { ClipboardCheck, Layers3, LoaderCircle, LogOut, Map as MapIcon, MapPin, TriangleAlert, ZoomIn } from 'lucide-react'
import {
  loadAddressContext,
  loadCommuneCoverage,
  loadEntity,
  loadSession,
  type AddressContext,
  type CommuneCoverage,
  type EntityDetail,
  type EntityType,
  type SearchResult,
  type Session,
} from './api'
import { authEnabled, signOut } from './auth'
import { CoverageBadge } from './CoverageBadge'
import RealMap, { PARCELS_MIN_ZOOM, type MapView, type RealMapHandle } from './RealMap'
import { ReviewPanel } from './review/ReviewPanel'
import { Search } from './Search'
import { AddressSheet } from './sheets/AddressSheet'
import { EntitySheet } from './sheets/EntitySheet'
import { State } from './ui'
import 'maplibre-gl/dist/maplibre-gl.css'

/**
 * Coquille de l'Explorer : navigation, carte, fiche. L'état de navigation — cadrage, fond,
 * sélection, adresse, recherche — vit dans l'URL, pour qu'un lien restitue ce qu'on regardait.
 *
 * Aucun candidat, score ni administration n'y est rendu tant qu'aucun score n'est publié ; ces
 * écrans, retirés par C4, se reprennent de l'historique (ADR-019).
 */

const DEFAULT_VIEW: MapView = { longitude: -1.6778, latitude: 48.1173, zoom: 14 }

type Selection = { type: EntityType; id: string }

/** Un paramètre absent ou vide retombe sur la valeur par défaut. `Number(null)` vaut 0 : sans
 *  ce garde, une URL nue ouvrait la carte au large du golfe de Guinée. */
function numericParam(params: URLSearchParams, key: string, fallback: number) {
  const raw = params.get(key)
  if (raw === null || raw.trim() === '') return fallback
  const value = Number(raw)
  return Number.isFinite(value) ? value : fallback
}

function initialSelection(params: URLSearchParams): Selection | null {
  const type = params.get('type')
  const id = params.get('id')
  if (id && (type === 'parcel' || type === 'building' || type === 'property_unit')) return { type, id }
  return null
}

// Une adresse a son propre paramètre d'URL, pour que `type`/`id` continuent de désigner sans
// ambiguïté une parcelle, un bâtiment ou une unité foncière.
function initialAddressId(params: URLSearchParams): string | null {
  const id = params.get('address')
  return id && id.startsWith('address:') ? id : null
}

/** Charge l'objet désigné par `id`, et l'oublie dès que `id` change. */
function useRecord<T>(id: string | null, load: (id: string, signal: AbortSignal) => Promise<T>) {
  const [state, setState] = useState<{ id: string | null; record: T | null; loading: boolean }>({ id: null, record: null, loading: false })
  useEffect(() => {
    if (!id) { setState({ id: null, record: null, loading: false }); return }
    const controller = new AbortController()
    setState({ id, record: null, loading: true })
    load(id, controller.signal)
      .then((record) => setState({ id, record, loading: false }))
      .catch((error: unknown) => {
        if ((error as Error).name !== 'AbortError') setState({ id, record: null, loading: false })
      })
    return () => controller.abort()
  }, [id, load])
  return state.id === id ? state : { id, record: null, loading: Boolean(id) }
}

const loadSelected = (key: string, signal: AbortSignal) => {
  const [type, ...rest] = key.split('|')
  return loadEntity(type as EntityType, rest.join('|'), signal)
}

function App() {
  const params = useMemo(() => new URLSearchParams(window.location.search), [])
  const mapRef = useRef<RealMapHandle>(null)
  const [view, setView] = useState<MapView>({
    longitude: numericParam(params, 'lon', DEFAULT_VIEW.longitude),
    latitude: numericParam(params, 'lat', DEFAULT_VIEW.latitude),
    zoom: numericParam(params, 'z', DEFAULT_VIEW.zoom),
  })
  const [selection, setSelection] = useState<Selection | null>(() => initialSelection(params))
  const [addressId, setAddressId] = useState<string | null>(() => initialAddressId(params))
  const [query, setQuery] = useState(params.get('q') ?? '')
  const [orthophoto, setOrthophoto] = useState(params.get('base') === 'ortho')
  const [reviewOpen, setReviewOpen] = useState(false)
  const [mapError, setMapError] = useState(false)
  // Remonter la carte est la seule façon de relancer le chargement d'une couche en échec.
  const [mapKey, setMapKey] = useState(0)
  const [session, setSession] = useState<Session | null>(null)
  const [coverage, setCoverage] = useState<CommuneCoverage | null>(null)

  const entity = useRecord<EntityDetail>(selection ? `${selection.type}|${selection.id}` : null, loadSelected)
  const address = useRecord<AddressContext>(addressId, loadAddressContext)

  // La session ne sert qu'à signer les verdicts de revue ; en local elle est absente.
  useEffect(() => {
    const controller = new AbortController()
    loadSession(controller.signal).then(setSession).catch(() => undefined)
    return () => controller.abort()
  }, [])

  useEffect(() => {
    const next = new URLSearchParams()
    next.set('lon', view.longitude.toFixed(6))
    next.set('lat', view.latitude.toFixed(6))
    next.set('z', view.zoom.toFixed(2))
    if (query) next.set('q', query)
    if (orthophoto) next.set('base', 'ortho')
    if (selection) { next.set('type', selection.type); next.set('id', selection.id) }
    if (addressId) next.set('address', addressId)
    window.history.replaceState(null, '', `${window.location.pathname}?${next}`)
  }, [view, query, orthophoto, selection, addressId])

  // La commune observée est celle de ce que l'utilisateur consulte. Sans fiche ouverte, aucune
  // couverture n'est affirmée — annoncer un état sans savoir de quel territoire on parle serait
  // pire que se taire. Pendant le chargement d'une fiche, la commune précédente est gardée : la
  // pastille la nomme, et elle ne clignote plus d'une parcelle à sa voisine (C6).
  const loadedCommune = address.record?.address.commune_code ?? entity.record?.commune_code ?? null
  const hasSheet = Boolean(selection || addressId)
  const [observedCommune, setObservedCommune] = useState<string | null>(null)
  useEffect(() => {
    if (!hasSheet) setObservedCommune(null)
    else if (loadedCommune) setObservedCommune(loadedCommune)
  }, [hasSheet, loadedCommune])
  useEffect(() => {
    if (!observedCommune) { setCoverage(null); return }
    const controller = new AbortController()
    loadCommuneCoverage(observedCommune, controller.signal)
      .then(setCoverage)
      .catch((error: unknown) => { if ((error as Error).name !== 'AbortError') setCoverage(null) })
    return () => controller.abort()
  }, [observedCommune])

  const handleViewport = useCallback((next: MapView) => setView(next), [])

  const openEntity = useCallback((type: EntityType, id: string) => { setAddressId(null); setSelection({ type, id }) }, [])
  const closeSheet = () => { setSelection(null); setAddressId(null) }

  const choose = useCallback((result: SearchResult) => {
    // Une adresse sans position ne recentre pas la carte : la recentrer sur un point arbitraire
    // ferait passer une absence pour une localisation.
    if (result.bbox) mapRef.current?.fitBounds(result.bbox)
    if (result.entity_type === 'address') { setSelection(null); setAddressId(result.id) }
    else if (result.entity_type === 'parcel') openEntity('parcel', result.id)
    else { setSelection(null); setAddressId(null) }
  }, [openEntity])

  const selectedOnMap = selection?.type === 'property_unit'
    ? { type: 'parcel' as const, id: `parcel:cadastre:${selection.id.split(':').at(-1)}` }
    : selection

  return (
    <div className={`app-shell ${hasSheet ? 'has-detail' : ''}`}>
      <aside className="sidebar" aria-label="Navigation principale">
        <div className="brand-mark" aria-hidden="true">i<span>m</span></div>
        <nav>
          <button className={`nav-item ${reviewOpen ? '' : 'active'}`} aria-current={reviewOpen ? undefined : 'page'} onClick={() => setReviewOpen(false)}><MapIcon size={20} /><span>Carte</span></button>
          <button className={`nav-item ${reviewOpen ? 'active' : ''}`} aria-current={reviewOpen ? 'page' : undefined} onClick={() => setReviewOpen(true)}><ClipboardCheck size={20} /><span>Revue</span></button>
        </nav>
        {authEnabled && <div className="sidebar-bottom"><button className="nav-item" onClick={() => void signOut()} title={session ? `Déconnecter ${session.display_name}` : undefined}><LogOut size={19} /><span>Quitter</span></button></div>}
      </aside>

      <main className="workspace">
        <header className="topbar">
          <div className="title-block"><h1>Vérification des données</h1><span>Ille-et-Vilaine · base locale</span></div>
          <Search initialQuery={query} onQueryChange={setQuery} onChoose={choose} />
          {coverage && <CoverageBadge coverage={coverage} />}
          <div className="map-mode" role="group" aria-label="Fond cartographique">
            <button aria-pressed={!orthophoto} className={!orthophoto ? 'active' : ''} onClick={() => setOrthophoto(false)}>Plan</button>
            <button aria-pressed={orthophoto} className={orthophoto ? 'active' : ''} onClick={() => setOrthophoto(true)}>Orthophoto IGN</button>
          </div>
        </header>

        <section className="explorer-grid">
          <section className="map-panel" aria-label="Carte des parcelles et bâtiments">
            <RealMap key={mapKey} ref={mapRef} initialView={view} orthophoto={orthophoto} selected={selectedOnMap} onViewport={handleViewport} onSelect={openEntity} onError={() => setMapError(true)} />
            <div className="layer-badge"><Layers3 size={15} /> Parcelles · Bâtiments</div>
            {view.zoom < PARCELS_MIN_ZOOM && <div className="map-hint" role="status"><span>Les parcelles s’affichent à partir du zoom {PARCELS_MIN_ZOOM}.</span><button onClick={() => mapRef.current?.flyTo(view.longitude, view.latitude, 16)}><ZoomIn size={14} /> Zoomer ici</button></div>}
            {mapError && <div className="map-error" role="alert"><TriangleAlert size={15} /><span>Une couche n’a pas chargé.</span><button onClick={() => { setMapError(false); setMapKey((key) => key + 1) }}>Recharger la carte</button></div>}
            <div className="source-attribution">Cadastre Etalab · DGFiP{orthophoto ? ' · Orthophoto © IGN' : ''}</div>
          </section>

          <aside className="detail-panel" aria-live="polite">
            {!hasSheet && <State icon={<MapPin />} title="Aucune fiche ouverte" text="Recherchez une adresse ou une parcelle, ou cliquez une parcelle ou un bâtiment sur la carte. La fiche montre ce que la base en contient, avec ses sources." />}
            {addressId && address.loading && <State icon={<LoaderCircle className="spin" />} title="Chargement de l’adresse" text="Récupération des entités liées et de leurs appariements." />}
            {addressId && !address.loading && !address.record && <State icon={<TriangleAlert />} title="Adresse indisponible" text="L’adresse est absente de la release active ou le service est indisponible." action={<button onClick={closeSheet}>Fermer</button>} />}
            {address.record && <AddressSheet context={address.record} onClose={closeSheet} onRelated={openEntity} />}
            {selection && entity.loading && <State icon={<LoaderCircle className="spin" />} title="Chargement de la fiche" text="Récupération du détail exact par l’API." />}
            {selection && !entity.loading && !entity.record && <State icon={<TriangleAlert />} title="Fiche indisponible" text="L’entité est absente de la release active ou le service est indisponible." action={<button onClick={closeSheet}>Fermer</button>} />}
            {entity.record && <EntitySheet key={entity.record.id} detail={entity.record} onClose={closeSheet} onRelated={openEntity} />}
          </aside>
        </section>
      </main>
      {reviewOpen && <ReviewPanel sampleId="b4-2026-09-08" reviewer={session?.display_name ?? 'relecteur'} onClose={() => setReviewOpen(false)} />}
    </div>
  )
}

export default App
