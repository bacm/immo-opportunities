import { useId } from 'react'
import { CheckCircle2, TriangleAlert } from 'lucide-react'
import type { CommuneCoverage } from './api'

/**
 * État de couverture du territoire observé, en pastille dans la barre du haut (C6).
 *
 * La distinction que porte ce composant est une exigence produit, pas un détail d'affichage :
 * « territoire non couvert » et « aucun résultat » se ressemblent à l'écran et signifient le
 * contraire l'un de l'autre. Confondre les deux ferait lire une fiche vide comme un fait, alors
 * que le territoire n'a jamais été importé.
 *
 * La pastille nomme toujours sa commune ; le texte complet est dans l'infobulle, ouverte au
 * survol comme au focus clavier.
 */
export function CoverageBadge({ coverage }: { coverage: CommuneCoverage }) {
  const tooltipId = useId()
  const territory = coverage.commune_name ?? coverage.commune_code
  const [tone, state, detail] = coverage.state === 'covered'
    ? ['covered', 'territoire couvert', 'Les cinq sources du référentiel spatial sont actives ici. Une fiche sans rattachement signifie que la base n’en connaît aucun.']
    : coverage.state === 'not_covered'
      ? ['not-covered', 'territoire non couvert', 'Aucune source active sur ce territoire. Une fiche vide ne veut rien dire ici : la donnée n’a pas été importée.']
      : ['partial', 'données partielles', `Rattachements incomplets. Sources absentes : ${coverage.missing_sources.join(', ')}.`]
  return <div className={`coverage-badge ${tone}`}>
    <button type="button" aria-describedby={tooltipId}>
      {coverage.state === 'covered' ? <CheckCircle2 size={15} aria-hidden="true" /> : <TriangleAlert size={15} aria-hidden="true" />}
      <span>{territory} · {state}</span>
    </button>
    <div role="tooltip" id={tooltipId} className="coverage-tooltip">{detail}</div>
  </div>
}
