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

test('recherche → fiche → scénario → statut → note sans fixture de production', async ({ page }) => {
  const opportunity = {
    id: 'opportunity:test:connected', property_unit_id: 'property-unit:test:connected',
    strategy: 'division_extension', score: 78.4, score_class: 'high_priority',
    confidence_score: 82, confidence_level: 'high', segment_code: 'rennes-urban',
    snapshot_at: '2026-08-01', calculated_at: '2026-08-02T10:00:00+00:00',
    baseline_selected: true,
  }
  let candidateStatus = 'new'
  const notes: Array<{ id: string; body: string; author: string; created_at: string }> = []
  const scenarios: Array<Record<string, unknown>> = []

  await page.route('**/api/v1/opportunities?**', (route) => route.fulfill({
    json: [opportunity], headers: { 'Access-Control-Expose-Headers': 'X-Next-Cursor' },
  }))
  await page.route('**/api/v1/opportunities/opportunity%3Atest%3Aconnected', (route) => route.fulfill({
    json: {
      ...opportunity, definition_id: 'division-extension-v1', definition_version: 1,
      eligible: true, eligibility_results: [], missing_features: ['RISK-004'],
      publication_blockers: [], release_ids: ['DS-01:test'], financial_scenario: null,
      components: [{ code: 'land_capacity', score: 80 }],
    },
  }))
  await page.route('**/api/v1/opportunities/opportunity%3Atest%3Aconnected/evidence', (route) => route.fulfill({
    json: [{ feature_code: 'LAND-004', impact: 8.5, explanation: 'Surface utile favorable.', quality: 'accepted', observed_at: '2026-08-01' }],
  }))
  await page.route('**/api/v1/opportunities/opportunity%3Atest%3Aconnected/comparables', (route) => route.fulfill({
    json: [{ transaction_id: 'dvf:1', included: true, reason: 'Même segment', normalized_price_m2: 3150 }],
  }))
  await page.route('**/api/v1/opportunities/opportunity%3Atest%3Aconnected/sources', (route) => route.fulfill({
    json: [{ data_source_id: 'DS-01', name: 'Cadastre', producer: 'DGFiP', release_id: 'DS-01:test' }],
  }))
  await page.route('**/api/v1/opportunities/opportunity%3Atest%3Aconnected/workspace', (route) => route.fulfill({
    json: { state: { status: candidateStatus, favorite: false, rejection_reasons: [], rejection_comment: null, updated_at: null }, history: [], notes, scenarios },
  }))
  await page.route('**/api/v1/opportunities/opportunity%3Atest%3Aconnected/status', async (route) => {
    const payload = route.request().postDataJSON() as { status: string }
    candidateStatus = payload.status
    await route.fulfill({ json: { status: candidateStatus, favorite: false, rejection_reasons: [], rejection_comment: null, updated_at: '2026-08-07T12:00:00+00:00' } })
  })
  await page.route('**/api/v1/opportunities/opportunity%3Atest%3Aconnected/scenarios', async (route) => {
    const assumptions = route.request().postDataJSON() as Record<string, number>
    const result = { id: 'scenario:user:test', assumptions, results: { total_cost_eur: 270000, net_margin_eur: 70000, return_on_cost: 0.259 }, created_at: '2026-08-07T12:00:00+00:00' }
    scenarios.unshift(result)
    await route.fulfill({ status: 201, json: result })
  })
  await page.route('**/api/v1/opportunities/opportunity%3Atest%3Aconnected/notes', async (route) => {
    const payload = route.request().postDataJSON() as { body: string }
    const result = { id: 'note:test', body: payload.body, author: 'Ada', created_at: '2026-08-07T12:00:00+00:00' }
    notes.unshift(result)
    await route.fulfill({ status: 201, json: result })
  })

  const startedAt = Date.now()
  await page.goto('/')
  const card = page.getByRole('button', { name: /property-unit:test:connected/ })
  await expect(card).toBeVisible()
  await card.click()
  await expect(page).toHaveURL(/opportunity=opportunity%3Atest%3Aconnected/)
  await expect(page.getByText('Surface utile favorable.')).toBeVisible()
  await expect(page.getByText(/Inconnues : RISK-004/)).toBeVisible()
  expect(Date.now() - startedAt).toBeLessThan(1_000)

  await page.getByLabel('Acquisition').fill('200000')
  await page.getByLabel('Travaux').fill('50000')
  await page.getByLabel('Revente').fill('340000')
  await page.getByLabel('Frais').fill('20000')
  await page.getByRole('button', { name: 'Recalculer et sauvegarder' }).click()
  await expect(page.getByText('70 000 €', { exact: true })).toBeVisible()

  await page.getByLabel('Statut du candidat').selectOption('retained')
  await expect(page.getByLabel('Statut du candidat')).toHaveValue('retained')
  await page.getByLabel('Nouvelle note').fill('Accès à confirmer sur place.')
  await page.getByRole('button', { name: 'Ajouter la note' }).click()
  await expect(page.getByText('Accès à confirmer sur place.')).toBeVisible()

  await page.setViewportSize({ width: 390, height: 844 })
  await expect(page.getByLabel('Statut du candidat')).toBeVisible()
  await expect(page.getByLabel('Nouvelle note')).toBeVisible()
})

test('inconnu reste distinct de zéro et les contrôles ont un nom accessible', async ({ page }) => {
  await page.route('**/api/v1/opportunities?**', (route) => route.fulfill({ json: [{
    id: 'opportunity:test:unknown', property_unit_id: 'property-unit:test:unknown',
    strategy: 'renovation_resale', score: null, score_class: null, confidence_score: 25,
    confidence_level: 'low', segment_code: 'unknown', snapshot_at: '2025-01-01',
    calculated_at: '2025-01-02T10:00:00+00:00', baseline_selected: false,
  }] }))
  await page.goto('/')
  await expect(page.getByText('Inconnu')).toBeVisible()
  const unnamed = await page.locator('button:not([aria-label])').evaluateAll((buttons) => buttons.filter((button) => !(button.textContent ?? '').trim() && !button.getAttribute('title')).length)
  expect(unnamed).toBe(0)
})

test('sélecteur Bretagne et gate régional refusent une fausse couverture', async ({ page }) => {
  await page.route('**/api/v1/opportunities?**', (route) => route.fulfill({ json: [] }))
  await page.route('**/api/v1/session', (route) => route.fulfill({ json: {
    user_id: 'user:test', display_name: 'Admin', email: null,
    organization_id: 'org:test', organization_name: 'Test', role: 'platform_admin',
  } }))
  await page.route('**/api/v1/admin/import-runs', (route) => route.fulfill({ json: [] }))
  await page.route('**/api/v1/admin/data-quality', (route) => route.fulfill({ json: [] }))
  await page.route('**/api/v1/admin/brittany/readiness', (route) => route.fulfill({ json: {
    publishable: false,
    blockers: ['regional_data_not_covered', 'score_definitions_not_active'],
    territories: Object.fromEntries(['22', '29', '35', '56'].map((code) => [code, {
      covered: false,
      sources: Array.from({ length: 9 }, (_, index) => ({
        data_source_id: `DS-${String(index + 1).padStart(2, '0')}`,
        release_id: null, acceptance_status: 'missing', blocking_quality_count: 0, ready: false,
      })),
    }])),
    active_score_count: 0,
    segmentation: { id: 'brittany-market-segments', version: 1, status: 'draft' },
    active_bundle: null,
  } }))

  await page.goto('/')
  await page.getByLabel('Département').selectOption('29')
  await expect(page).toHaveURL(/department=29/)
  await expect(page.getByText('Bretagne · département 29')).toBeVisible()
  await page.getByRole('button', { name: /Pilote/ }).click()
  await expect(page.getByRole('heading', { name: 'Pilote Bretagne' })).toBeVisible()
  await expect(page.getByText('Publication bloquée')).toBeVisible()
  await expect(page.getByText('Département 56')).toBeVisible()
  await expect(page.getByRole('button', { name: 'Publier la Bretagne' })).toBeDisabled()
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
  await search.press('ArrowDown')
  await search.press('Enter')

  await expect(page.getByText('ADRESSE', { exact: true })).toBeVisible({ timeout: 15_000 })
  await expect(page.getByText(/Non localisée · ambiguous_position/)).toBeVisible()
  await expect(page.getByText(/la carte n’a pas été recentrée/)).toBeVisible()
  // Une absence d'appariement est motivée, et distinguée d'un rejet.
  await expect(page.getByText(/C’est une absence, pas un rejet/)).toBeVisible()
})
