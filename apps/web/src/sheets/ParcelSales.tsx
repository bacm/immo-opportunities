import { LoaderCircle } from 'lucide-react'
import type { ParcelTransaction } from '../api'
import { formatArea, formatDate, formatEuro } from '../format'
import { Chip, RequestReference, State } from '../ui'
import type { Loaded } from './useLoad'

/**
 * Les mutations DVF d'une parcelle — instrument de vérification D6a, pas fonctionnalité produit.
 *
 * Il existe pour qu'un humain vérifie que l'import et le rattachement tiennent, comme l'écran de
 * revue de B4 l'a fait pour les appariements. Il a servi avant d'exister : la première requête a
 * montré une « Dépendance » de 382 m², dont la surface venait du terrain — 30 816 lots bâtis
 * étaient concernés. Local seulement : aucune fiche de mutations n'est montrée à un tiers avant
 * l'avis juridique de H4 (`SPEC.md` §18.4).
 *
 * **Aucun prix au m² n'est calculé ici.** Il n'existe pas en base, et le dériver à l'affichage
 * fabriquerait une valeur que rien ne justifie. Le motif de non-allocation est montré à la place :
 * 55 % des mutations 2021-2025 n'ont aucun prix allouable (H7), et ce motif est l'information.
 */
/** Un compte inconnu n'est pas « un seul » : il ne déclenche simplement aucune mention. */
const several = (count: number | null) => count !== null && count > 1

export function ParcelSales({ loaded }: { loaded: Loaded<ParcelTransaction[]> }) {
  if (loaded.status === 'failed') {
    return <p className="inline-error" role="alert">Mutations indisponibles : le service local n’a pas répondu. Rien n’est affirmé sur cette parcelle.<RequestReference reference={loaded.reference} /></p>
  }
  if (loaded.status === 'loading') return <State icon={<LoaderCircle className="spin" />} title="Chargement des ventes" text="Lecture des mutations DVF rattachées." />
  const rows = loaded.value
  if (rows.length === 0) return <p className="unknown-value">Aucune mutation rattachée à cette parcelle.</p>

  // Groupé par mutation, jamais ligne à ligne. Une mutation est un acte ; ses lots en sont le
  // contenu. Affichés à plat, deux lots d'une même vente ressemblaient à deux ventes.
  const acts = Object.entries(rows.reduce<Record<string, ParcelTransaction[]>>((groups, row) => {
    (groups[row.transaction_id] ??= []).push(row)
    return groups
  }, {}))

  return <>
    <ol className="record-list transaction-list">
      {acts.map(([transactionId, lots]) => {
        const head = lots[0]
        const allocated = head.allocated_price_eur !== null
        return <li className="record transaction-row" key={transactionId}>
          <header>
            <span className="record-title">{formatDate(head.mutation_date)}</span>
            <span className="record-sub">{head.mutation_nature ?? 'Nature inconnue'}</span>
            <span className="record-side">
              {allocated
                ? <Chip tone="good">{lots.length === 1 ? 'Prix alloué' : 'Prix par lot'}</Chip>
                : <Chip tone="warn">Prix non allouable</Chip>}
            </span>
          </header>
          {!allocated && <p className="record-note">{head.unallocated_reason ?? 'motif absent'}</p>}
          {(several(head.lot_count) || several(head.parcel_count)) && <p className="record-note">
            {[
              several(head.lot_count) ? `${head.lot_count} lots dans l’acte` : null,
              several(head.parcel_count) ? `${head.parcel_count} parcelles` : null,
            ].filter(Boolean).join(' · ')}
          </p>}
          <ul className="lots">
            {lots.map((lot, index) => <li key={index} className="transaction-lot">
              <span>{lot.property_type ?? 'Type inconnu'}</span>
              <span>{lot.surface_m2 ? formatArea(lot.surface_m2) : 'surface absente'}</span>
              <span className="lot-price">{lot.allocated_price_eur !== null ? formatEuro(lot.allocated_price_eur) : '—'}</span>
            </li>)}
          </ul>
        </li>
      })}
    </ol>
    <p className="detail-note">
      {rows.length} lot{rows.length > 1 ? 's' : ''} sur cette parcelle. Aucun prix au m² n’est calculé ici : il n’existe pas en base. Un prix non allouable porte
      son motif — c’est le cas de plus d’une mutation sur deux, et c’est le résultat.
    </p>
  </>
}
