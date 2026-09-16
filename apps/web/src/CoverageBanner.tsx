import { CheckCircle2, TriangleAlert } from 'lucide-react'
import type { CommuneCoverage } from './api'

/**
 * État de couverture du territoire observé.
 *
 * La distinction que porte ce composant est une exigence produit, pas un détail d'affichage :
 * « territoire non couvert » et « aucun résultat » se ressemblent à l'écran et signifient le
 * contraire l'un de l'autre. Confondre les deux ferait lire une fiche vide comme un fait, alors
 * que le territoire n'a jamais été importé.
 *
 * Placé au-dessus de la grille, il est partagé par la carte et la fiche.
 */
export function CoverageBanner({ coverage }: { coverage: CommuneCoverage }) {
  const territory = coverage.commune_name ?? coverage.commune_code
  if (coverage.state === 'covered') {
    return <div className="coverage-banner covered" role="status">
      <CheckCircle2 size={15} />
      <span><strong>{territory} · territoire couvert</strong><small>Les cinq sources du référentiel spatial sont actives ici. Une fiche sans rattachement signifie que la base n’en connaît aucun.</small></span>
    </div>
  }
  if (coverage.state === 'not_covered') {
    return <div className="coverage-banner not-covered" role="status">
      <TriangleAlert size={15} />
      <span><strong>{territory} · territoire non couvert</strong><small>Aucune source active sur ce territoire. Une fiche vide ne veut rien dire ici : la donnée n’a pas été importée.</small></span>
    </div>
  }
  return <div className="coverage-banner partial" role="status">
    <TriangleAlert size={15} />
    <span><strong>{territory} · données partielles</strong><small>Rattachements incomplets. Sources absentes : {coverage.missing_sources.join(', ')}.</small></span>
  </div>
}
