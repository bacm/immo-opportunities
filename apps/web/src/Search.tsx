import { useEffect, useRef, useState, type KeyboardEvent } from 'react'
import { Gauge, LoaderCircle, Map as MapIcon, MapPin, Search as SearchIcon, X } from 'lucide-react'
import { searchEntities, type SearchResult } from './api'
import { asDpeNumber } from './format'

type Option = { kind: 'dpe'; number: string } | { kind: 'entity'; result: SearchResult }

/**
 * Recherche d'adresse, de parcelle ou de numéro de DPE, au clavier comme à la souris. Plusieurs
 * résultats plausibles donnent une liste, jamais une sélection implicite du premier.
 */

export function Search({ initialQuery, onQueryChange, onChoose, onChooseDpe }: {
  initialQuery: string
  onQueryChange: (query: string) => void
  onChoose: (result: SearchResult) => void
  onChooseDpe: (dpeNumber: string) => void
}) {
  const inputRef = useRef<HTMLInputElement>(null)
  const [query, setQuery] = useState(initialQuery)
  const [results, setResults] = useState<SearchResult[]>([])
  const [open, setOpen] = useState(false)
  const [active, setActive] = useState(0)
  const [loading, setLoading] = useState(false)
  const [failed, setFailed] = useState(false)
  const searching = query.trim().length >= 3
  // Un numéro de DPE ne se cherche pas dans le référentiel : il ouvre directement sa fiche (C7).
  const dpeNumber = asDpeNumber(query)
  const options: Option[] = [
    ...(dpeNumber ? [{ kind: 'dpe', number: dpeNumber } as const] : []),
    ...results.map((result) => ({ kind: 'entity', result }) as const),
  ]

  useEffect(() => onQueryChange(query), [query, onQueryChange])

  useEffect(() => {
    const handler = (event: globalThis.KeyboardEvent) => {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === 'k') {
        event.preventDefault()
        inputRef.current?.focus()
      }
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [])

  useEffect(() => {
    const normalized = query.trim()
    if (normalized.length < 3) {
      setResults([])
      setLoading(false)
      setFailed(false)
      return
    }
    const controller = new AbortController()
    const timeout = window.setTimeout(() => {
      setLoading(true)
      searchEntities(normalized, controller.signal)
        .then((found) => { setResults(found); setFailed(false); setActive(0) })
        .catch((error: unknown) => {
          if ((error as Error).name === 'AbortError') return
          setResults([])
          setFailed(true)
        })
        .finally(() => setLoading(false))
    }, 220)
    return () => { window.clearTimeout(timeout); controller.abort() }
  }, [query])

  const choose = (option: Option) => {
    setOpen(false)
    if (option.kind === 'dpe') {
      setQuery(option.number)
      onChooseDpe(option.number)
      return
    }
    setQuery(option.result.label)
    onChoose(option.result)
  }

  const onKeyDown = (event: KeyboardEvent<HTMLInputElement>) => {
    if (!open && event.key === 'ArrowDown' && options.length) setOpen(true)
    else if (event.key === 'ArrowDown') setActive((index) => Math.min(index + 1, options.length - 1))
    else if (event.key === 'ArrowUp') setActive((index) => Math.max(index - 1, 0))
    else if (event.key === 'Enter' && options[active]) choose(options[active])
    else if (event.key === 'Escape') setOpen(false)
    else return
    event.preventDefault()
  }

  return <div className="search-wrap">
    <div className="searchbox" role="combobox" aria-expanded={open && searching} aria-haspopup="listbox" aria-controls="global-search-results">
      <SearchIcon size={17} />
      <input
        ref={inputRef}
        value={query}
        onChange={(event) => { setQuery(event.target.value); setOpen(true) }}
        onFocus={() => setOpen(true)}
        onBlur={() => window.setTimeout(() => setOpen(false), 150)}
        onKeyDown={onKeyDown}
        placeholder="Adresse, parcelle ou numéro de DPE"
        aria-label="Rechercher"
        aria-autocomplete="list"
        aria-activedescendant={open && options.length ? `search-${active}` : undefined}
      />
      {loading
        ? <LoaderCircle className="spin" size={16} aria-label="Recherche en cours" />
        : query
          ? <button aria-label="Effacer la recherche" onClick={() => { setQuery(''); setOpen(false); inputRef.current?.focus() }}><X size={15} /></button>
          : <kbd>⌘ K</kbd>}
    </div>
    {open && searching && <div className="search-results" id="global-search-results" role="listbox">
      {options.map((option, index) => <button
        id={`search-${index}`}
        role="option"
        aria-selected={index === active}
        className={index === active ? 'active' : ''}
        key={option.kind === 'dpe' ? `dpe:${option.number}` : `${option.result.entity_type}:${option.result.id}`}
        onMouseEnter={() => setActive(index)}
        onMouseDown={(event) => event.preventDefault()}
        onClick={() => choose(option)}
      >
        {option.kind === 'dpe'
          ? <>
              <span className="result-icon"><Gauge size={15} /></span>
              <span><strong>Diagnostic DPE {option.number}</strong><small>Conservé ou écarté à l’import, avec son motif</small></span>
            </>
          : <>
              <span className="result-icon">{option.result.entity_type === 'parcel' ? <MapIcon size={15} /> : <MapPin size={15} />}</span>
              <span><strong>{option.result.label}</strong><small>{option.result.secondary_label}</small></span>
            </>}
      </button>)}
      {!loading && failed && <p className="inline-error">Recherche indisponible : le service local ne répond pas.</p>}
      {!loading && !failed && options.length === 0 && <p>Aucune adresse, parcelle ni numéro de DPE du 35 ne correspond.</p>}
    </div>}
  </div>
}
