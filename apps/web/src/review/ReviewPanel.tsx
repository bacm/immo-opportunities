import { useCallback, useEffect, useMemo, useRef, useState, type FormEvent } from 'react'
import { CheckCircle2, TriangleAlert, X } from 'lucide-react'
import {
  loadCaseContext,
  loadNextReviewCase,
  loadReviewProgress,
  loadReviewResults,
  submitReviewVerdict,
  type BlindCase,
  type CaseContext,
  type ReviewProgress,
  type StratumResult,
} from '../api'
import ReviewMap from './ReviewMap'
import { State } from '../ui'

/**
 * Les deux objets du cas, superposés à la même échelle.
 *
 * L'écran précédent centrait la carte sur **un seul** des deux et laissait deviner l'autre :
 * un décalage se lisait alors comme un signal, alors qu'il ne disait rien. Ici les deux formes
 * sont dessinées ensemble, dans le même repère, avec une échelle — la question « se
 * correspondent-elles ? » devient regardable.
 *
 * Montrer où sont les objets n'est pas montrer ce que le moteur en a conclu : la décision et la
 * confiance restent absentes de la réponse d'API.
 */
function CasePreview({ leftGeoJson, rightGeoJson }: { leftGeoJson: string | null; rightGeoJson: string | null }) {
  const shapes = useMemo(() => {
    const collect = (raw: string | null): number[][][] => {
      if (!raw) return []
      try {
        const parsed = JSON.parse(raw) as { type: string; coordinates: unknown }
        const rings: number[][][] = []
        const walk = (node: unknown, depth: number) => {
          if (!Array.isArray(node)) return
          if (depth === 0 && typeof node[0] === 'number') return
          if (Array.isArray(node[0]) && typeof (node[0] as unknown[])[0] === 'number') {
            rings.push(node as number[][])
            return
          }
          for (const child of node) walk(child, depth + 1)
        }
        if (parsed.type === 'Point') {
          const point = parsed.coordinates as number[]
          rings.push([point])
        } else walk(parsed.coordinates, 0)
        return rings
      } catch { return [] }
    }
    return { left: collect(leftGeoJson), right: collect(rightGeoJson) }
  }, [leftGeoJson, rightGeoJson])

  const all = [...shapes.left, ...shapes.right].flat()
  if (all.length === 0) return <p className="detail-note">Aucune géométrie exploitable pour ce cas : il faut consulter les sources directement.</p>

  const xs = all.map((point) => point[0])
  const ys = all.map((point) => point[1])
  const minX = Math.min(...xs), maxX = Math.max(...xs)
  const minY = Math.min(...ys), maxY = Math.max(...ys)
  // Marge de 12 % pour que rien ne touche le bord, et garde-fou sur un cas ponctuel où
  // l'étendue serait nulle.
  const spanX = Math.max(maxX - minX, 1e-6) * 1.24
  const spanY = Math.max(maxY - minY, 1e-6) * 1.24
  const centreX = (minX + maxX) / 2, centreY = (minY + maxY) / 2
  const span = Math.max(spanX, spanY)
  const project = (point: number[]) => [
    ((point[0] - (centreX - span / 2)) / span) * 300,
    300 - ((point[1] - (centreY - span / 2)) / span) * 300,
  ]
  // Un degré de latitude vaut ~111 km ; l'échelle affichée est donc indicative mais suffit à
  // savoir si l'on regarde 20 m ou 200 m.
  const metres = Math.round(span * 111_320)

  const draw = (rings: number[][][], className: string) => rings.map((ring, index) =>
    ring.length === 1
      ? <circle key={`${className}-${index}`} className={className} cx={project(ring[0])[0]} cy={project(ring[0])[1]} r={5} />
      : <polygon key={`${className}-${index}`} className={className} points={ring.map((point) => project(point).join(',')).join(' ')} />)

  return <figure className="case-preview">
    <svg viewBox="0 0 300 300" role="img" aria-label="Les deux objets du cas, superposés">
      {draw(shapes.right, 'shape-right')}
      {draw(shapes.left, 'shape-left')}
    </svg>
    <figcaption>
      <span className="legend-left" /> objet de gauche
      <span className="legend-right" /> objet de droite
      <em>largeur ≈ {metres} m</em>
    </figcaption>
  </figure>
}

/**
 * Écran de revue manuelle — B4.
 *
 * Le relecteur ne voit **jamais** la décision du moteur : l'API ne la lui envoie pas. Ce n'est
 * donc pas un masquage côté écran, qu'une inspection du réseau contournerait, mais une absence
 * à la source. Sans cela la revue mesurerait l'accord avec le moteur, pas l'exactitude.
 *
 * L'écran affiche ce qu'il faut pour aller regarder la donnée d'origine : les identifiants des
 * deux côtés, la commune, et un lien vers la carte au bon endroit. Le protocole demande de
 * consulter les sources, pas de trancher au jugé — d'où le champ « ce que j'ai consulté », qui
 * est obligatoire.
 */
export function ReviewPanel({ sampleId, reviewer, onClose }: { sampleId: string; reviewer: string; onClose: () => void }) {
  const [progress, setProgress] = useState<ReviewProgress | null>(null)
  const [current, setCurrent] = useState<BlindCase | null>(null)
  const [context, setContext] = useState<CaseContext | null>(null)
  const [results, setResults] = useState<StratumResult[]>([])
  const [verdict, setVerdict] = useState<'correct' | 'incorrect' | 'undecidable' | ''>('')
  const [rationale, setRationale] = useState('')
  const [evidence, setEvidence] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [finished, setFinished] = useState(false)
  // Orthophoto par défaut : c'est la vue que le relecteur allait chercher ailleurs.
  const [reviewOrthophoto, setReviewOrthophoto] = useState(true)

  const refresh = useCallback(async () => {
    setError('')
    try {
      const [nextProgress, nextResults] = await Promise.all([
        loadReviewProgress(sampleId),
        loadReviewResults(sampleId),
      ])
      setProgress(nextProgress)
      setResults(nextResults)
      try {
        const nextCase = await loadNextReviewCase(sampleId)
        setCurrent(nextCase)
        setFinished(false)
        // Le voisinage lève les doutes que la seule paire ne permet pas de trancher :
        // « c'est peut-être un bis », « cette adresse couvre plusieurs parcelles ».
        try { setContext(await loadCaseContext(nextCase.id)) } catch { setContext(null) }
      } catch {
        // 404 : plus aucun cas à juger. C'est une fin normale, pas une erreur.
        setCurrent(null)
        setContext(null)
        setFinished(true)
      }
    } catch (caught) {
      setError((caught as Error).message)
    }
  }, [sampleId])

  useEffect(() => { void refresh() }, [refresh])

  const submit = async (event: FormEvent) => {
    event.preventDefault()
    if (!current || !verdict) return
    setBusy(true)
    setError('')
    try {
      await submitReviewVerdict({
        case_id: current.id, verdict, reviewer,
        rationale: rationale.trim(), evidence_consulted: evidence.trim(),
      })
      setVerdict(''); setRationale(''); setEvidence('')
      await refresh()
    } catch (caught) {
      setError((caught as Error).message)
    } finally { setBusy(false) }
  }

  const located = current && current.longitude !== null && current.latitude !== null
  const mapHref = located
    ? `/?lon=${current.longitude!.toFixed(6)}&lat=${current.latitude!.toFixed(6)}&z=18.00`
    : null
  // Le relecteur va systématiquement vérifier sur une vue aérienne : lui faire chercher le
  // lieu à la main était le principal coût par cas, et pour un bâtiment BD TOPO — qui n'a ni
  // adresse ni libellé humain — c'était tout simplement impossible.
  const aerialHref = located
    ? `https://www.google.com/maps/@${current.latitude!.toFixed(6)},${current.longitude!.toFixed(6)},19z/data=!3m1!1e3`
    : null

  // `<dialog>` ouvert par `showModal()` : le navigateur retient le focus dans la revue, rend le
  // reste inerte et ferme sur Échap — ce qu'aucun `div` ne faisait.
  const dialogRef = useRef<HTMLDialogElement>(null)
  useEffect(() => {
    const dialog = dialogRef.current
    if (dialog && !dialog.open) dialog.showModal()
  }, [])

  const share = progress && progress.total_cases > 0 ? progress.judged_cases / progress.total_cases : null

  return <dialog ref={dialogRef} className="review-dialog" aria-labelledby="review-title" onClose={onClose}>
    <section className="admin-panel">
      <header>
        <div><span className="eyebrow">REVUE MANUELLE</span><h2 id="review-title">Échantillon {sampleId}</h2></div>
        {progress && <div className="review-progress" title={progress.size_rationale}>
          <span>{progress.judged_cases} / {progress.total_cases} cas jugés</span>
          {share !== null && <progress max={1} value={share} aria-label="Avancement de l’échantillon" />}
        </div>}
        <button className="icon-button" aria-label="Fermer la revue" onClick={() => dialogRef.current?.close()}><X size={17} /></button>
      </header>
      <div className="admin-content">
        {error && <State icon={<TriangleAlert />} title="Enregistrement impossible" text={error} />}
        {finished && <State icon={<CheckCircle2 />} title="Échantillon entièrement jugé" text="Tous les cas tirés portent un verdict. Le dépouillement par strate est ci-dessous." />}

        {current && <div className="review-body">
          <section className="detail-section review-case">
            <h3>Cas {current.case_ref} · {current.territorial_stratum}</h3>
            <p className="review-question">{current.question}</p>
            <p className="detail-note">{current.purpose}</p>
            <p className="detail-note">{current.out_of_scope}</p>
            {current.longitude !== null && current.latitude !== null
              ? <>
                  <ReviewMap
                    leftGeoJson={current.left_geojson} rightGeoJson={current.right_geojson}
                    longitude={current.longitude} latitude={current.latitude}
                    orthophoto={reviewOrthophoto}
                  />
                  <ul className="review-legend">
                    <li><span className="swatch swatch-left" /> Objet de gauche</li>
                    <li><span className="swatch swatch-right" /> Objet de droite</li>
                    {!reviewOrthophoto && <li><span className="swatch swatch-parcel" /> Parcelles — fond de plan, hors jugement</li>}
                  </ul>
                  {current.left_on_right_ratio !== null && current.left_on_right_ratio > 0.99 && <p className="detail-note">
                    Les deux emprises coïncident à {(current.left_on_right_ratio * 100).toFixed(0)} % :
                    une seule forme est visible, les deux contours se superposent.
                  </p>}
                  <div className="map-mode review-map-mode" role="group" aria-label="Fond de la carte de revue">
                    <button className={!reviewOrthophoto ? 'active' : ''} onClick={() => setReviewOrthophoto(false)}>Parcelles</button>
                    <button className={reviewOrthophoto ? 'active' : ''} onClick={() => setReviewOrthophoto(true)}>Orthophoto IGN</button>
                  </div>
                </>
              : <CasePreview leftGeoJson={current.left_geojson} rightGeoJson={current.right_geojson} />}
            <dl className="facts">
              <div><dt>Commune</dt><dd>{current.commune_name ?? current.commune_code}</dd></div>
              <div><dt>Objet de gauche</dt><dd>{current.left_label}{current.left_area_m2 ? ` · ${Math.round(current.left_area_m2)} m²` : ''}</dd></div>
              <div><dt>Objet de droite</dt><dd>{current.right_label}{current.right_area_m2 ? ` · ${Math.round(current.right_area_m2)} m²` : ''}</dd></div>
              {current.left_on_right_ratio !== null && <div>
                <dt>{current.right_kind === 'building' ? 'Recouvrement des deux emprises' : 'Part de gauche sur droite'}</dt>
                <dd className={current.left_on_right_ratio < 0.1 ? 'value-warning' : undefined}>
                  {(current.left_on_right_ratio * 100).toFixed(1)} %
                </dd>
              </div>}
            </dl>
            {current.left_on_right_ratio !== null && current.left_on_right_ratio < 0.1 && <p className="detail-note">
              {current.right_kind === 'building'
                ? 'Les deux emprises ne se recouvrent presque pas : ce sont vraisemblablement deux bâtiments différents.'
                : 'L’objet de gauche ne touche celui de droite que sur une fraction de sa surface. À vous de juger si cela suffit à dire qu’il y est situé — c’est exactement la question que pose ce cas.'}
            </p>}
            {current.left_on_right_ratio !== null && current.left_on_right_ratio > 0.99 && current.right_kind === 'building' && <p className="detail-note">
              Les deux emprises coïncident : à l’écran elles se superposent, et le contour tireté
              est celui de l’objet de droite.
            </p>}
            {context && context.sibling_addresses.length > 0 && <div className="case-context">
              <h4>Adresses au même numéro</h4>
              {context.sibling_addresses.length === 1
                ? <p className="detail-note">Aucun <em>bis</em> ni <em>ter</em> à ce numéro : une seule adresse y existe.</p>
                : <ul>{context.sibling_addresses.map((sibling) => <li key={sibling.display_label} className={sibling.is_case ? 'is-case' : ''}>{sibling.display_label}{sibling.repetition_index ? ` (${sibling.repetition_index})` : ''}{sibling.is_case ? ' ← le cas' : ''}</li>)}</ul>}
            </div>}
            {context && context.related_parcels.length > 1 && <div className="case-context">
              <h4>Parcelles rattachées à cette adresse</h4>
              <ul>{context.related_parcels.map((parcel) => <li key={parcel.cadastral_id} className={parcel.is_case ? 'is-case' : ''}>{parcel.cadastral_id}{parcel.area_m2 ? ` · ${Math.round(parcel.area_m2)} m²` : ''}{parcel.is_case ? ' ← le cas' : ''}</li>)}</ul>
              <p className="detail-note">Cette adresse en couvre {context.related_parcels.length}. Être l’une d’elles n’est pas une erreur.</p>
            </div>}
            {context && context.nearby_addresses.length > 0 && <div className="case-context">
              <h4>Adresses proches — repères, pas appariements</h4>
              <ul>{context.nearby_addresses.map((nearby) => <li key={nearby.display_label}>{nearby.display_label} · {Math.round(nearby.distance_m)} m</li>)}</ul>
              <p className="detail-note">Aucune n’est déclarée correspondre à cet objet. Elles servent à le situer, comme un nom de rue sur une carte.</p>
            </div>}
            <p className="detail-note review-links">
              {mapHref && <a href={mapHref} target="_blank" rel="noreferrer">Ouvrir sur la carte, zoom 18</a>}
              {aerialHref && <a href={aerialHref} target="_blank" rel="noreferrer">Vue aérienne</a>}
              {located && <span>{current.latitude!.toFixed(6)}, {current.longitude!.toFixed(6)}</span>}
            </p>
          </section>
          <aside className="detail-section review-side">
            <h3>Verdict</h3>
            <form className="review-form" onSubmit={submit}>
              <div className="review-verdicts" role="group" aria-label="Verdict">
                {([['correct', 'Correct'], ['incorrect', 'Incorrect'], ['undecidable', 'Indécidable']] as const).map(([value, label]) =>
                  <button key={value} type="button" className={verdict === value ? 'active' : ''} onClick={() => setVerdict(value)}>{label}</button>)}
              </div>
              <label>Motif<textarea value={rationale} maxLength={2000} onChange={(event) => setRationale(event.target.value)} placeholder="Pourquoi ce verdict…" /></label>
              <label>Ce que j’ai consulté<input value={evidence} maxLength={500} onChange={(event) => setEvidence(event.target.value)} placeholder="carte, BAN, cadastre…" /></label>
              <button type="submit" disabled={busy || !verdict || rationale.trim().length < 3 || evidence.trim().length < 3}>Enregistrer et passer au suivant</button>
            </form>
            <p className="detail-note">« Indécidable » est un résultat valide. Ne pas le forcer : un cas indécidable n’est jamais compté comme correct.</p>
          </aside>
        </div>}

        {progress && <section className="detail-section">
          <h3>Protocole</h3>
          <dl className="facts">
            <div><dt>Cas jugés</dt><dd>{progress.judged_cases} / {progress.total_cases}</dd></div>
            <div><dt>Graine</dt><dd>{progress.seed}</dd></div>
            <div><dt>Protocole</dt><dd className="mono">{progress.protocol_document}</dd></div>
          </dl>
          <p className="detail-note">{progress.size_rationale}</p>
        </section>}

        {results.length > 0 && <section className="detail-section">
          <h3>Dépouillement par strate</h3>
          <div className="review-results">
            <table>
              <thead><tr><th>Appariement</th><th>Territoire</th><th>Tirés</th><th>Jugés</th><th>Abandonnés</th><th>Corrects</th><th>Incorrects</th><th>Indécid.</th><th>Exactitude</th></tr></thead>
              <tbody>{results.map((row) => <tr key={`${row.matching_stratum}:${row.territorial_stratum}`}>
                <td>{row.matching_stratum}</td><td>{row.territorial_stratum}</td>
                <td>{row.drawn}</td><td>{row.judged}</td>
                <td className={row.abandoned > 0 ? 'value-warning' : undefined}>{row.abandoned || '—'}</td>
                <td>{row.correct}</td>
                <td>{row.incorrect}</td><td>{row.undecidable}</td>
                <td>{row.accuracy === null ? '—' : `${(row.accuracy * 100).toFixed(1)} %`}</td>
              </tr>)}</tbody>
            </table>
          </div>
          <p className="detail-note">L’exactitude est calculée sur les seuls cas tranchés. Les indécidables ont leur colonne et ne gonflent aucun taux. Un cas abandonné n’a jamais été jugé et ne le sera pas : le motif de l’abandon est en base, et une strate abandonnée ne peut plus conclure à un taux d’erreur, seulement le constater.</p>
        </section>}
      </div>
    </section>
  </dialog>
}
