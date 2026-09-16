import { useEffect, useState } from 'react'

import { failureReference } from '../api'

/**
 * Trois états, jamais deux : une panne n'est pas une absence. « Aucune mutation » sur un 500
 * affirmerait un fait que la base n'a pas dit.
 */
export type Loaded<T> =
  | { status: 'loading' }
  | { status: 'failed'; reference?: string }
  | { status: 'ready'; value: T }

export function useLoad<T>(key: string, load: (key: string, signal: AbortSignal) => Promise<T>): Loaded<T> {
  const [state, setState] = useState<{ key: string; loaded: Loaded<T> }>({ key, loaded: { status: 'loading' } })

  useEffect(() => {
    const controller = new AbortController()
    setState({ key, loaded: { status: 'loading' } })
    load(key, controller.signal)
      .then((value) => setState({ key, loaded: { status: 'ready', value } }))
      .catch((error: unknown) => {
        if ((error as Error).name !== 'AbortError') {
          setState({ key, loaded: { status: 'failed', reference: failureReference(error) } })
        }
      })
    return () => controller.abort()
  }, [key, load])

  // Un résultat n'est rendu que pour la clé qui l'a demandé : passer d'une parcelle à sa voisine
  // ne peut pas montrer, même un instant, les ventes de la précédente. Signalé sur
  // 35024000AP0206, qui affichait les deux ventes de sa voisine AP0207 (D6a).
  return state.key === key ? state.loaded : { status: 'loading' }
}
