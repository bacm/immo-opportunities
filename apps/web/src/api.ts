import type { components } from './generated/api'
import { getAccessToken } from './auth'

export type Bbox = [number, number, number, number]
export type Center = [number, number]

type GeneratedSearchResult = components['schemas']['SearchResponse']
type GeneratedEntityDetail = components['schemas']['EntityDetailResponse']
export type Session = components['schemas']['SessionResponse']
export type AddressContext = components['schemas']['AddressContextResponse']
export type EntityMatch = components['schemas']['EntityMatchResponse']
export type CommuneCoverage = components['schemas']['CommuneCoverageResponse']
export type BlindCase = components['schemas']['BlindCaseResponse']
export type ReviewProgress = components['schemas']['ReviewProgressResponse']
export type StratumResult = components['schemas']['StratumResultResponse']
export type CaseContext = components['schemas']['CaseContextResponse']
export type ParcelTransaction = components['schemas']['ParcelTransactionResponse']
export type ParcelEnergyAssessment = components['schemas']['ParcelEnergyAssessmentResponse']

export type SearchResult = Omit<GeneratedSearchResult, 'center' | 'bbox'> & {
  center: Center
  bbox: Bbox
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
): Promise<T> {
  const token = getAccessToken()
  const headers = new Headers(init.headers)
  headers.set('Accept', 'application/json')
  if (token) headers.set('Authorization', `Bearer ${token}`)
  if (init.body) headers.set('Content-Type', 'application/json')
  const response = await fetch(path, { ...init, headers })
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

export function searchEntities(query: string, signal?: AbortSignal) {
  return request<SearchResult[]>(`/api/v1/search?query=${encodeURIComponent(query)}&department_code=35`, { signal })
}

export function loadEntity(type: EntityType, id: string, signal?: AbortSignal) {
  const collection = type === 'property_unit' ? 'property-units' : `${type}s`
  return request<EntityDetail>(`/api/v1/${collection}/${encodeURIComponent(id)}`, { signal })
}

/**
 * Contexte d'une adresse : sa position, son statut de position, et les appariements qui la
 * relient aux entités canoniques — chacun avec sa méthode, sa confiance et sa décision.
 *
 * Une adresse n'est pas une entité canonique de l'Explorer : elle ne se charge donc pas par
 * `loadEntity`, dont les collections sont parcelle, bâtiment et unité foncière.
 */
export function loadAddressContext(id: string, signal?: AbortSignal) {
  return request<AddressContext>(`/api/v1/spatial/addresses/${encodeURIComponent(id)}`, { signal })
}

/**
 * Couverture d'une commune, source par source. Distingue trois états que l'utilisateur ne doit
 * jamais confondre : territoire non couvert, couvert partiellement, couvert.
 */
export function loadCommuneCoverage(communeCode: string, signal?: AbortSignal) {
  return request<CommuneCoverage>(`/api/v1/spatial/coverage?commune_code=${encodeURIComponent(communeCode)}`, { signal })
}

/**
 * Revue manuelle B4. Le cas rendu est **aveugle** : l'API n'expose ni la décision du moteur, ni
 * sa confiance, ni sa justification. Le front n'a donc rien à masquer — il ne les reçoit pas.
 */
export function loadReviewProgress(sampleId: string, signal?: AbortSignal) {
  return request<ReviewProgress>(`/api/v1/review/samples/${encodeURIComponent(sampleId)}`, { signal })
}

export function loadNextReviewCase(sampleId: string, signal?: AbortSignal) {
  return request<BlindCase>(`/api/v1/review/samples/${encodeURIComponent(sampleId)}/next`, { signal })
}

export function loadCaseContext(caseId: number, signal?: AbortSignal) {
  return request<CaseContext>(`/api/v1/review/cases/${caseId}/context`, { signal })
}

export function loadReviewResults(sampleId: string, signal?: AbortSignal) {
  return request<StratumResult[]>(`/api/v1/review/samples/${encodeURIComponent(sampleId)}/results`, { signal })
}

export function submitReviewVerdict(payload: {
  case_id: number
  verdict: 'correct' | 'incorrect' | 'undecidable'
  reviewer: string
  rationale: string
  evidence_consulted: string
}) {
  return request<components['schemas']['VerdictResponse']>('/api/v1/review/verdicts', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
}

export function loadParcelTransactions(parcelId: string, signal?: AbortSignal) {
  return request<ParcelTransaction[]>(`/api/v1/parcels/${encodeURIComponent(parcelId)}/transactions`, { signal })
}

export function loadParcelEnergyAssessments(parcelId: string, signal?: AbortSignal) {
  return request<ParcelEnergyAssessment[]>(`/api/v1/parcels/${encodeURIComponent(parcelId)}/energy-assessments`, { signal })
}

export function loadSession(signal?: AbortSignal) {
  return request<Session>('/api/v1/session', { signal })
}
