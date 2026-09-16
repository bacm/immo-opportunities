import { LoaderCircle } from 'lucide-react'
import type { ParcelEnergyAssessment } from '../api'
import { entityLabel, formatArea, formatDate } from '../format'
import { Chip, State } from '../ui'
import type { Loaded } from './useLoad'

/** Plafond d'affichage, annoncé à l'écran et jamais silencieux : une parcelle rennaise porte
 *  jusqu'à 526 diagnostics. Rendre les 526 noierait la vérification ; les couper sans le dire
 *  ferait croire à une couverture complète. Le compte total reste affiché. */
const DISPLAY_LIMIT = 50

/**
 * Les diagnostics DPE d'une parcelle — instrument de vérification D6b, pas fonctionnalité produit.
 *
 * Il met à l'épreuve une hypothèse que rien n'a contrôlée : la confiance d'appariement vaut 1,0
 * pour tous, parce que l'`id_rnb` est déclaré par le producteur et repris tel quel. D'où la
 * provenance de l'identifiant, montrée diagnostic par diagnostic.
 *
 * **Aucune couleur de A à G**, ici ni sur la carte : une classe F rendue en rouge deviendrait un
 * signal de dégradation, et une observation de diagnostic n'est pas une preuve d'état du bâti.
 * L'étiquette est une pastille neutre. Aucune agrégation non plus — pas d'étiquette « dominante »
 * sur la parcelle, qui fabriquerait une valeur n'existant nulle part.
 */
export function ParcelDiagnostics({ loaded }: { loaded: Loaded<ParcelEnergyAssessment[]> }) {
  if (loaded.status === 'failed') {
    return <p className="inline-error" role="alert">Diagnostics indisponibles : le service local n’a pas répondu. Rien n’est affirmé sur cette parcelle.</p>
  }
  if (loaded.status === 'loading') return <State icon={<LoaderCircle className="spin" />} title="Chargement des diagnostics" text="Lecture des DPE rattachés aux bâtiments de la parcelle." />
  const rows = loaded.value
  if (rows.length === 0) return <p className="unknown-value">Aucun diagnostic rattaché aux bâtiments de cette parcelle.</p>
  const ambiguous = rows.filter((row) => row.relation_status !== 'certain').length
  const newBuild = rows.filter((row) => row.data_source_id === 'DS-13').length

  // `assessment-*` distingue ces lignes de celles des ventes à l'inspection.
  return <>
    <ol className="record-list assessment-list">
      {rows.slice(0, DISPLAY_LIMIT).map((row) => {
        const certain = row.relation_status === 'certain'
        return <li className="record assessment-row" key={row.dpe_number}>
          <header>
            <span className="energy-label" aria-label={`Étiquette ${row.energy_label ?? 'absente'}`}>{row.energy_label ?? '?'}</span>
            <span className="record-title">
              {row.energy_consumption_kwh_m2_year !== null
                ? `${Math.round(row.energy_consumption_kwh_m2_year)} kWh/m²/an`
                : 'consommation absente'}
            </span>
            <span className="record-sub">
              {formatDate(row.assessment_date)}
              {row.building_type ? ` · ${row.building_type}` : ''}
              {/* Surface montrée telle quelle, aucun ratio dérivé : le produit ne juge pas un
                  DPE, il vérifie qu'il est au bon endroit. */}
              {` · ${formatArea(row.surface_habitable_m2, 'surface non déclarée')}`}
            </span>
            <span className="record-side">
              {/* DS-13 : diagnostic établi à la réception d'une construction (ADR-021). */}
              <Chip>{row.data_source_id === 'DS-13' ? 'Neuf' : 'Existant'}</Chip>
              <Chip tone={certain ? 'good' : 'warn'}>{certain ? 'Rattachement certain' : 'Rattachement ambigu'}</Chip>
            </span>
          </header>
          <p className="record-note">{row.address_label ?? 'Adresse du diagnostic absente'}</p>
          <p className="record-note mono">
            DPE {row.dpe_number}
            {row.building_id ? <> · <span title={row.building_id}>{entityLabel('building', row.building_id, row.building_id)}</span></> : ''}
            {' · '}Identifiant RNB : {row.identifier_provenance ?? 'provenance absente'}
          </p>
        </li>
      })}
    </ol>
    <p className="detail-note">
      {rows.length} diagnostic{rows.length > 1 ? 's' : ''} sur cette parcelle
      {rows.length > DISPLAY_LIMIT ? `, dont ${DISPLAY_LIMIT} affichés` : ''}
      {ambiguous > 0 ? ` · ${ambiguous} par un bâtiment qui chevauche plusieurs parcelles` : ''}
      {newBuild > 0 ? ` · ${newBuild} de logement neuf, établi${newBuild > 1 ? 's' : ''} à la réception de la construction, qu’aucune mesure du marché ne lit` : ''}. Les diagnostics rattachés à la seule adresse n’apparaissent pas ici : la relation
      adresse ↔ parcelle n’est vérifiable par aucune règle géométrique, et l’inventer placerait
      un diagnostic sur environ une parcelle sur quatre à tort. Une étiquette est l’observation
      d’un diagnostic déposé, pas une preuve d’état du bâti.
    </p>
  </>
}
