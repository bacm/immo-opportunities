import { useEffect, useRef, useState, type KeyboardEvent } from 'react'
import { LoaderCircle, Map as MapIcon, MapPin, Search as SearchIcon, X } from 'lucide-react'
import { searchEntities, type SearchResult } from './api'

/**
 * Recherche d'adresse ou de parcelle, au clavier comme à la souris. Plusieurs résultats
 * plausibles donnent une liste, jamais une sélection implicite du premier.
 */
export function Search({ initialQuery, onQueryChange, onChoose }: {
  initialQuery: string
  onQueryChange: (query: string) => void
  onChoose: (result: SearchResult) => void
}) {
  const inputRef = useRef<HTMLInputElement>(null)
  const [query, setQuery] = useState(initialQuery)
  const [results, setResults] = useState<SearchResult[]>([])
  const [open, setOpen] = useState(false)
  const [active, setActive] = useState(0)
  const [loading, setLoading] = useState(false)
  const [failed, setFailed] = useState(false)
  const searching = query.trim().length >= 3

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

  const choose = (result: SearchResult) => {
    setQuery(result.label)
    setOpen(false)
    onChoose(result)
  }

  const onKeyDown = (event: KeyboardEvent<HTMLInputElement>) => {
    if (!open && event.key === 'ArrowDown' && results.length) setOpen(true)
    else if (event.key === 'ArrowDown') setActive((index) => Math.min(index + 1, results.length - 1))
    else if (event.key === 'ArrowUp') setActive((index) => Math.max(index - 1, 0))
    else if (event.key === 'Enter' && results[active]) choose(results[active])
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
        placeholder="Adresse ou parcelle (ex. 35238000BE0253)"
        aria-label="Rechercher"
        aria-autocomplete="list"
        aria-activedescendant={open && results.length ? `search-${active}` : undefined}
      />
      {loading
        ? <LoaderCircle className="spin" size={16} aria-label="Recherche en cours" />
        : query
          ? <button aria-label="Effacer la recherche" onClick={() => { setQuery(''); setOpen(false); inputRef.current?.focus() }}><X size={15} /></button>
          : <kbd>⌘ K</kbd>}
    </div>
    {open && searching && <div className="search-results" id="global-search-results" role="listbox">
      {results.map((result, index) => <button
        id={`search-${index}`}
        role="option"
        aria-selected={index === active}
        className={index === active ? 'active' : ''}
        key={`${result.entity_type}:${result.id}`}
        onMouseEnter={() => setActive(index)}
        onMouseDown={(event) => event.preventDefault()}
        onClick={() => choose(result)}
      >
        <span className="result-icon">{result.entity_type === 'parcel' ? <MapIcon size={15} /> : <MapPin size={15} />}</span>
        <span><strong>{result.label}</strong><small>{result.secondary_label}</small></span>
      </button>)}
      {!loading && failed && <p className="inline-error">Recherche indisponible : le service local ne répond pas.</p>}
      {!loading && !failed && results.length === 0 && <p>Aucune adresse ni parcelle du 35 ne correspond.</p>}
    </div>}
  </div>
}
