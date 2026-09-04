import type { components } from './generated/api'
import { getAccessToken } from './auth'

export type Bbox = [number, number, number, number]
export type Center = [number, number]

type GeneratedSearchResult = components['schemas']['SearchResponse']
type GeneratedPropertyUnit = components['schemas']['PropertyUnitSummaryResponse']
type GeneratedViewport = components['schemas']['ViewportResponse']
type GeneratedEntityDetail = components['schemas']['EntityDetailResponse']
export type OpportunitySummary = components['schemas']['OpportunitySummaryResponse']
export type OpportunityDetail = components['schemas']['OpportunityDetailResponse']
export type CandidateWorkspace = components['schemas']['WorkspaceResponse']
export type CandidateState = components['schemas']['CandidateStateResponse']
export type ScenarioRequest = components['schemas']['ScenarioRequest']
export type ScenarioResponse = components['schemas']['ScenarioResponse']
export type NoteResponse = components['schemas']['NoteResponse']
export type Session = components['schemas']['SessionResponse']

export type BrittanyReadiness = {
  publishable: boolean
  blockers: string[]
  territories: Record<string, {
    covered: boolean
    sources: Array<{
      data_source_id: string
      release_id: string | null
      acceptance_status: string
      blocking_quality_count: number
      ready: boolean
    }>
  }>
  active_score_count: number
  segmentation: { id: string; version: number; status: string }
  active_bundle: { bundle_id: string; published_at: string; published_by: string } | null
}

export type SearchResult = Omit<GeneratedSearchResult, 'center' | 'bbox'> & {
  center: Center
  bbox: Bbox
}

export type PropertyUnitSummary = Omit<GeneratedPropertyUnit, 'center'> & {
  center: Center
}

export type ViewportResult = Omit<GeneratedViewport, 'items'> & {
  items: PropertyUnitSummary[]
}

export type EntityType = 'parcel' | 'building' | 'property_unit'

export type EntityDetail = Omit<GeneratedEntityDetail, 'area_m2' | 'center' | 'bbox' | 'geometry' | 'related_entities' | 'sources'> & {
  area_m2: number | null
  center: Center
  bbox: Bbox
  geometry: { type: string; coordinates: unknown }
  properties: Record<string, unknown>
  related_entities: Array<{ entity_type: EntityType; id: string; label: string }>
  sources: Array<{ data_source_id: string; release_id?: string; producer?: string }>
}

type ErrorPayload = { detail?: string; error?: { message?: string } }

async function request<T>(
  path: string,
  init: RequestInit = {},
  onResponse?: (response: Response) => void,
): Promise<T> {
  const token = getAccessToken()
  const headers = new Headers(init.headers)
  headers.set('Accept', 'application/json')
  if (token) headers.set('Authorization', `Bearer ${token}`)
  if (init.body) headers.set('Content-Type', 'application/json')
  const response = await fetch(path, { ...init, headers })
  onResponse?.(response)
  if (!response.ok) {
    let message = `La requête a échoué (${response.status})`
    try {
      const payload = await response.json() as ErrorPayload
      if (payload.detail) message = payload.detail
      else if (payload.error?.message) message = payload.error.message
    } catch {
      // Preserve the HTTP fallback message when the proxy returns a non-JSON error.
    }
    throw new Error(message)
  }
  return response.json() as Promise<T>
}

export function searchEntities(query: string, departmentCode = '35', signal?: AbortSignal) {
  return request<SearchResult[]>(`/api/v1/search?query=${encodeURIComponent(query)}&department_code=${departmentCode}`, { signal })
}

export function loadViewport(bbox: Bbox, signal?: AbortSignal) {
  const [west, south, east, north] = bbox
  const params = new URLSearchParams({
    west: String(west), south: String(south), east: String(east), north: String(north), limit: '100',
  })
  return request<ViewportResult>(`/api/v1/property-units?${params}`, { signal })
}

export function loadEntity(type: EntityType, id: string, signal?: AbortSignal) {
  const collection = type === 'property_unit' ? 'property-units' : `${type}s`
  return request<EntityDetail>(`/api/v1/${collection}/${encodeURIComponent(id)}`, { signal })
}

export async function loadOpportunities(filters: {
  strategy?: OpportunitySummary['strategy'] | ''
  minimumScore?: number
  confidenceLevel?: OpportunitySummary['confidence_level'] | ''
  departmentCode?: string
  cursor?: string
}, signal?: AbortSignal) {
  const params = new URLSearchParams({ limit: '30' })
  if (filters.strategy) params.set('strategy', filters.strategy)
  if (filters.minimumScore !== undefined) params.set('minimum_score', String(filters.minimumScore))
  if (filters.confidenceLevel) params.set('confidence_level', filters.confidenceLevel)
  if (filters.departmentCode) params.set('department_code', filters.departmentCode)
  if (filters.cursor) params.set('cursor', filters.cursor)
  let nextCursor: string | null = null
  const items = await request<OpportunitySummary[]>(`/api/v1/opportunities?${params}`, { signal }, (response) => {
    nextCursor = response.headers.get('X-Next-Cursor')
  })
  return { items, nextCursor }
}

export async function loadOpportunity(id: string, signal?: AbortSignal) {
  const base = `/api/v1/opportunities/${encodeURIComponent(id)}`
  const [detail, evidence, comparables, sources, workspace] = await Promise.all([
    request<OpportunityDetail>(base, { signal }),
    request<Record<string, unknown>[]>(`${base}/evidence`, { signal }),
    request<Record<string, unknown>[]>(`${base}/comparables`, { signal }),
    request<Record<string, unknown>[]>(`${base}/sources`, { signal }),
    request<CandidateWorkspace>(`${base}/workspace`, { signal }),
  ])
  return { detail, evidence, comparables, sources, workspace }
}

export function updateCandidateStatus(id: string, payload: components['schemas']['StatusRequest']) {
  return request<CandidateState>(`/api/v1/opportunities/${encodeURIComponent(id)}/status`, {
    method: 'PATCH', body: JSON.stringify(payload),
  })
}

export function createCandidateNote(id: string, body: string) {
  return request<NoteResponse>(`/api/v1/opportunities/${encodeURIComponent(id)}/notes`, {
    method: 'POST', body: JSON.stringify({ body }),
  })
}

export function createCandidateScenario(id: string, payload: ScenarioRequest) {
  return request<ScenarioResponse>(`/api/v1/opportunities/${encodeURIComponent(id)}/scenarios`, {
    method: 'POST', body: JSON.stringify(payload),
  })
}

export function createSavedSearch(name: string, filters: Record<string, unknown>) {
  return request<components['schemas']['SavedSearchResponse']>('/api/v1/saved-searches', {
    method: 'POST', body: JSON.stringify({ name, filters }),
  })
}

export async function loadAdministration(signal?: AbortSignal) {
  const [importRuns, dataQuality, brittany] = await Promise.all([
    request<Record<string, unknown>[]>('/api/v1/admin/import-runs', { signal }),
    request<Record<string, unknown>[]>('/api/v1/admin/data-quality', { signal }),
    request<BrittanyReadiness>('/api/v1/admin/brittany/readiness', { signal }),
  ])
  return { importRuns, dataQuality, brittany }
}

export function publishBrittany(reason: string) {
  return request<{ bundle_id: string; status: string }>('/api/v1/admin/brittany/publications', {
    method: 'POST', body: JSON.stringify({ reason }),
  })
}

export function withdrawBrittany(reason: string) {
  return request<{ status: string }>('/api/v1/admin/brittany/withdraw', {
    method: 'POST', body: JSON.stringify({ reason }),
  })
}

export function loadSession(signal?: AbortSignal) {
  return request<Session>('/api/v1/session', { signal })
}
