import { useState } from 'react'
import { Building2, ExternalLink, Map as MapIcon } from 'lucide-react'
import {
  loadParcelEnergyAssessments,
  loadParcelTransactions,
  type EntityDetail,
  type EntityType,
} from '../api'
import { entityLabel, formatArea, parcelTitle, propertyLabel, propertyValue } from '../format'
import { Facts, KeyFigures, Section, Tabs } from '../ui'
import { ParcelDiagnostics } from './ParcelDiagnostics'
import { ParcelSales } from './ParcelSales'
import { SheetFrame } from './SheetFrame'
import { useLoad, type Loaded } from './useLoad'

type Props = { detail: EntityDetail; onClose: () => void; onRelated: (type: EntityType, id: string) => void }

const KIND: Record<EntityType, string> = { parcel: 'Parcelle', building: 'Bâtiment', property_unit: 'Unité foncière' }

export function EntitySheet({ detail, onClose, onRelated }: Props) {
  const parcelLike = detail.entity_type === 'parcel' || detail.entity_type === 'property_unit'
  const title = detail.entity_type === 'building' ? entityLabel('building', detail.id, detail.label) : parcelTitle(detail.label)
  return <SheetFrame
    kind={KIND[detail.entity_type]}
    icon={detail.entity_type === 'building' ? <Building2 size={22} /> : <MapIcon size={22} />}
    title={title}
    subtitle={<>{detail.commune_name ?? detail.commune_code ?? 'Commune inconnue'} · <span className="mono">{detail.label}</span></>}
    onClose={onClose}
  >
    {parcelLike
      ? <ParcelBody detail={detail} onRelated={onRelated} />
      : <>
          <Overview detail={detail} onRelated={onRelated} />
          <Sources detail={detail} />
        </>}
  </SheetFrame>
}

type ParcelTab = 'overview' | 'sales' | 'diagnostics' | 'sources'

/** Les ventes et les DPE sont chargés dès l'ouverture : leur effectif dans l'onglet dit s'il vaut
 *  la peine de l'ouvrir. Les deux s'ancrent sur la même parcelle cadastrale. */
function ParcelBody({ detail, onRelated }: Omit<Props, 'onClose'>) {
  const parcelId = detail.entity_type === 'parcel' ? detail.id : String(detail.properties.parcel_id ?? detail.id)
  const sales = useLoad(parcelId, loadParcelTransactions)
  const diagnostics = useLoad(parcelId, loadParcelEnergyAssessments)
  const [tab, setTab] = useState<ParcelTab>('overview')
  const count = (loaded: Loaded<unknown[]>) =>
    loaded.status === 'ready' ? loaded.value.length : loaded.status === 'loading' ? null : undefined
  const saleCount = sales.status === 'ready' ? new Set(sales.value.map((row) => row.transaction_id)).size : count(sales)

  return <>
    <Tabs<ParcelTab>
      label="Contenu de la fiche"
      active={tab}
      onChange={setTab}
      items={[
        { id: 'overview', label: 'Aperçu' },
        { id: 'sales', label: 'Ventes DVF', count: saleCount },
        { id: 'diagnostics', label: 'Diagnostics DPE', count: count(diagnostics) },
        { id: 'sources', label: 'Sources' },
      ]}
    />
    <div role="tabpanel" className="tab-panel">
      {tab === 'overview' && <Overview detail={detail} onRelated={onRelated} />}
      {tab === 'sales' && <Section><ParcelSales loaded={sales} /></Section>}
      {tab === 'diagnostics' && <Section><ParcelDiagnostics loaded={diagnostics} /></Section>}
      {tab === 'sources' && <Sources detail={detail} />}
    </div>
  </>
}

function Overview({ detail, onRelated }: Omit<Props, 'onClose'>) {
  const parcelLike = detail.entity_type !== 'building'
  const stated = detail.properties.stated_area_m2
  const buildings = detail.related_entities.filter((entity) => entity.entity_type === 'building').length
  const attributes = Object.entries(detail.properties).filter(([key]) => !['number', 'section', 'cadastral_id', 'stated_area_m2'].includes(key))
  return <>
    <Section>
      <KeyFigures items={parcelLike
        ? [
            ['Surface calculée', formatArea(detail.area_m2)],
            ['Surface déclarée', formatArea(typeof stated === 'number' ? stated : null, 'Non déclarée')],
            ['Bâtiments', buildings],
          ]
        : [
            ['Emprise', formatArea(detail.area_m2)],
            ['Parcelles touchées', detail.related_entities.length],
          ]}
      />
      {/* ADR-020 : aucune règle autorisée ne réunit les parcelles d'un même bien. Le dire ici
          évite de lire une dépendance sur parcelle propre comme un bien à part entière. */}
      {parcelLike && <p className="callout unit-scope">Objet analysé : une parcelle cadastrale, pas un bien. Un bien peut s’étendre sur plusieurs parcelles, et aucune source autorisée ne permet de les réunir.</p>}
    </Section>
    {detail.related_entities.length > 0 && <Section title={parcelLike ? 'Bâtiments sur la parcelle' : 'Parcelles touchées'} aside={<span className="count">{detail.related_entities.length}</span>}>
      <div className="related-list">
        {detail.related_entities.map((entity) => <button key={`${entity.entity_type}:${entity.id}`} title={entity.id} onClick={() => onRelated(entity.entity_type, entity.id)}>
          {entity.entity_type === 'building' ? <Building2 size={15} /> : <MapIcon size={15} />}
          <span>{entityLabel(entity.entity_type, entity.id, entity.label)}</span>
          {entity.entity_type === 'parcel' && <span className="mono muted">{entity.label}</span>}
        </button>)}
      </div>
    </Section>}
    <Section title="Identité">
      <Facts items={[
        ['Identifiant stable', <span className="mono">{detail.id}</span>],
        ['Commune INSEE', detail.commune_code ?? 'Non disponible'],
        ...attributes.map(([key, value]): [string, string] => [propertyLabel(key), propertyValue(key, value)]),
      ]} />
    </Section>
  </>
}

function Sources({ detail }: { detail: EntityDetail }) {
  return <Section title="Provenance">
    {detail.sources.map((source, index) => <div className="source-row" key={`${source.data_source_id}:${index}`}>
      <ExternalLink size={15} />
      <span><strong>{source.data_source_id}</strong><small>{source.producer ?? 'Producteur documenté'}{source.release_id ? ` · ${source.release_id}` : ''}</small></span>
    </div>)}
  </Section>
}
