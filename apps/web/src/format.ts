/**
 * Mise en forme des valeurs affichées. Une absence y reste une absence : chaque fonction rend un
 * libellé explicite pour `null`, jamais un zéro.
 */

const DATE = new Intl.DateTimeFormat('fr-FR', { day: 'numeric', month: 'short', year: 'numeric' })
const EURO = new Intl.NumberFormat('fr-FR', { style: 'currency', currency: 'EUR', maximumFractionDigits: 0 })

export function formatArea(value: number | null | undefined, missing = 'Non disponible') {
  return value === null || value === undefined ? missing : `${Math.round(value).toLocaleString('fr-FR')} m²`
}

export function formatEuro(value: number | null | undefined, missing = 'Prix absent') {
  return value === null || value === undefined ? missing : EURO.format(value)
}

export function formatDate(value: string | null | undefined, missing = 'Date inconnue') {
  if (!value) return missing
  const parsed = new Date(value)
  return Number.isNaN(parsed.getTime()) ? value : DATE.format(parsed)
}

export function formatPercent(value: number | null | undefined, missing = 'Inconnue') {
  return value === null || value === undefined ? missing : `${Math.round(value * 100)} %`
}

export function displayValue(value: unknown) {
  if (value === null || value === undefined || value === '') return 'Non disponible'
  if (typeof value === 'number') return value.toLocaleString('fr-FR', { maximumFractionDigits: 2 })
  if (typeof value === 'boolean') return value ? 'Oui' : 'Non'
  if (typeof value === 'object') return JSON.stringify(value)
  return String(value)
}

/** « 35238000AB0303 » → section AB, numéro 303. Un identifiant hors format reste tel quel. */
export function parseCadastralId(id: string) {
  const match = /^(\d{5})(\d{3})([0-9A-Z]{2})(\d{4})$/.exec(id.replace(/^parcel:cadastre:/, ''))
  if (!match) return null
  return { commune: match[1], prefix: match[2], section: match[3].replace(/^0/, ''), number: String(Number(match[4])) }
}

export function parcelTitle(id: string) {
  const parsed = parseCadastralId(id)
  if (!parsed) return id.replace(/^parcel:cadastre:/, '')
  return `Section ${parsed.section} · n° ${parsed.number}`
}

/** Les bâtiments cadastraux ont pour identifiant une empreinte de 64 caractères : illisible. */
export function entityLabel(type: string, id: string, label: string) {
  if (type === 'parcel') return parcelTitle(id)
  if (type === 'building') {
    const [, source = '', key = label] = id.split(':')
    const name = source === 'cadastre' ? 'Bâtiment cadastral' : source === 'rnb' ? 'Bâtiment RNB' : 'Bâtiment'
    return `${name} · ${key.length > 12 ? key.slice(0, 8) : key}`
  }
  return label
}

export const CADASTRAL_BUILDING_TYPES: Record<string, string> = { '01': 'bâti dur', '02': 'bâti léger' }

const PROPERTY_LABELS: Record<string, string> = {
  number: 'Numéro',
  section: 'Section',
  cadastral_id: 'Identifiant cadastral',
  stated_area_m2: 'Surface déclarée',
  cadastral_type: 'Type cadastral',
  cadastral_name: 'Nom cadastral',
  was_repaired: 'Géométrie réparée',
  parcel_id: 'Parcelle',
}

export function propertyLabel(key: string) {
  return PROPERTY_LABELS[key] ?? key.replaceAll('_', ' ')
}

export function propertyValue(key: string, value: unknown) {
  if (key === 'stated_area_m2' && typeof value === 'number') return formatArea(value)
  if (key === 'cadastral_type' && typeof value === 'string') return CADASTRAL_BUILDING_TYPES[value] ?? value
  return displayValue(value)
}

export const DECISION_LABELS: Record<string, string> = {
  certain: 'Certain',
  ambiguous: 'Ambigu',
  rejected: 'Rejeté',
}

export const METHOD_LABELS: Record<string, string> = {
  source_relation: 'relation déclarée par la source',
  spatial_containment: 'contenance géométrique',
  spatial_overlap: 'recouvrement géométrique',
}
