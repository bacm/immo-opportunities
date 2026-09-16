import { useCallback, useEffect, useMemo, useRef, useState, type FormEvent, type KeyboardEvent } from 'react'
import {
  Building2,
  CheckCircle2,
  ClipboardCheck,
  Euro,
  ExternalLink,
  Gauge,
  Layers3,
  LoaderCircle,
  LogOut,
  Map as MapIcon,
  MapPin,
  Search,
  TriangleAlert,
  X,
  ZoomIn,
} from 'lucide-react'
import {
  loadEntity,
  loadSession,
  loadAddressContext,
  loadCaseContext,
  loadNextReviewCase,
  loadParcelEnergyAssessments,
  loadParcelTransactions,
  loadReviewProgress,
  loadReviewResults,
  submitReviewVerdict,
  loadCommuneCoverage,
  searchEntities,
  type AddressContext,
  type BlindCase,
  type CaseContext,
  type CommuneCoverage,
  type EntityDetail,
  type EntityMatch,
  type EntityType,
  type ParcelEnergyAssessment,
  type ParcelTransaction,
  type ReviewProgress,
  type SearchResult,
  type Session,
  type StratumResult,
} from './api'
import { authEnabled, signOut } from './auth'
import RealMap, { PARCELS_MIN_ZOOM, type MapView, type RealMapHandle } from './RealMap'
import ReviewMap from './ReviewMap'
import 'maplibre-gl/dist/maplibre-gl.css'

/**
 * L'Explorer est l'outil local de vérification des données du 35 (ADR-018) : on y cherche une
 * adresse ou une parcelle, on la voit sur la carte, et sa fiche montre ce que la base en dit.
 * Rien de la plateforme gelée n'y est rendu — ni candidat, ni score, ni administration.
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

// Une adresse n'est pas une entité canonique de l'Explorer : elle a son propre paramètre d'URL,
// pour que `type`/`id` continuent de désigner sans ambiguïté une parcelle, un bâtiment ou une
// unité foncière.
function initialAddressId(params: URLSearchParams): string | null {
  const id = params.get('address')
  return id && id.startsWith('address:') ? id : null
}

function formatArea(value: number | null) {
  return value === null ? 'Non disponible' : `${Math.round(value).toLocaleString('fr-FR')} m²`
}

function App() {
  const initialParams = useMemo(() => new URLSearchParams(window.location.search), [])
  const mapRef = useRef<RealMapHandle>(null)
  const searchRef = useRef<HTMLInputElement>(null)
  const [view, setView] = useState<MapView>({
    longitude: numericParam(initialParams, 'lon', DEFAULT_VIEW.longitude),
    latitude: numericParam(initialParams, 'lat', DEFAULT_VIEW.latitude),
    zoom: numericParam(initialParams, 'z', DEFAULT_VIEW.zoom),
  })
  const [selection, setSelection] = useState<Selection | null>(() => initialSelection(initialParams))
  const [addressId, setAddressId] = useState<string | null>(() => initialAddressId(initialParams))
  const [addressContext, setAddressContext] = useState<AddressContext | null>(null)
  const [addressLoading, setAddressLoading] = useState(false)
  const [coverage, setCoverage] = useState<CommuneCoverage | null>(null)
  const [reviewOpen, setReviewOpen] = useState(false)
  const [detail, setDetail] = useState<EntityDetail | null>(null)
  const [detailLoading, setDetailLoading] = useState(false)
  const [query, setQuery] = useState(initialParams.get('q') ?? '')
  const [searchResults, setSearchResults] = useState<SearchResult[]>([])
  const [searchOpen, setSearchOpen] = useState(false)
  const [activeSearchIndex, setActiveSearchIndex] = useState(0)
  const [searchLoading, setSearchLoading] = useState(false)
  const [searchError, setSearchError] = useState(false)
  const [mapError, setMapError] = useState(false)
  // Remonter la carte est la seule façon de relancer le chargement d'une couche en échec.
  const [mapKey, setMapKey] = useState(0)
  const [orthophoto, setOrthophoto] = useState(initialParams.get('base') === 'ortho')
  const [session, setSession] = useState<Session | null>(null)

  // La session ne sert qu'à signer les verdicts de revue ; en local elle est absente.
  useEffect(() => {
    const controller = new AbortController()
    loadSession(controller.signal).then(setSession).catch(() => undefined)
    return () => controller.abort()
  }, [])

  useEffect(() => {
    const handler = (event: globalThis.KeyboardEvent) => {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === 'k') {
        event.preventDefault()
        searchRef.current?.focus()
      }
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [])

  useEffect(() => {
    const next = new URLSearchParams()
    next.set('lon', view.longitude.toFixed(6))
    next.set('lat', view.latitude.toFixed(6))
    next.set('z', view.zoom.toFixed(2))
    if (query) next.set('q', query)
    if (orthophoto) next.set('base', 'ortho')
    if (selection) {
      next.set('type', selection.type)
      next.set('id', selection.id)
    }
    if (addressId) next.set('address', addressId)
    window.history.replaceState(null, '', `${window.location.pathname}?${next}`)
  }, [view, query, orthophoto, selection, addressId])

  useEffect(() => {
    const normalized = query.trim()
    if (normalized.length < 3) {
      setSearchResults([])
      setSearchLoading(false)
      setSearchError(false)
      return
    }
    const controller = new AbortController()
    const timeout = window.setTimeout(() => {
      setSearchLoading(true)
      searchEntities(normalized, controller.signal)
        .then((results) => {
          setSearchResults(results)
          setSearchError(false)
          setActiveSearchIndex(0)
        })
        .catch((error: unknown) => {
          if ((error as Error).name === 'AbortError') return
          setSearchResults([])
          setSearchError(true)
        })
        .finally(() => setSearchLoading(false))
    }, 220)
    return () => {
      window.clearTimeout(timeout)
      controller.abort()
    }
  }, [query])

  useEffect(() => {
    if (!selection) {
      setDetail(null)
      return
    }
    const controller = new AbortController()
    setDetailLoading(true)
    loadEntity(selection.type, selection.id, controller.signal)
      .then((record) => setDetail(record))
      .catch((error: unknown) => {
        if ((error as Error).name !== 'AbortError') setDetail(null)
      })
      .finally(() => setDetailLoading(false))
    return () => controller.abort()
  }, [selection])

  useEffect(() => {
    if (!addressId) {
      setAddressContext(null)
      return
    }
    const controller = new AbortController()
    setAddressLoading(true)
    loadAddressContext(addressId, controller.signal)
      .then((record) => setAddressContext(record))
      .catch((error: unknown) => {
        if ((error as Error).name !== 'AbortError') setAddressContext(null)
      })
      .finally(() => setAddressLoading(false))
    return () => controller.abort()
  }, [addressId])

  // La commune observée est celle de ce que l'utilisateur consulte : l'adresse ouverte, sinon
  // l'entité sélectionnée. Sans sélection, aucune couverture n'est affirmée — annoncer un état
  // sans savoir de quel territoire on parle serait pire que se taire.
  const observedCommune = addressContext?.address.commune_code ?? detail?.commune_code ?? null

  useEffect(() => {
    if (!observedCommune) {
      setCoverage(null)
      return
    }
    const controller = new AbortController()
    loadCommuneCoverage(observedCommune, controller.signal)
      .then((record) => setCoverage(record))
      .catch((error: unknown) => {
        if ((error as Error).name !== 'AbortError') setCoverage(null)
      })
    return () => controller.abort()
  }, [observedCommune])

  const handleViewport = useCallback((nextView: MapView) => setView(nextView), [])

  const chooseSearchResult = (result: SearchResult) => {
    setQuery(result.label)
    setSearchOpen(false)
    // Une adresse sans position ne recentre pas la carte : la recentrer sur un point arbitraire
    // ferait passer une absence pour une localisation.
    if (result.bbox) mapRef.current?.fitBounds(result.bbox)
    if (result.entity_type === 'address') {
      setAddressId(result.id)
      setSelection(null)
    } else if (result.entity_type === 'parcel') {
      setAddressId(null)
      setSelection({ type: 'parcel', id: result.id })
    } else {
      setAddressId(null)
      setSelection(null)
    }
  }

  const handleSearchKeyDown = (event: KeyboardEvent<HTMLInputElement>) => {
    if (!searchOpen && event.key === 'ArrowDown' && searchResults.length) setSearchOpen(true)
    else if (event.key === 'ArrowDown') setActiveSearchIndex((index) => Math.min(index + 1, searchResults.length - 1))
    else if (event.key === 'ArrowUp') setActiveSearchIndex((index) => Math.max(index - 1, 0))
    else if (event.key === 'Enter' && searchResults[activeSearchIndex]) chooseSearchResult(searchResults[activeSearchIndex])
    else if (event.key === 'Escape') setSearchOpen(false)
    else return
    event.preventDefault()
  }

  const closeSheet = () => {
    setSelection(null)
    setAddressId(null)
  }

  const selectedMapEntity = selection?.type === 'property_unit'
    ? { type: 'parcel' as const, id: `parcel:cadastre:${selection.id.split(':').at(-1)}` }
    : selection

  const hasSheet = Boolean(selection || addressId)
  const belowParcels = view.zoom < PARCELS_MIN_ZOOM
  const searching = query.trim().length >= 3

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
          <div className="search-wrap">
            <div className="searchbox" role="combobox" aria-expanded={searchOpen && searching} aria-haspopup="listbox" aria-controls="global-search-results">
              <Search size={17} />
              <input ref={searchRef} value={query} onChange={(event) => { setQuery(event.target.value); setSearchOpen(true) }} onFocus={() => setSearchOpen(true)} onKeyDown={handleSearchKeyDown} placeholder="Adresse ou parcelle (ex. 35238000BE0253)" aria-label="Rechercher" aria-autocomplete="list" aria-activedescendant={searchOpen && searchResults.length ? `search-${activeSearchIndex}` : undefined} />
              {searchLoading ? <LoaderCircle className="spin" size={16} aria-label="Recherche en cours" /> : query ? <button aria-label="Effacer la recherche" onClick={() => { setQuery(''); setSearchOpen(false); searchRef.current?.focus() }}><X size={15} /></button> : <kbd>⌘ K</kbd>}
            </div>
            {searchOpen && searching && (
              <div className="search-results" id="global-search-results" role="listbox">
                {searchResults.map((result, index) => (
                  <button id={`search-${index}`} role="option" aria-selected={index === activeSearchIndex} className={index === activeSearchIndex ? 'active' : ''} key={`${result.entity_type}:${result.id}`} onMouseEnter={() => setActiveSearchIndex(index)} onClick={() => chooseSearchResult(result)}>
                    {result.entity_type === 'parcel' ? <MapIcon size={16} /> : <MapPin size={16} />}<span><strong>{result.label}</strong><small>{result.secondary_label}</small></span>
                  </button>
                ))}
                {!searchLoading && searchError && <p className="inline-error">Recherche indisponible : le service local ne répond pas.</p>}
                {!searchLoading && !searchError && searchResults.length === 0 && <p>Aucune adresse ni parcelle du 35 ne correspond.</p>}
              </div>
            )}
          </div>
          <div className="map-mode" role="group" aria-label="Fond cartographique"><button aria-pressed={!orthophoto} className={!orthophoto ? 'active' : ''} onClick={() => setOrthophoto(false)}>Plan</button><button aria-pressed={orthophoto} className={orthophoto ? 'active' : ''} onClick={() => setOrthophoto(true)}>Orthophoto IGN</button></div>
        </header>

        {coverage && <CoverageBanner coverage={coverage} />}

        <section className="explorer-grid">
          <section className="map-panel" aria-label="Carte des parcelles et bâtiments">
            <RealMap key={mapKey} ref={mapRef} initialView={view} orthophoto={orthophoto} selected={selectedMapEntity} onViewport={handleViewport} onSelect={(type, id) => { setAddressId(null); setSelection({ type, id }) }} onError={() => setMapError(true)} />
            <div className="layer-badge"><Layers3 size={15} /> Parcelles · Bâtiments</div>
            {belowParcels && <div className="map-hint" role="status"><span>Les parcelles s’affichent à partir du zoom {PARCELS_MIN_ZOOM}.</span><button onClick={() => mapRef.current?.flyTo(view.longitude, view.latitude, 16)}><ZoomIn size={14} /> Zoomer ici</button></div>}
            {mapError && <div className="map-error" role="alert"><TriangleAlert size={15} /><span>Une couche n’a pas chargé.</span><button onClick={() => { setMapError(false); setMapKey((key) => key + 1) }}>Recharger la carte</button></div>}
            <div className="source-attribution">Cadastre Etalab · DGFiP{orthophoto ? ' · Orthophoto © IGN' : ''}</div>
          </section>

          <aside className="detail-panel" aria-live="polite">
            {!hasSheet && <State icon={<MapPin />} title="Aucune fiche ouverte" text="Recherchez une adresse ou une parcelle, ou cliquez une parcelle ou un bâtiment sur la carte. La fiche montre ce que la base en contient, avec ses sources." />}
            {addressId && addressLoading && !addressContext && <State icon={<LoaderCircle className="spin" />} title="Chargement de l’adresse" text="Récupération des entités liées et de leurs appariements." />}
            {addressId && !addressLoading && !addressContext && <State icon={<TriangleAlert />} title="Adresse indisponible" text="L’adresse est absente de la release active ou le service est indisponible." action={<button onClick={closeSheet}>Fermer</button>} />}
            {addressContext && <AddressSheet context={addressContext} onClose={closeSheet} onRelated={(type, id) => { setAddressId(null); setSelection({ type, id }) }} />}
            {selection && detailLoading && !detail && <State icon={<LoaderCircle className="spin" />} title="Chargement de la fiche" text="Récupération du détail exact par l’API." />}
            {selection && !detailLoading && !detail && <State icon={<TriangleAlert />} title="Fiche indisponible" text="L’entité est absente de la release active ou le service est indisponible." action={<button onClick={closeSheet}>Fermer</button>} />}
            {selection && detail && <EntitySheet detail={detail} onClose={closeSheet} onRelated={(type, id) => setSelection({ type, id })} />}
          </aside>
        </section>
      </main>
      {reviewOpen && <ReviewPanel sampleId="b4-2026-09-08" reviewer={session?.display_name ?? 'relecteur'} onClose={() => setReviewOpen(false)} />}
    </div>
  )
}

function State({ icon, title, text, action }: { icon: React.ReactNode; title: string; text: string; action?: React.ReactNode }) {
  return <div className="empty-state"><span>{icon}</span><strong>{title}</strong><p>{text}</p>{action}</div>
}

/**
 * Les mutations DVF d'une parcelle — instrument de vérification D6a, pas fonctionnalité produit.
 *
 * Le produit ne donne pas accès à l'historique des ventes d'une adresse. Ce bloc existe pour
 * qu'un humain vérifie que l'import et le rattachement tiennent, comme l'écran de
 * revue de B4 l'a fait pour les appariements — et B4 a produit trois défauts structurels qu'aucun
 * contrôle automatique n'avait vus.
 *
 * Il a d'ailleurs servi avant d'exister : la première requête a montré une « Dépendance » de
 * 382 m², dont la surface venait du terrain. 30 816 lots bâtis étaient concernés.
 *
 * **Aucun prix au m² n'est calculé ici.** Il n'existe pas en base, et le dériver à l'affichage
 * fabriquerait une valeur que rien ne justifie. Le motif de non-allocation est montré à la place :
 * 65,5 % des mutations n'ont aucun prix allouable, et ce motif est l'information.
 *
 * Chargé à la demande, jamais avec la fiche : une parcelle sur huit seulement porte une mutation,
 * et le bloc ne doit rien coûter aux sept autres.
 */
function ParcelTransactions({ parcelId }: { parcelId: string }) {
  const [rows, setRows] = useState<ParcelTransaction[] | null>(null)
  const [failed, setFailed] = useState(false)
  const [open, setOpen] = useState(false)

  useEffect(() => {
    if (!open) return
    const controller = new AbortController()
    // Vider avant de recharger. Sans cela, passer d'une parcelle à sa voisine laissait les
    // mutations de la première à l'écran : la fiche est rendue à la même place, React réutilise
    // donc l'instance et son état survit au changement de parcelle. Le garde `rows !== null`,
    // écrit pour ne pas recharger inutilement, empêchait alors toute nouvelle requête.
    //
    // Signalé sur 35024000AP0206, qui affichait les deux ventes de sa voisine AP0207 alors
    // qu'elle n'en porte qu'une. Un écran de vérification qui attribue une vente à la mauvaise
    // parcelle est pire qu'un écran absent.
    //
    // Une erreur n'est pas une absence : « aucune mutation » sur un 500 affirmerait un fait
    // que la base n'a pas dit.
    setRows(null)
    setFailed(false)
    loadParcelTransactions(parcelId, controller.signal)
      .then(setRows)
      .catch((error: unknown) => { if ((error as Error).name !== 'AbortError') setFailed(true) })
    return () => controller.abort()
  }, [open, parcelId])

  return <section className="detail-section">
    <h3>
      <button className="property-link" aria-expanded={open} onClick={() => setOpen(!open)}>
        <Euro size={15} /> {open ? 'Masquer' : 'Voir'} les mutations DVF
      </button>
    </h3>
    {open && failed && <p className="inline-error" role="alert">Mutations indisponibles : le service local n’a pas répondu. Rien n’est affirmé sur cette parcelle.</p>}
    {open && !failed && rows === null && <p className="unknown-value">Chargement…</p>}
    {open && rows !== null && rows.length === 0 &&
      <p className="unknown-value">Aucune mutation rattachée à cette parcelle.</p>}
    {open && rows !== null && rows.length > 0 && <>
      {/* Groupé par mutation, jamais ligne à ligne. Une mutation est un acte ; ses lots en sont
          le contenu. Affichés à plat, deux lots d'une même vente sur la même parcelle
          ressemblaient à deux ventes — et c'est précisément ce qu'un écran de vérification ne
          doit pas laisser croire. */}
      <div className="transaction-list">{Object.entries(
        rows.reduce<Record<string, ParcelTransaction[]>>((groups, row) => {
          (groups[row.transaction_id] ??= []).push(row)
          return groups
        }, {}),
      ).map(([transactionId, lots]) => {
        const head = lots[0]
        return <div className="transaction-row" key={transactionId}>
          <span>
            <strong>{head.mutation_date ?? 'Date inconnue'}</strong>
            <small>{head.mutation_nature ?? 'Nature inconnue'}
              {head.lot_count && head.lot_count > 1 ? ` · ${head.lot_count} lots dans l’acte` : ''}
              {head.parcel_count && head.parcel_count > 1 ? ` · ${head.parcel_count} parcelles` : ''}
            </small>
            {lots.map((lot, index) => <small key={index} className="transaction-lot">
              {lot.property_type ?? 'Type inconnu'}
              {lot.surface_m2 ? ` · ${Math.round(lot.surface_m2)} m²` : ' · surface absente'}
              {lot.allocated_price_eur !== null
                ? ` · ${Math.round(lot.allocated_price_eur).toLocaleString('fr-FR')} €`
                : ''}
            </small>)}
          </span>
          <span className={head.allocated_price_eur === null ? 'unknown-value' : undefined}>
            {head.allocated_price_eur === null
              ? <>Prix non allouable<br /><small>{head.unallocated_reason ?? 'motif absent'}</small></>
              : <>{lots.length === 1 ? 'Prix alloué' : 'Prix par lot'}</>}
          </span>
        </div>
      })}
      </div>
      <p className="detail-note">
        {rows.length} lot{rows.length > 1 ? 's' : ''} sur cette parcelle. Aucun prix au m² n’est calculé ici : il n’existe pas en base. Un prix non allouable porte
        son motif — c’est le cas de deux mutations sur trois, et c’est le résultat.
      </p>
    </>}
  </section>
}

/** Plafond d'affichage, annoncé à l'écran et jamais silencieux : une parcelle rennaise porte
 *  jusqu'à 526 diagnostics. Rendre les 526 noierait la vérification ; les couper sans le dire
 *  ferait croire à une couverture complète. Le compte total reste affiché. */
const ENERGY_ASSESSMENT_DISPLAY_LIMIT = 50

/** Compte les rattachements ambigus d'une liste **déjà chargée**. Prendre la liste en paramètre
 *  plutôt que de lire un état encore nul évite d'avoir à replier « pas de données » sur zéro :
 *  les deux se liraient « aucun rattachement ambigu », et l'un des deux serait faux. */
const countAmbiguousAttachments = (rows: ParcelEnergyAssessment[]) =>
  rows.filter((row) => row.relation_status !== 'certain').length

/**
 * Les diagnostics DPE d'une parcelle — instrument de vérification D6b, pas fonctionnalité produit.
 *
 * Symétrique du bloc DVF de D6a, et pour la même raison : 208 086 diagnostics sont en base et
 * rien ne les montrait. Ce bloc met à l'épreuve une hypothèse que rien n'a contrôlée — la
 * confiance d'appariement vaut 1,0 pour tous, parce que l'`id_rnb` est déclaré par le producteur
 * et repris tel quel. D'où la provenance de l'identifiant, montrée diagnostic par diagnostic.
 *
 * Aucune couleur de A à G, ici ni sur la carte : une classe F rendue en rouge deviendrait un
 * signal de dégradation, et une observation de diagnostic n'est pas une preuve d'état du bâti.
 * Aucune agrégation non plus — pas d'étiquette « dominante » sur la parcelle, qui fabriquerait
 * une valeur n'existant nulle part.
 */
function ParcelEnergyAssessments({ parcelId }: { parcelId: string }) {
  const [rows, setRows] = useState<ParcelEnergyAssessment[] | null>(null)
  const [failed, setFailed] = useState(false)
  const [open, setOpen] = useState(false)

  useEffect(() => {
    if (!open) return
    const controller = new AbortController()
    // Même garde que pour les mutations : la fiche est rendue à la même place d'une parcelle à
    // l'autre, React réutilise l'instance, et sans ce vidage la parcelle voisine garderait les
    // diagnostics de la précédente. Attribuer un DPE à la mauvaise parcelle est exactement ce
    // qu'un écran de vérification ne doit pas faire.
    setRows(null)
    setFailed(false)
    loadParcelEnergyAssessments(parcelId, controller.signal)
      .then(setRows)
      .catch((error: unknown) => { if ((error as Error).name !== 'AbortError') setFailed(true) })
    return () => controller.abort()
  }, [open, parcelId])

  return <section className="detail-section">
    <h3>
      <button className="property-link" aria-expanded={open} onClick={() => setOpen(!open)}>
        <Gauge size={15} /> {open ? 'Masquer' : 'Voir'} les diagnostics DPE
      </button>
    </h3>
    {open && failed && <p className="inline-error" role="alert">Diagnostics indisponibles : le service local n’a pas répondu. Rien n’est affirmé sur cette parcelle.</p>}
    {open && !failed && rows === null && <p className="unknown-value">Chargement…</p>}
    {open && rows !== null && rows.length === 0 &&
      <p className="unknown-value">Aucun diagnostic rattaché aux bâtiments de cette parcelle.</p>}
    {open && rows !== null && rows.length > 0 && <>
      {/* Les classes du bloc DVF sont réutilisées pour le style, `assessment-*` s'y ajoute pour
          que les deux blocs restent distincts à l'inspection — sans quoi un test qui compte des
          lignes compterait celles de l'autre bloc dès que les deux sont ouverts. */}
      <div className="transaction-list assessment-list">
        {rows.slice(0, ENERGY_ASSESSMENT_DISPLAY_LIMIT).map((row) => <div
          className="transaction-row assessment-row"
          key={row.dpe_number}
        >
          <span>
            <strong>{row.energy_label ?? 'Étiquette absente'}
              {row.energy_consumption_kwh_m2_year !== null
                ? ` · ${Math.round(row.energy_consumption_kwh_m2_year)} kWh/m²/an`
                : ' · consommation absente'}
            </strong>
            <small>{row.assessment_date ?? 'Date inconnue'}
              {row.building_type ? ` · ${row.building_type}` : ''}
              {/* La surface du diagnostic est montrée telle quelle. Aucun ratio n'est dérivé :
                  le produit ne juge pas un DPE, il vérifie qu'il est au bon endroit. */}
              {row.surface_habitable_m2 !== null
                ? ` · ${Math.round(row.surface_habitable_m2)} m²`
                : ' · surface non déclarée'}
            </small>
            <small>{row.address_label ?? 'Adresse du diagnostic absente'}</small>
            <small className="transaction-lot">{row.dpe_number}
              {row.building_id ? ` · ${row.building_id}` : ''}
            </small>
          </span>
          <span className={row.relation_status === 'certain' ? undefined : 'unknown-value'}>
            {row.relation_status === 'certain' ? 'Rattachement certain' : 'Rattachement ambigu'}
            <br /><small>Identifiant RNB : {row.identifier_provenance ?? 'provenance absente'}</small>
          </span>
        </div>)}
      </div>
      <p className="detail-note">
        {rows.length} diagnostic{rows.length > 1 ? 's' : ''} sur cette parcelle
        {rows.length > ENERGY_ASSESSMENT_DISPLAY_LIMIT
          ? `, dont ${ENERGY_ASSESSMENT_DISPLAY_LIMIT} affichés`
          : ''}
        {countAmbiguousAttachments(rows) > 0
          ? ` · ${countAmbiguousAttachments(rows)} par un bâtiment qui chevauche plusieurs parcelles`
          : ''}. Les diagnostics rattachés à la seule adresse n’apparaissent pas ici : la relation
        adresse ↔ parcelle n’est vérifiable par aucune règle géométrique, et l’inventer placerait
        un diagnostic sur environ une parcelle sur quatre à tort. Une étiquette est l’observation
        d’un diagnostic déposé, pas une preuve d’état du bâti.
      </p>
    </>}
  </section>
}

function EntitySheet({ detail, onClose, onRelated }: { detail: EntityDetail; onClose: () => void; onRelated: (type: EntityType, id: string) => void }) {
  const kind = detail.entity_type === 'building' ? 'Bâtiment' : detail.entity_type === 'property_unit' ? 'Unité foncière' : 'Parcelle'
  // Les deux blocs de vérification — mutations D6a et diagnostics D6b — s'ancrent sur la même
  // parcelle cadastrale. Nommée une fois ici plutôt que reconstruite dans chaque bloc.
  const isParcelLike = detail.entity_type === 'parcel' || detail.entity_type === 'property_unit'
  const parcelId = detail.entity_type === 'parcel' ? detail.id : String(detail.properties.parcel_id ?? detail.id)
  return <>
    <div className="detail-actions"><span className="eyebrow">{kind.toUpperCase()}</span><button className="icon-button" onClick={onClose} aria-label="Fermer la fiche"><X size={17} /></button></div>
    <div className="detail-scroll">
      <header className="detail-header"><span className="entity-icon">{detail.entity_type === 'building' ? <Building2 size={24} /> : <MapIcon size={24} />}</span><div><h2>{detail.label}</h2><p>{detail.commune_name ?? detail.commune_code} · {detail.department_code}</p></div></header>
      <section className="detail-section"><h3>Géométrie active</h3><dl className="facts"><div><dt>Surface calculée</dt><dd>{formatArea(detail.area_m2)}</dd></div><div><dt>Identifiant stable</dt><dd>{detail.id}</dd></div><div><dt>Commune INSEE</dt><dd>{detail.commune_code ?? 'Non disponible'}</dd></div></dl></section>
      {Object.keys(detail.properties).length > 0 && <section className="detail-section"><h3>Attributs</h3><dl className="facts">{Object.entries(detail.properties).map(([key, value]) => <div key={key}><dt>{key.replaceAll('_', ' ')}</dt><dd>{value === null ? 'Non disponible' : String(value)}</dd></div>)}</dl></section>}
      {detail.related_entities.length > 0 && <section className="detail-section"><h3>Entités liées</h3><div className="related-list">{detail.related_entities.map((entity) => <button key={`${entity.entity_type}:${entity.id}`} onClick={() => onRelated(entity.entity_type, entity.id)}>{entity.entity_type === 'building' ? <Building2 size={15} /> : <MapIcon size={15} />}<span>{entity.label}</span></button>)}</div></section>}
      {isParcelLike && <ParcelTransactions parcelId={parcelId} />}
      {isParcelLike && <ParcelEnergyAssessments parcelId={parcelId} />}
      <section className="detail-section"><h3>Provenance</h3>{detail.sources.map((source, index) => <div className="source-row" key={`${source.data_source_id}:${index}`}><ExternalLink size={15} /><span><strong>{source.data_source_id}</strong><small>{source.producer ?? 'Producteur documenté'}{source.release_id ? ` · ${source.release_id}` : ''}</small></span></div>)}</section>
    </div>
  </>
}

/**
 * État de couverture du territoire observé.
 *
 * La distinction que porte ce composant est une exigence produit, pas un détail d'affichage :
 * « territoire non couvert » et « aucun résultat » se ressemblent à l'écran et signifient le
 * contraire l'un de l'autre. Confondre les deux ferait lire une fiche vide comme un fait, alors
 * que le territoire n'a jamais été importé.
 *
 * Placé au-dessus de la grille, il est partagé par la carte et la fiche.
 */
function CoverageBanner({ coverage }: { coverage: CommuneCoverage }) {
  const territory = coverage.commune_name ?? coverage.commune_code
  if (coverage.state === 'covered') {
    return <div className="coverage-banner covered" role="status">
      <CheckCircle2 size={15} />
      <span><strong>{territory} · territoire couvert</strong><small>Les cinq sources du référentiel spatial sont actives ici. Une fiche sans rattachement signifie que la base n’en connaît aucun.</small></span>
    </div>
  }
  if (coverage.state === 'not_covered') {
    return <div className="coverage-banner not-covered" role="status">
      <TriangleAlert size={15} />
      <span><strong>{territory} · territoire non couvert</strong><small>Aucune source active sur ce territoire. Une fiche vide ne veut rien dire ici : la donnée n’a pas été importée.</small></span>
    </div>
  }
  return <div className="coverage-banner partial" role="status">
    <TriangleAlert size={15} />
    <span><strong>{territory} · données partielles</strong><small>Rattachements incomplets. Sources absentes : {coverage.missing_sources.join(', ')}.</small></span>
  </div>
}

/**
 * Fiche d'une adresse : sa position quand elle en a une, et les entités auxquelles elle se
 * rattache — chacune avec la méthode, la confiance et la décision de son appariement.
 *
 * Trois exigences de FR-001 et FR-007 gouvernent ce rendu :
 *
 * - une adresse **sans position** s'affiche avec son motif, et la carte ne se recentre pas ;
 * - un appariement **ambigu** est montré comme tel, jamais réduit au plus probable ;
 * - une relation **rejetée** reste visible avec sa justification : c'est une décision, pas une
 *   absence, et la masquer ferait disparaître un cas que l'utilisateur doit pouvoir juger.
 */
function AddressSheet({ context, onClose, onRelated }: { context: AddressContext; onClose: () => void; onRelated: (type: EntityType, id: string) => void }) {
  const { address, matches } = context
  const located = address.longitude !== null && address.latitude !== null
  const certain = matches.filter((match) => match.decision === 'certain')
  const ambiguous = matches.filter((match) => match.decision === 'ambiguous')
  const rejected = matches.filter((match) => match.decision === 'rejected')
  return <>
    <div className="detail-actions"><span className="eyebrow">ADRESSE</span><button className="icon-button" onClick={onClose} aria-label="Fermer la fiche"><X size={17} /></button></div>
    <div className="detail-scroll">
      <header className="detail-header"><span className="entity-icon"><MapPin size={24} /></span><div><h2>{address.display_label}</h2><p>{address.commune_code} · {address.department_code}</p></div></header>
      <section className="detail-section">
        <h3>Position</h3>
        <dl className="facts">
          <div><dt>État</dt><dd>{located ? 'Localisée' : `Non localisée · ${address.position_status}`}</dd></div>
          <div><dt>Identifiant stable</dt><dd>{address.id}</dd></div>
        </dl>
        {!located && <p className="detail-note">Cette adresse existe dans la release mais sa position est inutilisable. Elle n’entre dans aucune relation spatiale et la carte n’a pas été recentrée.</p>}
      </section>
      {matches.length === 0 && <section className="detail-section"><h3>Entités liées</h3><p className="detail-note">Aucun appariement pour cette adresse dans la release active. C’est une absence, pas un rejet : rien ne permet de la rattacher, et rien ne l’en empêche formellement.</p></section>}
      {[['Appariements certains', certain], ['Appariements ambigus', ambiguous], ['Relations rejetées', rejected]].map(([title, group]) => {
        const list = group as EntityMatch[]
        if (!list.length) return null
        return <section className="detail-section" key={title as string}>
          <h3>{title as string}</h3>
          {list.map((match) => <div className="match-row" key={match.id}>
            <button onClick={() => onRelated(match.right_entity_type as EntityType, match.right_entity_id)}>
              <MapIcon size={15} /><span>{match.right_entity_id}</span>
            </button>
            <dl className="facts">
              <div><dt>Méthode</dt><dd>{match.method}</dd></div>
              <div><dt>Confiance</dt><dd>{match.confidence}</dd></div>
              <div><dt>Décision</dt><dd>{match.decision}</dd></div>
              <div><dt>Justification</dt><dd>{match.rationale}</dd></div>
              <div><dt>Releases</dt><dd>{match.release_ids.join(', ')}</dd></div>
            </dl>
          </div>)}
        </section>
      })}
    </div>
  </>
}

/**
 * Les deux objets du cas, superposés à la même échelle.
 *
 * L'écran précédent centrait la carte sur **un seul** des deux et laissait deviner l'autre :
 * un décalage se lisait alors comme un signal, alors qu'il ne disait rien. Ici les deux formes
 * sont dessinées ensemble, dans le même repère, avec une échelle — la question « se
 * correspondent-elles ? » devient regardable.
 *
 * Montrer où sont les objets n'est pas montrer ce que le moteur en a conclu : la décision et la
 * confiance restent absentes de la réponse d'API.
 */
function CasePreview({ leftGeoJson, rightGeoJson }: { leftGeoJson: string | null; rightGeoJson: string | null }) {
  const shapes = useMemo(() => {
    const collect = (raw: string | null): number[][][] => {
      if (!raw) return []
      try {
        const parsed = JSON.parse(raw) as { type: string; coordinates: unknown }
        const rings: number[][][] = []
        const walk = (node: unknown, depth: number) => {
          if (!Array.isArray(node)) return
          if (depth === 0 && typeof node[0] === 'number') return
          if (Array.isArray(node[0]) && typeof (node[0] as unknown[])[0] === 'number') {
            rings.push(node as number[][])
            return
          }
          for (const child of node) walk(child, depth + 1)
        }
        if (parsed.type === 'Point') {
          const point = parsed.coordinates as number[]
          rings.push([point])
        } else walk(parsed.coordinates, 0)
        return rings
      } catch { return [] }
    }
    return { left: collect(leftGeoJson), right: collect(rightGeoJson) }
  }, [leftGeoJson, rightGeoJson])

  const all = [...shapes.left, ...shapes.right].flat()
  if (all.length === 0) return <p className="detail-note">Aucune géométrie exploitable pour ce cas : il faut consulter les sources directement.</p>

  const xs = all.map((point) => point[0])
  const ys = all.map((point) => point[1])
  const minX = Math.min(...xs), maxX = Math.max(...xs)
  const minY = Math.min(...ys), maxY = Math.max(...ys)
  // Marge de 12 % pour que rien ne touche le bord, et garde-fou sur un cas ponctuel où
  // l'étendue serait nulle.
  const spanX = Math.max(maxX - minX, 1e-6) * 1.24
  const spanY = Math.max(maxY - minY, 1e-6) * 1.24
  const centreX = (minX + maxX) / 2, centreY = (minY + maxY) / 2
  const span = Math.max(spanX, spanY)
  const project = (point: number[]) => [
    ((point[0] - (centreX - span / 2)) / span) * 300,
    300 - ((point[1] - (centreY - span / 2)) / span) * 300,
  ]
  // Un degré de latitude vaut ~111 km ; l'échelle affichée est donc indicative mais suffit à
  // savoir si l'on regarde 20 m ou 200 m.
  const metres = Math.round(span * 111_320)

  const draw = (rings: number[][][], className: string) => rings.map((ring, index) =>
    ring.length === 1
      ? <circle key={`${className}-${index}`} className={className} cx={project(ring[0])[0]} cy={project(ring[0])[1]} r={5} />
      : <polygon key={`${className}-${index}`} className={className} points={ring.map((point) => project(point).join(',')).join(' ')} />)

  return <figure className="case-preview">
    <svg viewBox="0 0 300 300" role="img" aria-label="Les deux objets du cas, superposés">
      {draw(shapes.right, 'shape-right')}
      {draw(shapes.left, 'shape-left')}
    </svg>
    <figcaption>
      <span className="legend-left" /> objet de gauche
      <span className="legend-right" /> objet de droite
      <em>largeur ≈ {metres} m</em>
    </figcaption>
  </figure>
}

/**
 * Écran de revue manuelle — B4.
 *
 * Le relecteur ne voit **jamais** la décision du moteur : l'API ne la lui envoie pas. Ce n'est
 * donc pas un masquage côté écran, qu'une inspection du réseau contournerait, mais une absence
 * à la source. Sans cela la revue mesurerait l'accord avec le moteur, pas l'exactitude.
 *
 * L'écran affiche ce qu'il faut pour aller regarder la donnée d'origine : les identifiants des
 * deux côtés, la commune, et un lien vers la carte au bon endroit. Le protocole demande de
 * consulter les sources, pas de trancher au jugé — d'où le champ « ce que j'ai consulté », qui
 * est obligatoire.
 */
function ReviewPanel({ sampleId, reviewer, onClose }: { sampleId: string; reviewer: string; onClose: () => void }) {
  const [progress, setProgress] = useState<ReviewProgress | null>(null)
  const [current, setCurrent] = useState<BlindCase | null>(null)
  const [context, setContext] = useState<CaseContext | null>(null)
  const [results, setResults] = useState<StratumResult[]>([])
  const [verdict, setVerdict] = useState<'correct' | 'incorrect' | 'undecidable' | ''>('')
  const [rationale, setRationale] = useState('')
  const [evidence, setEvidence] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [finished, setFinished] = useState(false)
  // Orthophoto par défaut : c'est la vue que le relecteur allait chercher ailleurs.
  const [reviewOrthophoto, setReviewOrthophoto] = useState(true)

  const refresh = useCallback(async () => {
    setError('')
    try {
      const [nextProgress, nextResults] = await Promise.all([
        loadReviewProgress(sampleId),
        loadReviewResults(sampleId),
      ])
      setProgress(nextProgress)
      setResults(nextResults)
      try {
        const nextCase = await loadNextReviewCase(sampleId)
        setCurrent(nextCase)
        setFinished(false)
        // Le voisinage lève les doutes que la seule paire ne permet pas de trancher :
        // « c'est peut-être un bis », « cette adresse couvre plusieurs parcelles ».
        try { setContext(await loadCaseContext(nextCase.id)) } catch { setContext(null) }
      } catch {
        // 404 : plus aucun cas à juger. C'est une fin normale, pas une erreur.
        setCurrent(null)
        setContext(null)
        setFinished(true)
      }
    } catch (caught) {
      setError((caught as Error).message)
    }
  }, [sampleId])

  useEffect(() => { void refresh() }, [refresh])

  const submit = async (event: FormEvent) => {
    event.preventDefault()
    if (!current || !verdict) return
    setBusy(true)
    setError('')
    try {
      await submitReviewVerdict({
        case_id: current.id, verdict, reviewer,
        rationale: rationale.trim(), evidence_consulted: evidence.trim(),
      })
      setVerdict(''); setRationale(''); setEvidence('')
      await refresh()
    } catch (caught) {
      setError((caught as Error).message)
    } finally { setBusy(false) }
  }

  const located = current && current.longitude !== null && current.latitude !== null
  const mapHref = located
    ? `/?lon=${current.longitude!.toFixed(6)}&lat=${current.latitude!.toFixed(6)}&z=18.00`
    : null
  // Le relecteur va systématiquement vérifier sur une vue aérienne : lui faire chercher le
  // lieu à la main était le principal coût par cas, et pour un bâtiment BD TOPO — qui n'a ni
  // adresse ni libellé humain — c'était tout simplement impossible.
  const aerialHref = located
    ? `https://www.google.com/maps/@${current.latitude!.toFixed(6)},${current.longitude!.toFixed(6)},19z/data=!3m1!1e3`
    : null

  // `<dialog>` ouvert par `showModal()` : le navigateur retient le focus dans la revue, rend le
  // reste inerte et ferme sur Échap — ce qu'aucun `div` ne faisait.
  const dialogRef = useRef<HTMLDialogElement>(null)
  useEffect(() => {
    const dialog = dialogRef.current
    if (dialog && !dialog.open) dialog.showModal()
  }, [])

  return <dialog ref={dialogRef} className="review-dialog" aria-labelledby="review-title" onClose={onClose}>
    <section className="admin-panel">
      <header>
        <div><span className="eyebrow">REVUE MANUELLE</span><h2 id="review-title">Échantillon {sampleId}</h2></div>
        <button className="icon-button" aria-label="Fermer la revue" onClick={() => dialogRef.current?.close()}><X size={17} /></button>
      </header>
      <div className="admin-content">
        {error && <State icon={<TriangleAlert />} title="Enregistrement impossible" text={error} />}
        {progress && <section className="detail-section">
          <h3>Avancement</h3>
          <dl className="facts">
            <div><dt>Cas jugés</dt><dd>{progress.judged_cases} / {progress.total_cases}</dd></div>
            <div><dt>Graine</dt><dd>{progress.seed}</dd></div>
            <div><dt>Protocole</dt><dd>{progress.protocol_document}</dd></div>
          </dl>
          <p className="detail-note">{progress.size_rationale}</p>
        </section>}

        {finished && <State icon={<CheckCircle2 />} title="Échantillon entièrement jugé" text="Tous les cas tirés portent un verdict. Le dépouillement par strate est ci-dessous." />}

        {current && <section className="detail-section">
          <h3>Cas {current.case_ref} · {current.territorial_stratum}</h3>
          <p className="review-question">{current.question}</p>
          <p className="detail-note">{current.purpose}</p>
          <p className="detail-note">{current.out_of_scope}</p>
          {current.longitude !== null && current.latitude !== null
            ? <>
                <ReviewMap
                  leftGeoJson={current.left_geojson} rightGeoJson={current.right_geojson}
                  longitude={current.longitude} latitude={current.latitude}
                  orthophoto={reviewOrthophoto}
                />
                <ul className="review-legend">
                  <li><span className="swatch swatch-left" /> Objet de gauche</li>
                  <li><span className="swatch swatch-right" /> Objet de droite</li>
                  {!reviewOrthophoto && <li><span className="swatch swatch-parcel" /> Parcelles — fond de plan, hors jugement</li>}
                </ul>
                {current.left_on_right_ratio !== null && current.left_on_right_ratio > 0.99 && <p className="detail-note">
                  Les deux emprises coïncident à {(current.left_on_right_ratio * 100).toFixed(0)} % :
                  une seule forme est visible, les deux contours se superposent.
                </p>}
                <div className="map-mode review-map-mode" role="group" aria-label="Fond de la carte de revue">
                  <button className={!reviewOrthophoto ? 'active' : ''} onClick={() => setReviewOrthophoto(false)}>Parcelles</button>
                  <button className={reviewOrthophoto ? 'active' : ''} onClick={() => setReviewOrthophoto(true)}>Orthophoto IGN</button>
                </div>
              </>
            : <CasePreview leftGeoJson={current.left_geojson} rightGeoJson={current.right_geojson} />}
          <dl className="facts">
            <div><dt>Commune</dt><dd>{current.commune_name ?? current.commune_code}</dd></div>
            <div><dt>Objet de gauche</dt><dd>{current.left_label}{current.left_area_m2 ? ` · ${Math.round(current.left_area_m2)} m²` : ''}</dd></div>
            <div><dt>Objet de droite</dt><dd>{current.right_label}{current.right_area_m2 ? ` · ${Math.round(current.right_area_m2)} m²` : ''}</dd></div>
            {current.left_on_right_ratio !== null && <div>
              <dt>{current.right_kind === 'building' ? 'Recouvrement des deux emprises' : 'Part de gauche sur droite'}</dt>
              <dd className={current.left_on_right_ratio < 0.1 ? 'value-warning' : undefined}>
                {(current.left_on_right_ratio * 100).toFixed(1)} %
              </dd>
            </div>}
          </dl>
          {current.left_on_right_ratio !== null && current.left_on_right_ratio < 0.1 && <p className="detail-note">
            {current.right_kind === 'building'
              ? 'Les deux emprises ne se recouvrent presque pas : ce sont vraisemblablement deux bâtiments différents.'
              : 'L’objet de gauche ne touche celui de droite que sur une fraction de sa surface. À vous de juger si cela suffit à dire qu’il y est situé — c’est exactement la question que pose ce cas.'}
          </p>}
          {current.left_on_right_ratio !== null && current.left_on_right_ratio > 0.99 && current.right_kind === 'building' && <p className="detail-note">
            Les deux emprises coïncident : à l’écran elles se superposent, et le contour tireté
            est celui de l’objet de droite.
          </p>}
          {context && context.sibling_addresses.length > 0 && <div className="case-context">
            <h4>Adresses au même numéro</h4>
            {context.sibling_addresses.length === 1
              ? <p className="detail-note">Aucun <em>bis</em> ni <em>ter</em> à ce numéro : une seule adresse y existe.</p>
              : <ul>{context.sibling_addresses.map((sibling) => <li key={sibling.display_label} className={sibling.is_case ? 'is-case' : ''}>{sibling.display_label}{sibling.repetition_index ? ` (${sibling.repetition_index})` : ''}{sibling.is_case ? ' ← le cas' : ''}</li>)}</ul>}
          </div>}
          {context && context.related_parcels.length > 1 && <div className="case-context">
            <h4>Parcelles rattachées à cette adresse</h4>
            <ul>{context.related_parcels.map((parcel) => <li key={parcel.cadastral_id} className={parcel.is_case ? 'is-case' : ''}>{parcel.cadastral_id}{parcel.area_m2 ? ` · ${Math.round(parcel.area_m2)} m²` : ''}{parcel.is_case ? ' ← le cas' : ''}</li>)}</ul>
            <p className="detail-note">Cette adresse en couvre {context.related_parcels.length}. Être l’une d’elles n’est pas une erreur.</p>
          </div>}
          {context && context.nearby_addresses.length > 0 && <div className="case-context">
            <h4>Adresses proches — repères, pas appariements</h4>
            <ul>{context.nearby_addresses.map((nearby) => <li key={nearby.display_label}>{nearby.display_label} · {Math.round(nearby.distance_m)} m</li>)}</ul>
            <p className="detail-note">Aucune n’est déclarée correspondre à cet objet. Elles servent à le situer, comme un nom de rue sur une carte.</p>
          </div>}
          <p className="detail-note review-links">
            {mapHref && <a href={mapHref} target="_blank" rel="noreferrer">Ouvrir sur la carte, zoom 18</a>}
            {aerialHref && <a href={aerialHref} target="_blank" rel="noreferrer">Vue aérienne</a>}
            {located && <span>{current.latitude!.toFixed(6)}, {current.longitude!.toFixed(6)}</span>}
          </p>

          <form className="review-form" onSubmit={submit}>
            <div className="review-verdicts" role="group" aria-label="Verdict">
              {([['correct', 'Correct'], ['incorrect', 'Incorrect'], ['undecidable', 'Indécidable']] as const).map(([value, label]) =>
                <button key={value} type="button" className={verdict === value ? 'active' : ''} onClick={() => setVerdict(value)}>{label}</button>)}
            </div>
            <label>Motif<textarea value={rationale} maxLength={2000} onChange={(event) => setRationale(event.target.value)} placeholder="Pourquoi ce verdict…" /></label>
            <label>Ce que j’ai consulté<input value={evidence} maxLength={500} onChange={(event) => setEvidence(event.target.value)} placeholder="carte, BAN, cadastre…" /></label>
            <button type="submit" disabled={busy || !verdict || rationale.trim().length < 3 || evidence.trim().length < 3}>Enregistrer et passer au suivant</button>
          </form>
          <p className="detail-note">« Indécidable » est un résultat valide. Ne pas le forcer : un cas indécidable n’est jamais compté comme correct.</p>
        </section>}

        {results.length > 0 && <section className="detail-section">
          <h3>Dépouillement par strate</h3>
          <div className="review-results">
            <table>
              <thead><tr><th>Appariement</th><th>Territoire</th><th>Tirés</th><th>Jugés</th><th>Abandonnés</th><th>Corrects</th><th>Incorrects</th><th>Indécid.</th><th>Exactitude</th></tr></thead>
              <tbody>{results.map((row) => <tr key={`${row.matching_stratum}:${row.territorial_stratum}`}>
                <td>{row.matching_stratum}</td><td>{row.territorial_stratum}</td>
                <td>{row.drawn}</td><td>{row.judged}</td>
                <td className={row.abandoned > 0 ? 'value-warning' : undefined}>{row.abandoned || '—'}</td>
                <td>{row.correct}</td>
                <td>{row.incorrect}</td><td>{row.undecidable}</td>
                <td>{row.accuracy === null ? '—' : `${(row.accuracy * 100).toFixed(1)} %`}</td>
              </tr>)}</tbody>
            </table>
          </div>
          <p className="detail-note">L’exactitude est calculée sur les seuls cas tranchés. Les indécidables ont leur colonne et ne gonflent aucun taux. Un cas abandonné n’a jamais été jugé et ne le sera pas : le motif de l’abandon est en base, et une strate abandonnée ne peut plus conclure à un taux d’erreur, seulement le constater.</p>
        </section>}
      </div>
    </section>
  </dialog>
}

export default App
