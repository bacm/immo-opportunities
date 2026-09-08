import { useCallback, useEffect, useMemo, useRef, useState, type FormEvent, type KeyboardEvent } from 'react'
import {
  Building2,
  Bookmark,
  Calculator,
  CheckCircle2,
  ChevronDown,
  CircleHelp,
  Compass,
  Database,
  ExternalLink,
  FileText,
  Heart,
  Layers3,
  LoaderCircle,
  Map as MapIcon,
  MapPin,
  Plus,
  RefreshCw,
  Search,
  Settings,
  TriangleAlert,
  X,
} from 'lucide-react'
import {
  createCandidateNote,
  createCandidateScenario,
  createSavedSearch,
  loadEntity,
  loadAdministration,
  loadOpportunities,
  loadOpportunity,
  loadSession,
  publishBrittany,
  loadAddressContext,
  searchEntities,
  updateCandidateStatus,
  withdrawBrittany,
  type Bbox,
  type CandidateWorkspace,
  type EntityDetail,
  type EntityType,
  type OpportunityDetail,
  type OpportunitySummary,
  type ScenarioRequest,
  type AddressContext,
  type EntityMatch,
  type SearchResult,
  type Session,
} from './api'
import { signOut } from './auth'
import RealMap, { type MapView, type RealMapHandle } from './RealMap'
import 'maplibre-gl/dist/maplibre-gl.css'

const DEFAULT_VIEW: MapView = { longitude: -1.6778, latitude: 48.1173, zoom: 14 }
const DEPARTMENT_VIEWS: Record<string, MapView> = {
  '22': { longitude: -2.764, latitude: 48.514, zoom: 9 },
  '29': { longitude: -4.094, latitude: 48.261, zoom: 9 },
  '35': { longitude: -1.6778, latitude: 48.1173, zoom: 10 },
  '56': { longitude: -2.759, latitude: 47.846, zoom: 9 },
}

type Selection = { type: EntityType; id: string }
type ListState = 'idle' | 'loading' | 'ready' | 'error'

function numericParam(params: URLSearchParams, key: string, fallback: number) {
  const value = Number(params.get(key))
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

function initials(name: string) {
  return name.split(/\s+/).filter(Boolean).slice(0, 2).map((part) => part[0]?.toUpperCase()).join('') || 'U'
}

function App() {
  const initialParams = useMemo(() => new URLSearchParams(window.location.search), [])
  const mapRef = useRef<RealMapHandle>(null)
  const listRef = useRef<HTMLDivElement>(null)
  const searchRef = useRef<HTMLInputElement>(null)
  const [view, setView] = useState<MapView>({
    longitude: numericParam(initialParams, 'lon', DEFAULT_VIEW.longitude),
    latitude: numericParam(initialParams, 'lat', DEFAULT_VIEW.latitude),
    zoom: numericParam(initialParams, 'z', DEFAULT_VIEW.zoom),
  })
  const [selection, setSelection] = useState<Selection | null>(() => initialSelection(initialParams))
  const [opportunityId, setOpportunityId] = useState(initialParams.get('opportunity'))
  const [addressId, setAddressId] = useState<string | null>(() => initialAddressId(initialParams))
  const [addressContext, setAddressContext] = useState<AddressContext | null>(null)
  const [addressLoading, setAddressLoading] = useState(false)
  const [detail, setDetail] = useState<EntityDetail | null>(null)
  const [detailLoading, setDetailLoading] = useState(false)
  const [query, setQuery] = useState(initialParams.get('q') ?? '')
  const [searchResults, setSearchResults] = useState<SearchResult[]>([])
  const [searchOpen, setSearchOpen] = useState(false)
  const [activeSearchIndex, setActiveSearchIndex] = useState(0)
  const [searchLoading, setSearchLoading] = useState(false)
  const [listState, setListState] = useState<ListState>('idle')
  const [opportunities, setOpportunities] = useState<OpportunitySummary[]>([])
  const [nextCursor, setNextCursor] = useState<string | null>(null)
  const [strategy, setStrategy] = useState<OpportunitySummary['strategy'] | ''>(
    initialParams.get('strategy') === 'renovation_resale' ? 'renovation_resale'
      : initialParams.get('strategy') === 'division_extension' ? 'division_extension' : '',
  )
  const [minimumScore, setMinimumScore] = useState(numericParam(initialParams, 'score', 0))
  const [confidence, setConfidence] = useState<OpportunitySummary['confidence_level'] | ''>(
    (initialParams.get('confidence') as OpportunitySummary['confidence_level'] | null) ?? '',
  )
  const [department, setDepartment] = useState(
    ['22', '29', '35', '56'].includes(initialParams.get('department') ?? '')
      ? initialParams.get('department') ?? '35' : '35',
  )
  const [listError, setListError] = useState('')
  const [mapError, setMapError] = useState(false)
  const [orthophoto, setOrthophoto] = useState(initialParams.get('base') === 'ortho')
  const [refreshKey, setRefreshKey] = useState(0)
  const [saveSearchOpen, setSaveSearchOpen] = useState(false)
  const [savedSearchName, setSavedSearchName] = useState('')
  const [savedSearchMessage, setSavedSearchMessage] = useState('')
  const [adminOpen, setAdminOpen] = useState(false)
  const [session, setSession] = useState<Session | null>(null)

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
    if (strategy) next.set('strategy', strategy)
    if (minimumScore > 0) next.set('score', String(minimumScore))
    if (confidence) next.set('confidence', confidence)
    next.set('department', department)
    if (opportunityId) next.set('opportunity', opportunityId)
    if (selection) {
      next.set('type', selection.type)
      next.set('id', selection.id)
    }
    if (addressId) next.set('address', addressId)
    window.history.replaceState(null, '', `${window.location.pathname}?${next}`)
  }, [view, query, orthophoto, selection, strategy, minimumScore, confidence, department, opportunityId, addressId])

  useEffect(() => {
    const normalized = query.trim()
    if (normalized.length < 3) {
      setSearchResults([])
      setSearchLoading(false)
      return
    }
    const controller = new AbortController()
    const timeout = window.setTimeout(() => {
      setSearchLoading(true)
      searchEntities(normalized, department, controller.signal)
        .then((results) => {
          setSearchResults(results)
          setActiveSearchIndex(0)
          setSearchOpen(true)
        })
        .catch((error: unknown) => {
          if ((error as Error).name !== 'AbortError') setSearchResults([])
        })
        .finally(() => setSearchLoading(false))
    }, 220)
    return () => {
      window.clearTimeout(timeout)
      controller.abort()
    }
  }, [query, department])

  useEffect(() => {
    const controller = new AbortController()
    const timeout = window.setTimeout(() => {
      setListState('loading')
      setListError('')
      loadOpportunities({ strategy, minimumScore, confidenceLevel: confidence, departmentCode: department }, controller.signal)
        .then((result) => {
          setOpportunities(result.items)
          setNextCursor(result.nextCursor)
          setListState('ready')
        })
        .catch((error: unknown) => {
          if ((error as Error).name === 'AbortError') return
          setListError((error as Error).message)
          setListState('error')
        })
    }, 180)
    return () => {
      window.clearTimeout(timeout)
      controller.abort()
    }
  }, [strategy, minimumScore, confidence, department, refreshKey])

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

  const handleViewport = useCallback((nextBbox: Bbox, nextView: MapView) => {
    void nextBbox
    setView(nextView)
  }, [])

  const chooseSearchResult = (result: SearchResult) => {
    setQuery(result.label)
    setSearchOpen(false)
    setOpportunityId(null)
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

  const handleListKeyDown = (event: KeyboardEvent<HTMLDivElement>) => {
    if (event.key !== 'ArrowDown' && event.key !== 'ArrowUp') return
    const buttons = [...(listRef.current?.querySelectorAll<HTMLButtonElement>('.result-card') ?? [])]
    const current = buttons.indexOf(document.activeElement as HTMLButtonElement)
    const next = event.key === 'ArrowDown' ? Math.min(current + 1, buttons.length - 1) : Math.max(current - 1, 0)
    buttons[next]?.focus()
    event.preventDefault()
  }

  const changeDepartment = (code: string) => {
    setDepartment(code)
    setSelection(null)
    setOpportunityId(null)
    const target = DEPARTMENT_VIEWS[code]
    if (target) mapRef.current?.flyTo(target.longitude, target.latitude, target.zoom)
  }

  const selectedMapEntity = selection?.type === 'property_unit'
    ? { type: 'parcel' as const, id: `parcel:cadastre:${selection.id.split(':').at(-1)}` }
    : selection

  const resultLabel = `${opportunities.length}${nextCursor ? '+' : ''} candidat${opportunities.length > 1 ? 's' : ''}`

  const loadMore = () => {
    if (!nextCursor) return
    setListState('loading')
    loadOpportunities({ strategy, minimumScore, confidenceLevel: confidence, departmentCode: department, cursor: nextCursor })
      .then((result) => {
        setOpportunities((current) => [...current, ...result.items])
        setNextCursor(result.nextCursor)
        setListState('ready')
      })
      .catch((error: unknown) => { setListError((error as Error).message); setListState('error') })
  }

  const saveSearch = async (event: FormEvent) => {
    event.preventDefault()
    if (!savedSearchName.trim()) return
    try {
      await createSavedSearch(savedSearchName, {
        strategy: strategy || null,
        minimum_score: minimumScore || null,
        confidence_level: confidence || null,
      })
      setSavedSearchMessage('Recherche sauvegardée')
      setSaveSearchOpen(false)
      setSavedSearchName('')
    } catch (caught) { setSavedSearchMessage((caught as Error).message) }
  }

  return (
    <div className={`app-shell ${opportunityId || selection ? 'has-detail' : ''}`}>
      <aside className="sidebar" aria-label="Navigation principale">
        <div className="brand-mark" title="Immo">i<span>m</span></div>
        <nav><button className="nav-item active"><Compass size={21} /><span>Explorer</span></button><button className="nav-item" onClick={() => setAdminOpen(true)}><Database size={20} /><span>Pilote</span></button></nav>
        <div className="sidebar-bottom"><button className="nav-item"><CircleHelp size={20} /><span>Aide</span></button><button className="avatar" aria-label={`Compte de ${session?.display_name ?? 'l’utilisateur'}`}>{initials(session?.display_name ?? 'Utilisateur')}</button></div>
      </aside>

      <main className="workspace">
        <header className="topbar">
          <div className="search-wrap">
            <div className="searchbox" role="combobox" aria-expanded={searchOpen} aria-haspopup="listbox" aria-controls="global-search-results">
              <Search size={18} />
              <input ref={searchRef} value={query} onChange={(event) => { setQuery(event.target.value); setSearchOpen(true) }} onFocus={() => searchResults.length && setSearchOpen(true)} onKeyDown={handleSearchKeyDown} placeholder="Adresse, commune ou parcelle…" aria-label="Rechercher" aria-autocomplete="list" aria-activedescendant={searchOpen ? `search-${activeSearchIndex}` : undefined} />
              {searchLoading ? <LoaderCircle className="spin" size={16} /> : query ? <button aria-label="Effacer la recherche" onClick={() => { setQuery(''); setSearchOpen(false) }}><X size={15} /></button> : <kbd>⌘ K</kbd>}
            </div>
            {searchOpen && query.trim().length >= 3 && (
              <div className="search-results" id="global-search-results" role="listbox">
                {searchResults.length ? searchResults.map((result, index) => (
                  <button id={`search-${index}`} role="option" aria-selected={index === activeSearchIndex} className={index === activeSearchIndex ? 'active' : ''} key={`${result.entity_type}:${result.id}`} onMouseEnter={() => setActiveSearchIndex(index)} onClick={() => chooseSearchResult(result)}>
                    {result.entity_type === 'parcel' ? <MapIcon size={16} /> : <MapPin size={16} />}<span><strong>{result.label}</strong><small>{result.secondary_label}</small></span>
                  </button>
                )) : !searchLoading && <p>Aucun résultat actif dans le {department}.</p>}
              </div>
            )}
          </div>
          <div className="top-actions"><span className="live-label"><i /> Données réelles</span><button className="icon-button" aria-label="Paramètres"><Settings size={18} /></button><button className="profile-button" onClick={() => void signOut()} title="Se déconnecter"><span>{initials(session?.display_name ?? 'Utilisateur')}</span><div><strong>{session?.display_name ?? 'Utilisateur connecté'}</strong><small>{session ? `${session.organization_name} · ${session.role}` : 'Session locale'}</small></div><ChevronDown size={14} /></button></div>
        </header>

        <section className="explorer-toolbar">
          <div><h1>Explorer</h1><span>Bretagne · département {department}</span></div>
          <div className="candidate-filters" aria-label="Filtres candidats">
            <label>Département<select aria-label="Département" value={department} onChange={(event) => changeDepartment(event.target.value)}><option value="22">22 · Côtes-d’Armor</option><option value="29">29 · Finistère</option><option value="35">35 · Ille-et-Vilaine</option><option value="56">56 · Morbihan</option></select></label>
            <label>Stratégie<select aria-label="Stratégie" value={strategy} onChange={(event) => setStrategy(event.target.value as typeof strategy)}><option value="">Toutes</option><option value="division_extension">Division / extension</option><option value="renovation_resale">Rénovation / revente</option></select></label>
            <label>Score min.<input aria-label="Score minimum" type="number" min="0" max="100" value={minimumScore} onChange={(event) => setMinimumScore(Math.min(100, Math.max(0, Number(event.target.value))))} /></label>
            <label>Confiance<select aria-label="Confiance" value={confidence} onChange={(event) => setConfidence(event.target.value as typeof confidence)}><option value="">Toutes</option><option value="high">Haute</option><option value="medium">Moyenne</option><option value="low">Faible</option></select></label>
            <button className="save-search-button" onClick={() => setSaveSearchOpen((open) => !open)}><Bookmark size={13} /> Sauvegarder</button>
          </div>
          <div className="map-mode" role="group" aria-label="Fond cartographique"><button className={!orthophoto ? 'active' : ''} onClick={() => setOrthophoto(false)}>Plan clair</button><button className={orthophoto ? 'active' : ''} onClick={() => setOrthophoto(true)}>Orthophoto IGN</button></div>
        </section>
        {saveSearchOpen && <form className="save-search-popover" onSubmit={saveSearch}><label>Nom de la recherche<input autoFocus value={savedSearchName} maxLength={160} onChange={(event) => setSavedSearchName(event.target.value)} /></label><button type="submit">Enregistrer</button></form>}
        {savedSearchMessage && <div className="toast" role="status">{savedSearchMessage}<button aria-label="Fermer le message" onClick={() => setSavedSearchMessage('')}><X size={13} /></button></div>}

        <section className="explorer-grid">
          <section className="result-panel" aria-label="Candidats publiés">
            <div className="results-heading"><div><strong>{listState === 'loading' && opportunities.length === 0 ? 'Actualisation…' : resultLabel}</strong><span>scores publiés · filtres actifs</span></div>{listState === 'loading' && <LoaderCircle className="spin" size={17} />}</div>
            <div className="result-list" ref={listRef} onKeyDown={handleListKeyDown}>
              {listState === 'loading' && opportunities.length === 0 && <State icon={<LoaderCircle className="spin" />} title="Chargement des candidats" text="La liste interroge les opportunités publiées, sans donnée simulée." />}
              {listState === 'error' && <State icon={<TriangleAlert />} title="Liste indisponible" text={listError || 'Le service peut être relancé.'} action={<button onClick={() => setRefreshKey((key) => key + 1)}><RefreshCw size={14} /> Réessayer</button>} />}
              {listState === 'ready' && opportunities.length === 0 && <State icon={<CheckCircle2 />} title="Aucun candidat publié" text="Les définitions de score doivent être validées avant qu’un candidat réel apparaisse ici. Les valeurs inconnues ne sont pas converties en zéro." />}
              {opportunities.map((opportunity) => (
                <button key={opportunity.id} className={`result-card ${opportunityId === opportunity.id ? 'selected' : ''}`} onClick={() => { setOpportunityId(opportunity.id); setSelection(null) }}>
                  <div><span className="parcel-icon"><Compass size={18} /></span><span><strong>{opportunity.property_unit_id}</strong><small>{opportunity.strategy === 'division_extension' ? 'Division / extension' : 'Rénovation / revente'} · {opportunity.segment_code}</small></span></div>
                  <dl><div><dt>Score</dt><dd>{opportunity.score === null || opportunity.score === undefined ? 'Inconnu' : `${opportunity.score.toFixed(1)} / 100`}</dd></div><div><dt>Confiance</dt><dd>{opportunity.confidence_level} · {opportunity.confidence_score.toFixed(0)}%</dd></div></dl>
                </button>
              ))}
              {nextCursor && <button className="load-more" onClick={loadMore} disabled={listState === 'loading'}><Plus size={14} /> Charger la suite</button>}
            </div>
          </section>

          <section className="map-panel" aria-label="Carte réelle des parcelles et bâtiments">
            <RealMap ref={mapRef} initialView={view} orthophoto={orthophoto} selected={selectedMapEntity} selectedOpportunity={opportunityId} onViewport={handleViewport} onSelect={(type, id) => { setOpportunityId(null); setSelection({ type, id }) }} onOpportunitySelect={(id) => { setSelection(null); setOpportunityId(id) }} onError={() => setMapError(true)} />
            <div className="layer-badge"><Layers3 size={15} /> Opportunités · Parcelles · Bâtiments</div>
            {mapError && <div className="map-error"><TriangleAlert size={15} /><span>Une couche n’a pas chargé.</span><button onClick={() => { setMapError(false); setRefreshKey((key) => key + 1) }}>Réessayer</button></div>}
            <div className="source-attribution">Cadastre Etalab · DGFiP · Fond © IGN</div>
          </section>

          <aside className="detail-panel" aria-live="polite">
            {!selection && !opportunityId && !addressId && <State icon={<MapPin />} title="Sélectionnez un candidat" text="Cliquez une opportunité dans la liste ou sur la carte pour examiner ses preuves." />}
            {!opportunityId && addressId && addressLoading && !addressContext && <State icon={<LoaderCircle className="spin" />} title="Chargement de l’adresse" text="Récupération des entités liées et de leurs appariements." />}
            {!opportunityId && addressId && !addressLoading && !addressContext && <State icon={<TriangleAlert />} title="Adresse indisponible" text="L’adresse est absente de la release active ou le service est indisponible." action={<button onClick={() => setAddressId(null)}>Fermer</button>} />}
            {!opportunityId && addressContext && <AddressSheet context={addressContext} onClose={() => setAddressId(null)} onRelated={(type, id) => { setAddressId(null); setSelection({ type, id }) }} />}
            {opportunityId && <OpportunitySheet id={opportunityId} onClose={() => setOpportunityId(null)} onProperty={(id) => { setOpportunityId(null); setSelection({ type: 'property_unit', id }) }} />}
            {!opportunityId && selection && detailLoading && !detail && <State icon={<LoaderCircle className="spin" />} title="Chargement de la fiche" text="Récupération du détail exact par l’API." />}
            {!opportunityId && selection && !detailLoading && !detail && <State icon={<TriangleAlert />} title="Fiche indisponible" text="L’entité est absente de la release active ou le service est indisponible." action={<button onClick={() => setSelection(null)}>Fermer</button>} />}
            {!opportunityId && detail && <EntitySheet detail={detail} onClose={() => setSelection(null)} onRelated={(type, id) => setSelection({ type, id })} />}
          </aside>
        </section>
      </main>
      {adminOpen && <AdminPanel session={session} onClose={() => setAdminOpen(false)} />}
    </div>
  )
}

function AdminPanel({ session, onClose }: { session: Session | null; onClose: () => void }) {
  const [data, setData] = useState<Awaited<ReturnType<typeof loadAdministration>> | null>(null)
  const [error, setError] = useState('')
  const [reason, setReason] = useState('')
  const [publishing, setPublishing] = useState(false)
  const [message, setMessage] = useState('')
  const reload = useCallback(() => {
    const controller = new AbortController()
    setError('')
    loadAdministration(controller.signal).then(setData).catch((caught: unknown) => {
      if ((caught as Error).name !== 'AbortError') setError((caught as Error).message)
    })
    return () => controller.abort()
  }, [])
  useEffect(() => reload(), [reload])

  const submitPublication = async (event: FormEvent) => {
    event.preventDefault()
    if (!reason.trim() || !data?.brittany.publishable) return
    setPublishing(true)
    setMessage('')
    try {
      const result = await publishBrittany(reason)
      setMessage(`Bundle ${result.bundle_id} publié.`)
      setReason('')
      reload()
    } catch (caught) { setMessage((caught as Error).message) }
    finally { setPublishing(false) }
  }

  const withdraw = async () => {
    if (!reason.trim() || !data?.brittany.active_bundle) return
    setPublishing(true)
    try {
      await withdrawBrittany(reason)
      setMessage('Publication Bretagne retirée.')
      setReason('')
      reload()
    } catch (caught) { setMessage((caught as Error).message) }
    finally { setPublishing(false) }
  }

  return <div className="admin-overlay" role="dialog" aria-modal="true" aria-labelledby="admin-title"><section className="admin-panel"><header><div><span className="eyebrow">ADMINISTRATION</span><h2 id="admin-title">Pilote Bretagne</h2></div><button className="icon-button" aria-label="Fermer l’administration" onClick={onClose}><X size={17} /></button></header>{error ? <State icon={<TriangleAlert />} title="Accès indisponible" text={error} /> : !data ? <State icon={<LoaderCircle className="spin" />} title="Chargement" text="Lecture des releases, de la couverture et des contrôles qualité." /> : <div className="admin-content">
    <section className="regional-readiness"><h3>Publication régionale</h3><div className={`regional-gate ${data.brittany.publishable ? 'ready' : 'blocked'}`}>{data.brittany.publishable ? <CheckCircle2 size={16} /> : <TriangleAlert size={16} />}<span><strong>{data.brittany.publishable ? 'Prête à publier' : 'Publication bloquée'}</strong><small>{data.brittany.blockers.length ? data.brittany.blockers.join(' · ') : 'Toutes les preuves requises sont présentes.'}</small></span></div><div className="territory-grid">{Object.entries(data.brittany.territories).map(([department, territory]) => <article key={department}><strong>Département {department}</strong><span>{territory.covered ? 'couvert' : 'non couvert'}</span><small>{territory.sources.filter((source) => source.ready).length}/9 sources acceptées</small></article>)}</div><p>Scores actifs : {data.brittany.active_score_count}/2 · segmentation v{data.brittany.segmentation.version} {data.brittany.segmentation.status}</p>{data.brittany.active_bundle && <p>Active : {data.brittany.active_bundle.bundle_id}</p>}<form className="publication-form" onSubmit={submitPublication}><label>Motif auditable<textarea value={reason} maxLength={2000} onChange={(event) => setReason(event.target.value)} placeholder="Décision et preuves examinées…" /></label><div><button type="submit" disabled={publishing || !data.brittany.publishable || session?.role !== 'platform_admin' || reason.trim().length < 3}>Publier la Bretagne</button>{data.brittany.active_bundle && <button type="button" className="danger-button" disabled={publishing || session?.role !== 'platform_admin' || reason.trim().length < 3} onClick={() => void withdraw()}>Retirer</button>}</div></form>{session?.role !== 'platform_admin' && <p>Lecture seule : le rôle platform_admin est requis.</p>}{message && <p role="status">{message}</p>}</section>
    <section><h3>Derniers imports</h3>{data.importRuns.length === 0 ? <p>Aucune exécution.</p> : data.importRuns.map((run, index) => <article key={String(run.id ?? index)}><strong>{displayValue(run.release_id)}</strong><span>{displayValue(run.status)}</span><small>{displayValue(run.territory_type)} {displayValue(run.territory_code)} · {displayValue(run.normalized_row_count)} lignes normalisées</small>{run.error_message ? <p>{displayValue(run.error_message)}</p> : null}</article>)}</section><section><h3>Qualité des données</h3>{data.dataQuality.length === 0 ? <p>Aucun contrôle.</p> : data.dataQuality.map((check, index) => <article key={`${displayValue(check.check_code)}:${index}`}><strong>{displayValue(check.check_code)}</strong><span>{displayValue(check.status)} · {displayValue(check.severity)}</span><small>{displayValue(check.scope_type)} {displayValue(check.scope_code)}{check.blocks_publication ? ' · publication bloquée' : ''}</small></article>)}</section></div>}</section></div>
}

function State({ icon, title, text, action }: { icon: React.ReactNode; title: string; text: string; action?: React.ReactNode }) {
  return <div className="empty-state"><span>{icon}</span><strong>{title}</strong><p>{text}</p>{action}</div>
}

type OpportunityBundle = {
  detail: OpportunityDetail
  evidence: Record<string, unknown>[]
  comparables: Record<string, unknown>[]
  sources: Record<string, unknown>[]
  workspace: CandidateWorkspace
}

const STATUS_LABELS: Record<CandidateWorkspace['state']['status'], string> = {
  new: 'Nouveau', to_analyze: 'À analyser', retained: 'Retenu',
  contact_to_prepare: 'Contact à préparer', contacted: 'Contacté', visit: 'Visite',
  offer: 'Offre', acquired: 'Acquis', lost: 'Perdu', rejected: 'Rejeté', ignored: 'Ignoré',
}

function displayValue(value: unknown) {
  if (value === null || value === undefined) return 'Inconnu'
  if (typeof value === 'number') return value.toLocaleString('fr-FR', { maximumFractionDigits: 2 })
  if (typeof value === 'object') return JSON.stringify(value)
  return String(value)
}

function OpportunitySheet({ id, onClose, onProperty }: { id: string; onClose: () => void; onProperty: (id: string) => void }) {
  const [bundle, setBundle] = useState<OpportunityBundle | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [saving, setSaving] = useState(false)
  const [actionError, setActionError] = useState('')
  const [note, setNote] = useState('')
  const [statusDraft, setStatusDraft] = useState<CandidateWorkspace['state']['status']>('new')
  const [rejectionReason, setRejectionReason] = useState<'land_false_positive' | 'adverse_planning' | 'no_access' | 'risk_too_high' | 'estimate_too_optimistic' | 'works_too_large' | 'already_known' | 'outside_strategy' | 'other'>('land_false_positive')
  const [rejectionComment, setRejectionComment] = useState('')
  const [scenario, setScenario] = useState<ScenarioRequest>({
    purchase_price_eur: 0, works_cost_eur: 0, resale_price_eur: 0,
    fees_eur: 0, finance_cost_eur: 0, holding_cost_eur: 0,
  })

  useEffect(() => {
    const controller = new AbortController()
    setLoading(true)
    setError('')
    loadOpportunity(id, controller.signal)
      .then((loaded) => { setBundle(loaded); setStatusDraft(loaded.workspace.state.status) })
      .catch((caught: unknown) => {
        if ((caught as Error).name !== 'AbortError') setError((caught as Error).message)
      })
      .finally(() => setLoading(false))
    return () => controller.abort()
  }, [id])

  const changeStatus = async (
    status: CandidateWorkspace['state']['status'],
    favorite = bundle?.workspace.state.favorite ?? false,
  ) => {
    if (!bundle) return
    setSaving(true)
    setActionError('')
    try {
      const state = await updateCandidateStatus(id, {
        status, favorite,
        rejection_reasons: status === 'rejected' ? [rejectionReason] : [],
        rejection_comment: status === 'rejected' ? rejectionComment : null,
      })
      setBundle({ ...bundle, workspace: { ...bundle.workspace, state } })
      setStatusDraft(state.status)
    } catch (caught) {
      setActionError((caught as Error).message)
      setStatusDraft(bundle.workspace.state.status)
    } finally { setSaving(false) }
  }

  const submitNote = async (event: FormEvent) => {
    event.preventDefault()
    if (!bundle || !note.trim()) return
    setSaving(true)
    setActionError('')
    try {
      const created = await createCandidateNote(id, note)
      setBundle({ ...bundle, workspace: { ...bundle.workspace, notes: [created, ...bundle.workspace.notes] } })
      setNote('')
    } catch (caught) { setActionError((caught as Error).message) }
    finally { setSaving(false) }
  }

  const submitScenario = async (event: FormEvent) => {
    event.preventDefault()
    if (!bundle) return
    setSaving(true)
    setActionError('')
    try {
      const created = await createCandidateScenario(id, scenario)
      setBundle({ ...bundle, workspace: { ...bundle.workspace, scenarios: [created, ...bundle.workspace.scenarios] } })
    } catch (caught) { setActionError((caught as Error).message) }
    finally { setSaving(false) }
  }

  if (loading) return <State icon={<LoaderCircle className="spin" />} title="Chargement du candidat" text="Score, preuves, comparables et espace privé sont chargés ensemble." />
  if (error || !bundle) return <State icon={<TriangleAlert />} title="Fiche indisponible" text={error || 'Réponse incomplète'} action={<button onClick={onClose}>Fermer</button>} />

  const { detail, workspace, evidence, comparables, sources } = bundle
  const stale = Date.now() - new Date(detail.snapshot_at).getTime() > 180 * 24 * 60 * 60 * 1000
  const latestScenario = workspace.scenarios[0]

  return <>
    <div className="detail-actions"><span className="eyebrow">CANDIDAT · {detail.strategy === 'division_extension' ? 'DIVISION' : 'RÉNOVATION'}</span><button className="icon-button" onClick={onClose} aria-label="Fermer la fiche"><X size={17} /></button></div>
    <div className="detail-scroll candidate-sheet">
      <header className="detail-header"><span className="entity-icon"><Compass size={24} /></span><div><h2>{detail.property_unit_id}</h2><p>Snapshot du {new Date(detail.snapshot_at).toLocaleDateString('fr-FR')} · segment {detail.segment_code}</p></div></header>
      {stale && <div className="state-banner partial"><TriangleAlert size={14} />Snapshot ancien : contrôlez la fraîcheur des sources.</div>}
      <section className="detail-section score-summary"><div><span>Score</span><strong>{detail.score === null || detail.score === undefined ? 'Inconnu' : detail.score.toFixed(1)}</strong></div><div><span>Confiance</span><strong>{detail.confidence_score.toFixed(0)}%</strong><small>{detail.confidence_level}</small></div></section>
      <section className="detail-section"><h3>Qualification privée</h3><button className={`favorite-button ${workspace.state.favorite ? 'active' : ''}`} aria-pressed={workspace.state.favorite} onClick={() => void changeStatus(workspace.state.status, !workspace.state.favorite)}><Heart size={14} fill={workspace.state.favorite ? 'currentColor' : 'none'} /> {workspace.state.favorite ? 'Retirer des favoris' : 'Ajouter aux favoris'}</button><label className="field-label">Statut<select aria-label="Statut du candidat" disabled={saving} value={statusDraft} onChange={(event) => { const value = event.target.value as CandidateWorkspace['state']['status']; setStatusDraft(value); if (value !== 'rejected') void changeStatus(value) }}>{Object.entries(STATUS_LABELS).map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></label>{statusDraft === 'rejected' && <div className="rejection-editor"><label className="field-label">Motif<select aria-label="Motif de rejet" value={rejectionReason} onChange={(event) => setRejectionReason(event.target.value as typeof rejectionReason)}><option value="land_false_positive">Faux positif foncier</option><option value="adverse_planning">Urbanisme défavorable</option><option value="no_access">Accès impossible</option><option value="risk_too_high">Risque trop élevé</option><option value="estimate_too_optimistic">Estimation trop optimiste</option><option value="works_too_large">Travaux trop importants</option><option value="already_known">Déjà connu</option><option value="outside_strategy">Hors stratégie</option><option value="other">Autre</option></select></label><label className="field-label">Commentaire<textarea aria-label="Commentaire de rejet" required={rejectionReason === 'other'} value={rejectionComment} onChange={(event) => setRejectionComment(event.target.value)} /></label><button disabled={saving || (rejectionReason === 'other' && !rejectionComment.trim())} onClick={() => void changeStatus('rejected')}>Confirmer le rejet</button></div>}{actionError && <p className="inline-error" role="alert">{actionError}</p>}</section>
      <section className="detail-section"><h3>Raisons du classement</h3>{evidence.length === 0 ? <p className="unknown-value">Aucune preuve publiée.</p> : <div className="evidence-list">{evidence.map((item, index) => <article key={`${displayValue(item.feature_code)}:${index}`}><div><strong>{displayValue(item.feature_code)}</strong><span className={`impact ${Number(item.impact) < 0 ? 'negative' : 'positive'}`}>{Number(item.impact) > 0 ? '+' : ''}{displayValue(item.impact)}</span></div><p>{displayValue(item.explanation)}</p><small>{displayValue(item.quality)} · observé {displayValue(item.observed_at)}</small></article>)}</div>} {detail.missing_features.length > 0 && <p className="missing-value"><TriangleAlert size={13} /> Inconnues : {detail.missing_features.join(', ')}</p>}</section>
      <section className="detail-section"><h3>Scénario financier</h3><form className="scenario-form" onSubmit={submitScenario}>{([['purchase_price_eur', 'Acquisition'], ['works_cost_eur', 'Travaux'], ['resale_price_eur', 'Revente'], ['fees_eur', 'Frais'], ['finance_cost_eur', 'Financement'], ['holding_cost_eur', 'Portage']] as const).map(([key, label]) => <label key={key}>{label}<input aria-label={label} required type="number" min="0" step="1000" value={scenario[key]} onChange={(event) => setScenario({ ...scenario, [key]: Number(event.target.value) })} /></label>)}<button disabled={saving} type="submit"><Calculator size={14} /> Recalculer et sauvegarder</button></form>{latestScenario && <dl className="scenario-results"><div><dt>Coût total</dt><dd>{displayValue(latestScenario.results.total_cost_eur)} €</dd></div><div><dt>Marge nette</dt><dd>{displayValue(latestScenario.results.net_margin_eur)} €</dd></div><div><dt>Rendement coût</dt><dd>{typeof latestScenario.results.return_on_cost === 'number' ? `${(latestScenario.results.return_on_cost * 100).toFixed(1)}%` : 'Inconnu'}</dd></div></dl>}<p className="method-note">Ces hypothèses privées créent un scénario séparé. Elles ne modifient jamais le snapshot ni ses sources.</p></section>
      <section className="detail-section"><h3>Transactions comparables</h3>{comparables.length === 0 ? <p className="unknown-value">Aucun comparable disponible.</p> : comparables.map((item, index) => <div className="comparable-row" key={`${displayValue(item.transaction_id)}:${index}`}><span><strong>{displayValue(item.transaction_id)}</strong><small>{displayValue(item.reason)}</small></span><span>{displayValue(item.normalized_price_m2)} €/m²<br /><small>{item.included ? 'Inclus' : 'Exclu'}</small></span></div>)}</section>
      <section className="detail-section"><h3>Sources et fraîcheur</h3>{sources.length === 0 ? <p className="unknown-value">Source indisponible — la provenance n’est pas masquée.</p> : sources.map((source, index) => <div className="source-row" key={`${displayValue(source.data_source_id)}:${index}`}><ExternalLink size={15} /><span><strong>{displayValue(source.name ?? source.data_source_id)}</strong><small>{displayValue(source.producer)} · {displayValue(source.release_id)}</small></span></div>)}</section>
      <section className="detail-section"><h3>Notes et historique</h3><form className="note-form" onSubmit={submitNote}><label htmlFor="candidate-note">Nouvelle note</label><textarea id="candidate-note" value={note} maxLength={10000} onChange={(event) => setNote(event.target.value)} placeholder="Observation factuelle…" /><button disabled={saving || !note.trim()} type="submit"><FileText size={14} /> Ajouter la note</button></form>{workspace.notes.map((item) => <article className="note-row" key={item.id}><p>{item.body}</p><small>{item.author} · {new Date(item.created_at).toLocaleString('fr-FR')}</small></article>)}{workspace.history.map((item, index) => <div className="history-row" key={String(item.id ?? index)}><CheckCircle2 size={13} /><span>{STATUS_LABELS[item.status as keyof typeof STATUS_LABELS] ?? displayValue(item.status)}<small>{displayValue(item.author)} · {item.occurred_at ? new Date(String(item.occurred_at)).toLocaleString('fr-FR') : 'date inconnue'}</small></span></div>)}</section>
      <section className="detail-section"><button className="property-link" onClick={() => onProperty(detail.property_unit_id)}><MapIcon size={15} /> Ouvrir l’unité foncière</button></section>
    </div>
  </>
}

function EntitySheet({ detail, onClose, onRelated }: { detail: EntityDetail; onClose: () => void; onRelated: (type: EntityType, id: string) => void }) {
  const kind = detail.entity_type === 'building' ? 'Bâtiment' : detail.entity_type === 'property_unit' ? 'Unité foncière' : 'Parcelle'
  return <>
    <div className="detail-actions"><span className="eyebrow">{kind.toUpperCase()}</span><button className="icon-button" onClick={onClose} aria-label="Fermer la fiche"><X size={17} /></button></div>
    <div className="detail-scroll">
      <header className="detail-header"><span className="entity-icon">{detail.entity_type === 'building' ? <Building2 size={24} /> : <MapIcon size={24} />}</span><div><h2>{detail.label}</h2><p>{detail.commune_name ?? detail.commune_code} · {detail.department_code}</p></div></header>
      <section className="detail-section"><h3>Géométrie active</h3><dl className="facts"><div><dt>Surface calculée</dt><dd>{formatArea(detail.area_m2)}</dd></div><div><dt>Identifiant stable</dt><dd>{detail.id}</dd></div><div><dt>Commune INSEE</dt><dd>{detail.commune_code ?? 'Non disponible'}</dd></div></dl></section>
      {Object.keys(detail.properties).length > 0 && <section className="detail-section"><h3>Attributs</h3><dl className="facts">{Object.entries(detail.properties).map(([key, value]) => <div key={key}><dt>{key.replaceAll('_', ' ')}</dt><dd>{value === null ? 'Non disponible' : String(value)}</dd></div>)}</dl></section>}
      {detail.related_entities.length > 0 && <section className="detail-section"><h3>Entités liées</h3><div className="related-list">{detail.related_entities.map((entity) => <button key={`${entity.entity_type}:${entity.id}`} onClick={() => onRelated(entity.entity_type, entity.id)}>{entity.entity_type === 'building' ? <Building2 size={15} /> : <MapIcon size={15} />}<span>{entity.label}</span></button>)}</div></section>}
      <section className="detail-section"><h3>Provenance</h3>{detail.sources.map((source, index) => <div className="source-row" key={`${source.data_source_id}:${index}`}><ExternalLink size={15} /><span><strong>{source.data_source_id}</strong><small>{source.producer ?? 'Producteur documenté'}{source.release_id ? ` · ${source.release_id}` : ''}</small></span></div>)}</section>
    </div>
  </>
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

export default App
