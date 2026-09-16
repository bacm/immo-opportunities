import { useId, type KeyboardEvent, type ReactNode } from 'react'

/** Composants de base partagés par toutes les vues. */

export function State({ icon, title, text, action }: { icon: ReactNode; title: string; text: string; action?: ReactNode }) {
  return <div className="empty-state"><span>{icon}</span><strong>{title}</strong><p>{text}</p>{action}</div>
}

export type Tone = 'neutral' | 'good' | 'warn' | 'bad'

export function Chip({ tone = 'neutral', children }: { tone?: Tone; children: ReactNode }) {
  return <span className={`chip chip-${tone}`}>{children}</span>
}

export function Facts({ items }: { items: Array<[string, ReactNode]> }) {
  return <dl className="facts">{items.map(([label, value]) => <div key={label}><dt>{label}</dt><dd>{value}</dd></div>)}</dl>
}

export function KeyFigures({ items }: { items: Array<[string, ReactNode]> }) {
  return <dl className="key-figures">{items.map(([label, value]) => <div key={label}><dt>{label}</dt><dd>{value}</dd></div>)}</dl>
}

export function Section({ title, aside, children }: { title?: string; aside?: ReactNode; children: ReactNode }) {
  return <section className="detail-section">
    {title && <header className="section-head"><h3>{title}</h3>{aside}</header>}
    {children}
  </section>
}

export type TabItem<T extends string> = { id: T; label: string; count?: number | null }

/** Onglets accessibles : flèches gauche/droite, un seul onglet dans l'ordre de tabulation. */
export function Tabs<T extends string>({ items, active, onChange, label }: {
  items: TabItem<T>[]; active: T; onChange: (id: T) => void; label: string
}) {
  const base = useId()
  const move = (event: KeyboardEvent<HTMLDivElement>) => {
    if (event.key !== 'ArrowRight' && event.key !== 'ArrowLeft') return
    const index = items.findIndex((item) => item.id === active)
    const next = items[(index + (event.key === 'ArrowRight' ? 1 : items.length - 1)) % items.length]
    onChange(next.id)
    document.getElementById(`${base}-${next.id}`)?.focus()
    event.preventDefault()
  }
  return <div className="tabs" role="tablist" aria-label={label} onKeyDown={move}>
    {items.map((item) => <button
      key={item.id}
      id={`${base}-${item.id}`}
      role="tab"
      aria-selected={item.id === active}
      tabIndex={item.id === active ? 0 : -1}
      className={item.id === active ? 'active' : ''}
      onClick={() => onChange(item.id)}
    >
      {item.label}
      {item.count !== undefined && <span className="tab-count">{item.count === null ? '…' : item.count}</span>}
    </button>)}
  </div>
}
