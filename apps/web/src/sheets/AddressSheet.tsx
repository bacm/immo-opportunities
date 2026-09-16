import { Map as MapIcon, MapPin } from 'lucide-react'
import type { AddressContext, EntityMatch, EntityType } from '../api'
import { DECISION_LABELS, METHOD_LABELS, entityLabel, formatPercent } from '../format'
import { Chip, Facts, Section, type Tone } from '../ui'
import { SheetFrame } from './SheetFrame'

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
export function AddressSheet({ context, onClose, onRelated }: {
  context: AddressContext; onClose: () => void; onRelated: (type: EntityType, id: string) => void
}) {
  const { address, matches } = context
  const located = address.longitude !== null && address.latitude !== null
  const groups: Array<[string, string, Tone]> = [
    ['certain', 'Appariements certains', 'good'],
    ['ambiguous', 'Appariements ambigus', 'warn'],
    ['rejected', 'Relations rejetées', 'bad'],
  ]
  return <SheetFrame
    kind="Adresse"
    icon={<MapPin size={22} />}
    title={address.display_label}
    subtitle={<>Commune {address.commune_code} · <span className="mono">{address.id}</span></>}
    onClose={onClose}
  >
    <Section title="Position">
      <Facts items={[['État', located ? 'Localisée' : `Non localisée · ${address.position_status}`]]} />
      {!located && <p className="callout">Cette adresse existe dans la release mais sa position est inutilisable. Elle n’entre dans aucune relation spatiale et la carte n’a pas été recentrée.</p>}
    </Section>
    {matches.length === 0 && <Section title="Entités liées">
      <p className="detail-note">Aucun appariement pour cette adresse dans la release active. C’est une absence, pas un rejet : rien ne permet de la rattacher, et rien ne l’en empêche formellement.</p>
    </Section>}
    {groups.map(([decision, title, tone]) => {
      const list = matches.filter((match) => match.decision === decision)
      if (!list.length) return null
      return <Section key={decision} title={title} aside={<span className="count">{list.length}</span>}>
        <ol className="record-list">{list.map((match) => <MatchRow key={match.id} match={match} tone={tone} onRelated={onRelated} />)}</ol>
      </Section>
    })}
  </SheetFrame>
}

function MatchRow({ match, tone, onRelated }: { match: EntityMatch; tone: Tone; onRelated: (type: EntityType, id: string) => void }) {
  const type = match.right_entity_type as EntityType
  return <li className="record match-row">
    <header>
      <button className="record-link" title={match.right_entity_id} onClick={() => onRelated(type, match.right_entity_id)}>
        <MapIcon size={15} />
        <span>{entityLabel(type, match.right_entity_id, match.right_entity_id)}</span>
      </button>
      <span className="record-side"><Chip tone={tone}>{DECISION_LABELS[match.decision] ?? match.decision}</Chip></span>
    </header>
    <Facts items={[
      ['Identifiant', <span className="mono">{match.right_entity_id}</span>],
      ['Méthode', <>{METHOD_LABELS[match.method] ?? match.method} <span className="mono muted">{match.method}</span></>],
      ['Confiance', formatPercent(match.confidence)],
      ['Justification', match.rationale],
      ['Releases', match.release_ids.join(', ')],
    ]} />
  </li>
}
