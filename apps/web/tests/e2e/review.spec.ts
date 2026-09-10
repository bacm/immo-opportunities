/**
 * Écran de revue manuelle — B4.
 *
 * L'invariant central se teste ici et nulle part ailleurs : la décision du moteur ne doit
 * apparaître ni à l'écran, ni dans la réponse réseau. Un masquage côté écran serait
 * contournable par une inspection du réseau, et ne prouverait rien.
 */
import { expect, test } from '@playwright/test'

test('le cas à juger ne révèle ni décision ni confiance, dans la réponse réseau', async ({ page }) => {
  const payloads: string[] = []
  page.on('response', async (response) => {
    if (response.url().includes('/api/v1/review/samples/') && response.url().endsWith('/next')) {
      payloads.push(await response.text())
    }
  })

  await page.goto('/')
  // Attendre la réponse elle-même, et non un élément qu'elle finit par produire : sinon le
  // listener peut n'avoir rien collecté au moment de l'assertion, et le test échoue pour une
  // raison de timing qui n'a rien à voir avec ce qu'il vérifie.
  const [response] = await Promise.all([
    page.waitForResponse((candidate) => candidate.url().includes('/api/v1/review/samples/') && candidate.url().endsWith('/next')),
    page.getByRole('button', { name: 'Revue' }).click(),
  ])
  await expect(page.getByRole('heading', { name: /Échantillon b4-/ })).toBeVisible({ timeout: 20_000 })
  payloads.push(await response.text())

  expect(payloads.length).toBeGreaterThan(0)
  for (const body of payloads) {
    for (const leak of ['"decision"', '"confidence"', '"rationale"', '"algorithm_code"', 'certain', 'ambiguous']) {
      expect(body).not.toContain(leak)
    }
  }
})

test('un verdict exige un motif et la mention de ce qui a été consulté', async ({ page }) => {
  await page.goto('/')
  await page.getByRole('button', { name: 'Revue' }).click()
  await expect(page.getByText(/^Cas \d+ ·/)).toBeVisible({ timeout: 20_000 })

  const submit = page.getByRole('button', { name: 'Enregistrer et passer au suivant' })
  await expect(submit).toBeDisabled()

  await page.getByRole('button', { name: 'Correct', exact: true }).click()
  await expect(submit).toBeDisabled()

  await page.getByLabel('Motif').fill('le bâtiment se trouve bien sur la parcelle')
  await expect(submit).toBeDisabled()

  await page.getByLabel('Ce que j’ai consulté').fill('carte au zoom 18, cadastre')
  await expect(submit).toBeEnabled()
})

test('« indécidable » est proposé au même rang que les deux autres verdicts', async ({ page }) => {
  await page.goto('/')
  await page.getByRole('button', { name: 'Revue' }).click()
  await expect(page.getByText(/^Cas \d+ ·/)).toBeVisible({ timeout: 20_000 })

  const group = page.getByRole('group', { name: 'Verdict' })
  await expect(group.getByRole('button', { name: 'Correct', exact: true })).toBeVisible()
  await expect(group.getByRole('button', { name: 'Incorrect' })).toBeVisible()
  await expect(group.getByRole('button', { name: 'Indécidable' })).toBeVisible()
})

test('le dépouillement expose les indécidables à part et l’avancement du lot', async ({ page }) => {
  await page.goto('/')
  await page.getByRole('button', { name: 'Revue' }).click()
  await expect(page.getByRole('heading', { name: 'Dépouillement par strate' })).toBeVisible({ timeout: 20_000 })
  await expect(page.getByRole('columnheader', { name: 'Indécid.' })).toBeVisible()
  await expect(page.getByText(/calculée sur les seuls cas tranchés/)).toBeVisible()
  await expect(page.getByText('180', { exact: false }).first()).toBeVisible()
})
