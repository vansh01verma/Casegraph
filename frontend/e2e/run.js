const { chromium } = require('playwright')
const OUT = './e2e-screens/'
const results = []
const ok = (name, cond, extra = '') => { results.push([cond ? 'PASS' : 'FAIL', name, extra]); if (!cond) process.exitCode = 1 }
;(async () => {
  const b = await chromium.launch(); const p = await b.newPage({ viewport: { width: 1440, height: 900 } })
  const errors = []; p.on('pageerror', (e) => errors.push(e.message)); p.on('console', (m) => { if (m.type() === 'error') errors.push(m.text()) })
  await p.goto('http://127.0.0.1:5173/'); await p.waitForSelector('[data-testid=option-demo]')
  ok('landing shows both options', await p.locator('[data-testid=option-live]').count() === 1)
  await p.click('[data-testid=option-demo]'); await p.waitForSelector('[data-tour=dashboard-metrics]')
  ok('DEMO MODE badge in header', (await p.textContent('[data-testid=demo-badge]')).includes('DEMO MODE'))
  const metrics = await p.textContent('[data-tour=dashboard-metrics]'); ok('dashboard metrics real', /239/.test(metrics) && /48/.test(metrics), metrics.slice(0, 80))
  await p.screenshot({ path: OUT + '1-dashboard.png' })
  // vault
  await p.click('text=Evidence Vault'); await p.waitForSelector('[data-testid=vault-row]')
  ok('vault lists records', await p.locator('[data-testid=vault-row]').count() === 25)
  await p.fill('[data-testid=vault-search]', 'naya number'); await p.waitForTimeout(700)
  ok('vault search filters', (await p.textContent('[data-testid=vault-total]')).startsWith('2') || parseInt(await p.textContent('[data-testid=vault-total]')) >= 2)
  await p.fill('[data-testid=vault-search]', ''); await p.selectOption('[data-testid=vault-category]', 'cctv'); await p.waitForTimeout(500)
  ok('vault category filter', (await p.textContent('[data-testid=vault-total]')).startsWith('15'))
  await p.locator('[data-testid=vault-row]').first().click(); await p.waitForSelector('[data-testid=evidence-drawer] img')
  ok('evidence drawer shows CCTV frame + hash', await p.locator('[data-testid=evidence-drawer] img').isVisible())
  await p.click('text=Recompute & verify hash'); await p.waitForSelector('text=Hash matches stored value'); ok('hash verify works', true)
  await p.screenshot({ path: OUT + '2-evidence.png' }); await p.click('text=Close')
  // identity
  await p.click('nav >> text=Identity'); await p.waitForSelector('[data-testid=identity-card]')
  ok('4 identity cards', await p.locator('[data-testid=identity-card]').count() === 4)
  await p.click('[data-testid=accept-IM-2]'); await p.waitForSelector('[data-testid=identity-card] >> text=accepted'); ok('accept updates status', true)
  await p.click('[data-testid=reject-IM-3]'); await p.waitForSelector('text=rejected'); await p.screenshot({ path: OUT + '3-identity.png' })
  // graph
  await p.click('nav >> text=Graph'); await p.waitForSelector('.react-flow__node')
  const n0 = await p.locator('.react-flow__node').count(); ok('graph renders nodes', n0 > 30, String(n0))
  await p.click('[data-testid=filter-location]'); await p.waitForTimeout(400); ok('graph type filter hides nodes', await p.locator('.react-flow__node').count() < n0)
  await p.click('[data-testid=filter-location]')
  await p.fill('[data-testid=graph-search]', 'Rajesh'); await p.waitForTimeout(300); ok('graph search highlights', (await p.textContent('[data-testid=graph-detail]')).length > 0 && (await p.locator('text=match(es) highlighted').count()) === 1)
  await p.fill('[data-testid=graph-search]', '')
  await p.locator('.react-flow__node', { hasText: 'Chitra Nair' }).first().click(); await p.waitForSelector('[data-testid=expand]')
  await p.click('[data-testid=expand]'); await p.waitForTimeout(500); const n1 = await p.locator('.react-flow__node').count(); ok('expand focuses neighbourhood', n1 > 1 && n1 < n0, String(n1))
  await p.screenshot({ path: OUT + '4-graph.png' })
  // timeline
  await p.click('nav >> text=Timeline'); await p.waitForSelector('[data-testid=slider]')
  const c0 = await p.textContent('[data-testid=tl-count]')
  await p.locator('[data-testid=slider]').fill('1290'); await p.waitForTimeout(300); const c1 = await p.textContent('[data-testid=tl-count]'); ok('slider reveals events', c0 !== c1, `${c0} -> ${c1}`)
  ok('corrected timestamp shown', await p.locator('text=/device 21:17:00/').count() >= 1)
  await p.click('[data-testid=tl-filter-cdr]'); await p.waitForTimeout(200); ok('type filter changes count', (await p.textContent('[data-testid=tl-count]')) !== c1)
  await p.click('[data-testid=tl-filter-cdr]'); await p.selectOption('[data-testid=tl-person]', 'P-C'); await p.waitForTimeout(500)
  ok('person filter', /of \d+ events/.test(await p.textContent('[data-testid=tl-count]')))
  await p.selectOption('[data-testid=tl-person]', ''); await p.locator('[data-testid=slider]').fill('1200'); await p.click('[data-testid=play]'); await p.waitForTimeout(2200)
  ok('play advances cursor', (await p.textContent('[data-testid=cursor]')) !== '20:00'); await p.click('[data-testid=play]')
  await p.screenshot({ path: OUT + '5-timeline.png' })
  // contradictions
  await p.click('nav >> text=Contradictions'); await p.waitForSelector('[data-testid=contradiction]')
  const ctext = await p.textContent('[data-tour=contradiction-list]'); ok('contradiction shows statement, caveats, evidence', ctext.includes('9:20 PM') && ctext.includes('Why this is not a conclusion') && /EV-0210/.test(ctext))
  await p.click('[data-testid=confirm-CON-1]'); await p.waitForSelector('text=Conflict confirmed by analyst'); ok('review status updates', true)
  await p.screenshot({ path: OUT + '6-contradictions.png', fullPage: true })
  // reconstruction
  await p.click('nav >> text=Reconstruction'); await p.click('[data-testid=run-reconstruction]'); await p.waitForSelector('[data-testid=scenario]', { timeout: 15000 })
  ok('3 scenarios + honest banner', (await p.locator('[data-testid=scenario]').count()) === 3 && (await p.textContent('[data-testid=mode-banner]')).includes('not newly generated'))
  await p.click('[data-testid=challenge-H-2]'); await p.waitForSelector('text=Produced by: precomputed'); ok('critic challenge works', true)
  await p.screenshot({ path: OUT + '7-reconstruction.png', fullPage: true })
  // gaps
  await p.click('nav >> text=Gaps'); await p.waitForSelector('[data-testid=gap]'); ok('gaps listed', (await p.locator('[data-testid=gap]').count()) === 11)
  // assistant
  await p.click('nav >> text=Assistant'); await p.fill('[data-testid=chat-input]', 'Who transferred money to Person B?'); await p.click('[data-testid=chat-send]'); await p.waitForSelector('[data-testid=bot-msg]')
  const bot = await p.textContent('[data-testid=bot-msg]'); ok('assistant answers from data', bot.includes('Chitra Nair') && bot.includes('rejected') === false && bot.includes('4,85,000') || bot.includes('No transactions'), bot.slice(0, 90))
  await p.fill('[data-testid=chat-input]', 'Did anyone buy a yacht?'); await p.click('[data-testid=chat-send]'); await p.waitForSelector('text=not available in the demo dataset'); ok('assistant admits no answer', true)
  await p.screenshot({ path: OUT + '8-assistant.png' })
  // report
  await p.click('nav >> text=PDF Report'); await p.click('[data-testid=generate-report]'); await p.waitForSelector('[data-testid=report-ready]', { timeout: 20000 })
  const [dl] = await Promise.all([p.waitForEvent('download'), p.click('[data-testid=download-report]')]); const path = await dl.path(); ok('PDF downloads', require('fs').readFileSync(path).slice(0, 4).toString() === '%PDF')
  // reset
  p.once('dialog', (d) => d.accept()); await p.click('[data-testid=reset]'); await p.waitForTimeout(1500)
  await p.click('nav >> text=Identity'); await p.waitForSelector('[data-testid=identity-card]'); ok('reset restores identity matches', (await p.locator('[data-testid=identity-card] >> text=proposed').count()) === 4)
  // tour
  await p.click('[data-testid=start-tour]'); await p.waitForSelector('[data-testid=tour]')
  for (let i = 0; i < 10; i++) { await p.click('[data-testid=tour-next]'); await p.waitForTimeout(450) }
  ok('tour reaches step 11 of 11', (await p.textContent('[data-testid=tour]')).includes('Step 11 of 11')); await p.screenshot({ path: OUT + '9-tour.png' })
  await p.click('[data-testid=tour-done]'); ok('tour can finish', (await p.locator('[data-testid=tour]').count()) === 0)
  await p.click('[data-testid=start-tour]'); await p.click('[data-testid=tour-skip]'); ok('tour can be skipped', (await p.locator('[data-testid=tour]').count()) === 0)
  ok('no console/page errors', errors.length === 0, errors.slice(0, 3).join(' | '))
  await b.close(); results.forEach((r) => console.log(r.join('  ')))
})().catch((e) => { console.error('E2E CRASH', e.message); results.forEach((r) => console.log(r.join('  '))); process.exit(1) })
