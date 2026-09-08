/**
 * Captures de démonstration C3 — sur données réelles, sans fixture.
 *
 * Ces captures sont une **preuve**, pas une illustration : elles montrent que la chaîne
 * fonctionne de bout en bout sur les releases citées dans `real-map-address-demo-35.md`.
 * Elles ne sont donc pas exécutées avec le reste de la suite — `pnpm test:e2e` les ignore —
 * mais par `pnpm capture:demo`, qui les régénère volontairement.
 *
 * Aucune route n'est interceptée : chaque écran vient de l'API réelle sur la base du 35.
 */
import { expect, test } from '@playwright/test'

const CAPTURES = '../../docs/data/captures'

// Adresse réelle d'Acigné portant à la fois un appariement certain et un ambigu — le cas
// intéressant, choisi pour cela et non parce qu'il « marche bien ».
const MIXED_ADDRESS = '2 Rue Agatha Christie'
const MIXED_ADDRESS_ID = 'address:ban:35001_0001_00002'
// Une des 216 adresses réelles dont la position est retenue par la quarantaine BUG-03.
const UNPOSITIONED_ADDRESS_ID = 'address:ban:35002_3n5z8h_00006'

test.describe('captures de démonstration sur données réelles', () => {
  test('recherche, fiche, appariements et couverture', async ({ page }) => {
    await page.goto('/')
    await page.waitForLoadState('networkidle')
    await page.screenshot({ path: `${CAPTURES}/01-explorer-initial.png`, fullPage: false })

    const search = page.getByRole('textbox', { name: 'Rechercher' })
    await search.fill('rue agatha christie acigne')
    await expect(page.getByRole('option', { name: new RegExp(MIXED_ADDRESS, 'i') }).first()).toBeVisible({ timeout: 20_000 })
    await page.screenshot({ path: `${CAPTURES}/02-recherche-adresse-reelle.png` })

    // Ouvrir le cas visé par son URL partageable, plutôt qu'en naviguant dans une liste qui se
    // réordonne au survol. L'URL est une fonctionnalité du produit — la capture la démontre en
    // même temps qu'elle rend la séquence reproductible à l'identique.
    // Le cadrage fait partie de l'URL : sans zoom suffisant, les tuiles ne sont pas servies —
    // `parcels` déclare minzoom 13, ce qui interdit tout rendu régional (ADR MapLibre).
    await page.goto(`/?address=${encodeURIComponent(MIXED_ADDRESS_ID)}&lon=-1.542000&lat=48.135000&z=16.00`)
    await expect(page.getByText('ADRESSE', { exact: true })).toBeVisible({ timeout: 20_000 })
    await page.waitForLoadState('networkidle')
    await expect(page.getByRole('heading', { name: 'Appariements certains' })).toBeVisible()
    await expect(page.getByRole('heading', { name: 'Appariements ambigus' })).toBeVisible()
    await page.screenshot({ path: `${CAPTURES}/03-fiche-adresse-certain-et-ambigu.png` })

    // L'état de couverture, avec la source manquante nommée.
    await expect(page.getByText(/données partielles|territoire couvert/)).toBeVisible({ timeout: 20_000 })
    await page.screenshot({ path: `${CAPTURES}/04-couverture-sources-nommees.png` })

    // L'ambiguïté n'est pas masquée : elle a sa propre section, sous les appariements certains.
    await page.locator('.detail-scroll').evaluate((panel) => { panel.scrollTop = panel.scrollHeight })
    await expect(page.getByRole('heading', { name: 'Appariements ambigus' })).toBeInViewport()
    await page.screenshot({ path: `${CAPTURES}/05-appariement-ambigu-visible.png` })

    // La liste dit la vraie raison de son vide : aucun score publié, pas un territoire vide.
    await expect(page.getByText('Aucun candidat publié')).toBeVisible()
    await page.screenshot({ path: `${CAPTURES}/06-absence-motivee.png` })
  })

  test('valeur absente avec son motif — FR-007', async ({ page }) => {
    // Adresse réelle dont la position a été retenue : l'inconnu reste distinct d'un zéro, et la
    // carte ne se recentre pas sur un point arbitraire.
    await page.goto(`/?address=${encodeURIComponent(UNPOSITIONED_ADDRESS_ID)}&lon=-1.542000&lat=48.135000&z=16.00`)
    await expect(page.getByText('ADRESSE', { exact: true })).toBeVisible({ timeout: 20_000 })
    await expect(page.getByText(/Non localisée/)).toBeVisible()
    await page.waitForLoadState('networkidle')
    await page.screenshot({ path: `${CAPTURES}/07-valeur-absente-motif.png` })
  })
})
