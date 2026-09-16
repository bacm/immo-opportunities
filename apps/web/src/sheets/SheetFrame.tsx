import type { ReactNode } from 'react'
import { X } from 'lucide-react'

/** Cadre commun à toutes les fiches : type, titre, sous-titre, fermeture, contenu défilant. */
export function SheetFrame({ kind, icon, title, subtitle, onClose, children }: {
  kind: string; icon: ReactNode; title: string; subtitle: ReactNode; onClose: () => void; children: ReactNode
}) {
  return <>
    <header className="sheet-head">
      <span className="entity-icon">{icon}</span>
      <div>
        <span className="eyebrow">{kind.toUpperCase()}</span>
        <h2>{title}</h2>
        <p>{subtitle}</p>
      </div>
      <button className="icon-button" onClick={onClose} aria-label="Fermer la fiche"><X size={17} /></button>
    </header>
    <div className="detail-scroll">{children}</div>
  </>
}
