import type { ReactNode } from 'react'
import { Gauge, LoaderCircle, Map as MapIcon, TriangleAlert } from 'lucide-react'
import { loadEnergyAssessment, type EnergyAssessmentLookup, type EntityType } from '../api'
import { QUARANTINE_REASONS, entityLabel, formatDate } from '../format'
import { Chip, Facts, Section, State } from '../ui'
import { SheetFrame } from './SheetFrame'
import { useLoad } from './useLoad'

const SOURCES: Record<string, string> = { 'DS-07': 'DPE logement existant', 'DS-13': 'DPE logement neuf' }

const DECLARED_LABELS: Record<string, string> = {
  id_rnb: 'Identifiant de bâtiment (RNB)',
  identifiant_ban: 'Identifiant d’adresse (BAN)',
  commune_code: 'Commune déclarée',
}

/**
 * Un DPE retrouvé par son numéro — C7.
 *
 * Un diagnostic écarté à l'import n'a pas disparu : son motif et les identifiants que la source
 * déclarait sont en quarantaine. Les montrer dit pourquoi il n'est sur aucune parcelle, sans
 * deviner à sa place où il devrait être.
 */
export function DpeSheet({ dpeNumber, onClose, onRelated }: {
  dpeNumber: string; onClose: () => void; onRelated: (type: EntityType, id: string) => void
}) {
  const loaded = useLoad(dpeNumber, loadEnergyAssessment)
  return <SheetFrame kind="Diagnostic DPE" icon={<Gauge size={22} />} title={dpeNumber} subtitle="Recherche par numéro, écarts d’import compris" onClose={onClose}>
    {loaded.status === 'loading' && <State icon={<LoaderCircle className="spin" />} title="Recherche du diagnostic" text="Lecture des diagnostics conservés et des écarts d’import." />}
    {loaded.status === 'failed' && <Section><p className="inline-error" role="alert">Recherche indisponible : le service local n’a pas répondu. Rien n’est affirmé sur ce diagnostic.</p></Section>}
    {loaded.status === 'ready' && loaded.value === null && <State icon={<TriangleAlert />} title="Diagnostic inconnu" text="Ce numéro n’est ni parmi les diagnostics importés, ni parmi les écarts d’import. Il peut être absent des extraits ADEME du 35, ou postérieur à leur date." />}
    {loaded.status === 'ready' && loaded.value !== null && <Lookup lookup={loaded.value} onRelated={onRelated} />}
  </SheetFrame>
}

function Lookup({ lookup, onRelated }: { lookup: EnergyAssessmentLookup; onRelated: (type: EntityType, id: string) => void }) {
  return <>
    {lookup.stored.map((record) => <Section key={record.release_id} title={SOURCES[record.data_source_id]} aside={<Chip tone="good">Conservé</Chip>}>
      <Facts items={[
        ['Établi le', formatDate(record.assessment_date)],
        ['Étiquette', record.energy_label ?? 'Absente'],
        ['Adresse déclarée', record.address_label ?? 'Absente'],
        ['Rattachement', record.building_id ? 'au bâtiment, par identifiant RNB' : 'à l’adresse seule, par identifiant BAN'],
        ['Release', <span className="mono">{record.release_id}</span>],
      ]} />
      {record.parcels.length > 0
        ? <div className="related-list">{record.parcels.map((parcel) => <button key={parcel.parcel_id} title={parcel.parcel_id} onClick={() => onRelated('parcel', parcel.parcel_id)}>
            <MapIcon size={15} />
            <span>{entityLabel('parcel', parcel.parcel_id, parcel.parcel_id)}</span>
            <Chip tone={parcel.relation_status === 'certain' ? 'good' : 'warn'}>{parcel.relation_status === 'certain' ? 'certain' : 'ambigu'}</Chip>
          </button>)}</div>
        : <p className="callout">Rattaché à l’adresse seule : il n’apparaît sur aucune parcelle, la relation adresse ↔ parcelle n’étant vérifiable par aucune règle.</p>}
    </Section>)}
    {lookup.rejected.map((rejection) => <Section key={`${rejection.release_id}:${rejection.attribute}`} title={SOURCES[rejection.data_source_id]} aside={<Chip tone="warn">{rejection.attribute === 'target' ? 'Écarté' : 'Attribut écarté'}</Chip>}>
      <p className="callout"><TriangleAlert size={13} /> {QUARANTINE_REASONS[rejection.reason_code] ?? rejection.reason_detail}</p>
      <Facts items={[
        ['Motif', <span className="mono">{rejection.reason_code}</span>],
        ...Object.entries(rejection.declared).map(([key, value]): [string, ReactNode] => [
          DECLARED_LABELS[key] ?? key,
          value === null
            ? 'Non déclaré'
            : <><span className="mono">{value}</span>{key === 'identifiant_ban' && /^\d{5}_[^_]+$/.test(value) && <span className="muted"> — une voie entière, sans numéro</span>}</>,
        ]),
        ['Release', <span className="mono">{rejection.release_id}</span>],
      ]} />
    </Section>)}
  </>
}
