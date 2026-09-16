import { expect, test } from '@playwright/test'

test('recherche réelle, sélection, fiche et URL persistante', async ({ page }) => {
  const regionalGeoJsonRequests: string[] = []
  page.on('request', (request) => {
    if (/\.(?:geojson|json)(?:\?|$)/.test(request.url()) && request.url().includes('cadastre')) {
      regionalGeoJsonRequests.push(request.url())
    }
  })

  await page.goto('/')
  const search = page.getByRole('textbox', { name: 'Rechercher' })
  await search.fill('35238000BE0253')
  await expect(page.getByRole('option', { name: /35238000BE0253/ })).toBeVisible()
  await search.press('ArrowDown')
  await search.press('Enter')

  await expect(page.getByText('PARCELLE', { exact: true })).toBeVisible({ timeout: 15_000 })
  await expect(page).toHaveURL(/type=parcel/)
  await expect(page).toHaveURL(/id=parcel%3Acadastre%3A/)
  await expect(page.getByText(/Cadastre Etalab · DGFiP/)).toBeVisible()

  const selectedUrl = page.url()
  await page.reload()
  await expect(page).toHaveURL(selectedUrl)
  await expect(page.getByText('PARCELLE', { exact: true })).toBeVisible({ timeout: 15_000 })
  expect(regionalGeoJsonRequests).toEqual([])
})

/**
 * L'Explorer réduit à l'outil de vérification — C4, ADR-018.
 *
 * Les écrans de la plateforme gelée (candidats, recherches sauvegardées, pilote régional) sont
 * sortis du front ; leurs tests sont partis avec eux, et le code se retrouve au commit de C4.
 * invariant-ok: assertion-supprimee — les assertions retirées portaient sur ces écrans retirés.
 */
test('aucun contrôle mort : chaque bouton visible a un nom et un effet, rien n’appelle la plateforme gelée', async ({ page }) => {
  const frozenCalls: string[] = []
  page.on('request', (request) => {
    if (/\/api\/v1\/(opportunities|admin|saved-searches)/.test(request.url())) frozenCalls.push(request.url())
  })
  await page.goto('/')
  await expect(page.getByRole('heading', { name: 'Vérification des données' })).toBeVisible()

  const unnamed = await page.locator('button:not([aria-label])').evaluateAll((buttons) => buttons.filter((button) => !(button.textContent ?? '').trim() && !button.getAttribute('title')).length)
  expect(unnamed).toBe(0)

  // La liste exhaustive des boutons de l'écran d'accueil : un bouton ajouté sans effet vérifié
  // fait échouer ce test.
  const labels = await page.getByRole('button').evaluateAll((buttons) => buttons
    .filter((button) => (button as HTMLElement).offsetParent !== null)
    .map((button) => button.getAttribute('aria-label') ?? (button.textContent ?? '').trim()))
  expect(labels.sort()).toEqual(['Carte', 'Orthophoto IGN', 'Plan', 'Revue', 'Zoom in', 'Zoom out'].sort())

  await page.getByRole('button', { name: 'Orthophoto IGN' }).click()
  await expect(page).toHaveURL(/base=ortho/)
  await expect(page.getByText(/Orthophoto © IGN/)).toBeVisible()
  await page.getByRole('button', { name: 'Plan', exact: true }).click()
  await expect(page).not.toHaveURL(/base=ortho/)

  const zoomBefore = Number(new URL(page.url()).searchParams.get('z'))
  await page.getByRole('button', { name: 'Zoom in' }).click()
  await expect.poll(() => Number(new URL(page.url()).searchParams.get('z'))).toBeGreaterThan(zoomBefore)

  await page.getByRole('button', { name: 'Revue' }).click()
  await expect(page.getByRole('dialog')).toBeVisible()

  for (const gone of ['Aide', 'Paramètres', 'Pilote', 'Sauvegarder', 'Stratégie', 'Score minimum', 'Département']) {
    await expect(page.getByLabel(gone, { exact: true })).toHaveCount(0)
  }
  expect(frozenCalls).toEqual([])
})

test('une URL nue ouvre Rennes, et une carte trop dézoomée le dit', async ({ page }) => {
  await page.goto('/')
  await expect.poll(() => new URL(page.url()).searchParams.get('lat')).toMatch(/^48\.1/)
  expect(new URL(page.url()).searchParams.get('lon')).toMatch(/^-1\.6/)
  await expect(page.getByText(/Les parcelles s’affichent à partir du zoom/)).toHaveCount(0)

  await page.goto('/?lon=-1.68&lat=48.11&z=10')
  await expect(page.getByText(/Les parcelles s’affichent à partir du zoom 13/)).toBeVisible()
  await page.getByRole('button', { name: 'Zoomer ici' }).click()
  await expect(page.getByText(/Les parcelles s’affichent à partir du zoom/)).toHaveCount(0, { timeout: 10_000 })
  expect(Number(new URL(page.url()).searchParams.get('z'))).toBeGreaterThanOrEqual(13)
})

test('un service en panne n’est jamais présenté comme une absence de mutation ou de diagnostic', async ({ page }) => {
  await page.route('**/api/v1/parcels/*/transactions', (route) => route.fulfill({ status: 500, json: { detail: 'panne' } }))
  await page.route('**/api/v1/parcels/*/energy-assessments', (route) => route.fulfill({ status: 500, json: { detail: 'panne' } }))
  await page.goto('/?lon=-1.6&lat=48.1&z=18&type=parcel&id=parcel:cadastre:35024000AP0207')
  await page.getByRole('button', { name: /mutations DVF/ }).click()
  await expect(page.getByText(/Mutations indisponibles/)).toBeVisible()
  await expect(page.getByText('Aucune mutation rattachée à cette parcelle.')).toHaveCount(0)
  await page.getByRole('button', { name: /diagnostics DPE/ }).click()
  await expect(page.getByText(/Diagnostics indisponibles/)).toBeVisible()
  await expect(page.getByText(/Aucun diagnostic rattaché/)).toHaveCount(0)
})

test('la revue est une fenêtre modale qui se ferme par Échap', async ({ page }) => {
  await page.goto('/')
  await page.getByRole('button', { name: 'Revue' }).click()
  const dialog = page.getByRole('dialog')
  await expect(dialog).toBeVisible()
  await expect(dialog.getByRole('heading', { name: /Échantillon b4-/ })).toBeVisible({ timeout: 20_000 })
  await page.keyboard.press('Escape')
  await expect(dialog).toHaveCount(0)
  await expect(page.getByRole('button', { name: 'Carte' })).toHaveAttribute('aria-current', 'page')
})

test('recherche d’adresse réelle : recentrage, entités liées, appariements et URL partageable', async ({ page }) => {
  // FR-001 sur données réelles : aucune fixture, l'API répond depuis la release BAN activée.
  await page.goto('/')
  const search = page.getByRole('textbox', { name: 'Rechercher' })
  await search.fill('rue de la monnaie')

  // Plusieurs adresses plausibles : une liste, jamais une sélection implicite du premier.
  const options = page.getByRole('option')
  await expect(options.first()).toBeVisible({ timeout: 15_000 })
  expect(await options.count()).toBeGreaterThan(1)

  await search.press('ArrowDown')
  await search.press('Enter')

  await expect(page.getByText('ADRESSE', { exact: true })).toBeVisible({ timeout: 15_000 })
  await expect(page.getByRole('heading', { name: /Rue de la Monnaie/i })).toBeVisible()

  // L'appariement est visible avec sa méthode et sa décision, pas seulement son résultat.
  await expect(page.getByRole('heading', { name: 'Appariements certains' })).toBeVisible()
  await expect(page.getByText('source_relation').first()).toBeVisible()

  // URL partageable : rouvrir restitue le même état.
  await expect(page).toHaveURL(/address=address%3Aban%3A/)
  const shared = page.url()
  await page.reload()
  await expect(page).toHaveURL(shared)
  await expect(page.getByText('ADRESSE', { exact: true })).toBeVisible({ timeout: 15_000 })
})

test('adresse sans position : présente dans les résultats, non localisée, motif visible', async ({ page }) => {
  // Les 216 adresses sans position de BUG-03 doivent rester consultables sans que la carte se
  // recentre sur un point arbitraire.
  await page.route('**/api/v1/search?query=*', async (route) => {
    await route.fulfill({
      json: [{
        entity_type: 'address', id: 'address:ban:35238_0000_09999',
        label: '9999 Rue Sans Position 35000 Rennes', secondary_label: 'Adresse · 35238',
        center: null, bbox: null,
      }],
    })
  })
  await page.route('**/api/v1/spatial/addresses/*', async (route) => {
    await route.fulfill({
      json: {
        address: {
          id: 'address:ban:35238_0000_09999',
          display_label: '9999 Rue Sans Position 35000 Rennes',
          commune_code: '35238', department_code: '35',
          longitude: null, latitude: null, position_status: 'ambiguous_position',
        },
        matches: [],
      },
    })
  })

  await page.goto('/')
  const search = page.getByRole('textbox', { name: 'Rechercher' })
  await search.fill('rue sans position')
  await expect(page.getByRole('option', { name: /Rue Sans Position/ })).toBeVisible()
  await search.press('ArrowDown')
  await search.press('Enter')

  await expect(page.getByText('ADRESSE', { exact: true })).toBeVisible({ timeout: 15_000 })
  await expect(page.getByText(/Non localisée · ambiguous_position/)).toBeVisible()
  await expect(page.getByText(/la carte n’a pas été recentrée/)).toBeVisible()
  // Une absence d'appariement est motivée, et distinguée d'un rejet.
  await expect(page.getByText(/C’est une absence, pas un rejet/)).toBeVisible()
})

const coverageSources = (covered: string[]) =>
  ['DS-01', 'DS-02', 'DS-03', 'DS-04', 'DS-05'].map((id) => ({
    data_source_id: id, name: `Source ${id}`,
    release_id: covered.includes(id) ? `${id}@2026-01-01` : null,
    acceptance_status: covered.includes(id) ? 'accepted' : null,
    covered: covered.includes(id), record_count: covered.includes(id) ? 1200 : 0,
  }))

async function openCommune(page: import('@playwright/test').Page, coverage: Record<string, unknown>) {
  // La couverture suit la commune de l'entité consultée : on ouvre donc une adresse.
  await page.route('**/api/v1/search?query=*', async (route) => {
    await route.fulfill({ json: [{
      entity_type: 'address', id: 'address:ban:35238_0001_00001',
      label: '1 Rue Témoin 35000 Rennes', secondary_label: 'Adresse · 35238',
      center: [-1.68, 48.11], bbox: [-1.69, 48.10, -1.67, 48.12],
    }] })
  })
  await page.route('**/api/v1/spatial/addresses/*', async (route) => {
    await route.fulfill({ json: {
      address: {
        id: 'address:ban:35238_0001_00001', display_label: '1 Rue Témoin 35000 Rennes',
        commune_code: '35238', department_code: '35',
        longitude: -1.68, latitude: 48.11, position_status: 'available',
      },
      matches: [],
    } })
  })
  await page.route('**/api/v1/spatial/coverage?*', async (route) => {
    await route.fulfill({ json: coverage })
  })
  await page.goto('/')
  const search = page.getByRole('textbox', { name: 'Rechercher' })
  await search.fill('rue temoin')
  // Attendre que la liste soit peuplée : ArrowDown n'ouvre le menu que si des résultats sont
  // déjà là, sinon la navigation clavier ne sélectionne rien.
  await expect(page.getByRole('option', { name: /Rue Témoin/ })).toBeVisible()
  await search.press('ArrowDown')
  await search.press('Enter')
}

test('territoire non couvert : jamais présenté comme un résultat vide', async ({ page }) => {
  await openCommune(page, {
    commune_code: '22001', commune_name: 'COMMUNE SANS DONNÉE', department_code: '22',
    state: 'not_covered', sources: coverageSources([]),
    missing_sources: ['DS-01 Cadastre', 'DS-02 RNB', 'DS-03 BDNB', 'DS-04 BD TOPO', 'DS-05 BAN'],
  })

  await expect(page.getByText(/territoire non couvert/)).toBeVisible({ timeout: 15_000 })
  await expect(page.getByText(/ne veut rien dire ici/)).toBeVisible()
  // L'état « couvert » ne doit jamais accompagner un territoire non couvert.
  await expect(page.getByText(/territoire couvert/)).toHaveCount(0)
})

test('données partielles : les sources absentes sont nommées, pas comptées', async ({ page }) => {
  await openCommune(page, {
    commune_code: '35238', commune_name: 'RENNES', department_code: '35',
    state: 'partial', sources: coverageSources(['DS-01', 'DS-03', 'DS-04', 'DS-05']),
    missing_sources: ['DS-02 Référentiel National des Bâtiments'],
  })

  await expect(page.getByText(/données partielles/)).toBeVisible({ timeout: 15_000 })
  await expect(page.getByText(/DS-02 Référentiel National des Bâtiments/)).toBeVisible()
  await expect(page.getByText(/Rattachements incomplets/)).toBeVisible()
})

test('territoire couvert : une fiche sans rattachement signifie bien que la base n’en connaît aucun', async ({ page }) => {
  await openCommune(page, {
    commune_code: '35238', commune_name: 'RENNES', department_code: '35',
    state: 'covered', sources: coverageSources(['DS-01', 'DS-02', 'DS-03', 'DS-04', 'DS-05']),
    missing_sources: [],
  })

  await expect(page.getByText(/territoire couvert/)).toBeVisible({ timeout: 15_000 })
  await expect(page.getByText(/la base n’en connaît aucun/)).toBeVisible()
  await expect(page.getByText(/C’est une absence, pas un rejet/)).toBeVisible()
})

test('l’état de couverture survit au partage d’URL', async ({ page }) => {
  await openCommune(page, {
    commune_code: '35238', commune_name: 'RENNES', department_code: '35',
    state: 'partial', sources: coverageSources(['DS-01', 'DS-03', 'DS-04', 'DS-05']),
    missing_sources: ['DS-02 Référentiel National des Bâtiments'],
  })
  await expect(page.getByText(/données partielles/)).toBeVisible({ timeout: 15_000 })

  const shared = page.url()
  await page.reload()
  await expect(page).toHaveURL(shared)
  await expect(page.getByText(/données partielles/)).toBeVisible({ timeout: 15_000 })
  await expect(page.getByText(/DS-02 Référentiel National des Bâtiments/)).toBeVisible()
})


/**
 * Changer de parcelle doit recharger ses mutations — D6a.
 *
 * La fiche est rendue à la même place d'une parcelle à l'autre : React réutilise l'instance et
 * son état survit au changement. Le bloc de mutations gardait donc celles de la parcelle
 * précédente, et un garde « ne pas recharger si on a déjà les données » empêchait toute nouvelle
 * requête.
 *
 * Signalé sur 35024000AP0206, qui affichait les deux ventes de sa voisine AP0207 alors qu'elle
 * n'en porte qu'une. Un écran de vérification qui attribue une vente à la mauvaise parcelle est
 * pire qu'un écran absent : il fait douter d'une donnée juste, ou pire, il fait croire à une
 * donnée fausse.
 */
test('changer de parcelle recharge ses mutations, sans garder celles de la précédente', async ({ page }) => {
  await page.goto('/?lon=-1.6&lat=48.1&z=18&department=35&type=parcel&id=parcel:cadastre:35024000AP0207')
  await page.waitForTimeout(4000)
  await page.getByRole('button', { name: /mutations DVF/ }).click()
  await page.waitForTimeout(2000)
  expect(await page.locator('.transaction-row').count()).toBe(2)

  await page.goto('/?lon=-1.6&lat=48.1&z=18&department=35&type=parcel&id=parcel:cadastre:35024000AP0206')
  await page.waitForTimeout(4000)
  await page.getByRole('button', { name: /mutations DVF/ }).click()
  await page.waitForTimeout(2000)
  expect(await page.locator('.transaction-row').count()).toBe(1)
})


/**
 * Changer de parcelle doit recharger ses diagnostics — D6b.
 *
 * Même défaut que pour les mutations de D6a, même cause : la fiche est rendue à la même place
 * d'une parcelle à l'autre, React réutilise l'instance, et son état survit au changement. Un
 * écran de vérification qui attribue un diagnostic à la mauvaise parcelle est pire qu'un écran
 * absent.
 *
 * Le second cas porte quatre diagnostics dont le rattachement est ambigu — un bâtiment
 * chevauchant plusieurs parcelles. Ils doivent rester visibles et signalés comme tels : les
 * masquer cacherait la population que cet écran existe pour montrer.
 */
test('changer de parcelle recharge ses diagnostics, et signale un rattachement ambigu', async ({ page }) => {
  await page.goto('/?lon=-1.685&lat=48.1168&z=18&department=35&type=parcel&id=parcel:cadastre:35238000AB0005')
  await page.waitForTimeout(4000)
  await page.getByRole('button', { name: /diagnostics DPE/ }).click()
  await page.waitForTimeout(2000)
  expect(await page.locator('.assessment-row').count()).toBe(1)
  await expect(page.getByText('Rattachement certain')).toBeVisible()

  await page.goto('/?lon=-1.685&lat=48.1168&z=18&department=35&type=parcel&id=parcel:cadastre:35238000AB0303')
  await page.waitForTimeout(4000)
  await page.getByRole('button', { name: /diagnostics DPE/ }).click()
  await page.waitForTimeout(2000)
  expect(await page.locator('.assessment-row').count()).toBe(4)
  expect(await page.getByText('Rattachement ambigu').count()).toBe(4)
})
