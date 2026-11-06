// The browser evidence run (Playwright, through the Playwright MCP's browser_run_code with this file).
// Writes .work/frames/*.png, and .work/browser-raw.json and .work/moment-0.x3d as browser downloads (the
// sandbox has no fs); then: python3 -E -s tools/record_browser.py
async (page) => {
  const ROOT = process.env.MANIFOLD_ROOT || '<path to studies/manifold>', BASE = 'http://127.0.0.1:8836/';
  const raw = { errors: [], failed: [] };
  page.on('console', m => { if (m.type() === 'error' || m.type() === 'warning') raw.errors.push(m.type() + ': ' + m.text().slice(0, 300)); });
  page.on('pageerror', e => raw.errors.push('pageerror: ' + e.message.slice(0, 300)));
  page.on('response', r => { if (r.status() >= 400) raw.failed.push(r.status() + ' ' + r.url()); });
  await page.setViewportSize({ width: 1280, height: 800 });
  const frames = async (n) => page.waitForFunction((n) => window.manifoldView && window.manifoldView().frame > n, n, { timeout: 120000 });
  const open = async (hash) => { await page.goto('about:blank'); await page.goto(BASE + hash); await frames(40); await page.waitForTimeout(500); };
  const view = () => page.evaluate(() => { const v = window.manifoldView(); delete v.heightAt; return v; });

  // 1. health, and the page's field against the builder's rest heights
  await open('#mood=0&settle=1&t=3.7&paused=1&orbit=0');
  raw.ua = await page.evaluate(() => navigator.userAgent);
  const v0 = await view();
  raw.health = { shaders: v0.x3d.shaders, blend: v0.x3d.blend, multisampling: v0.x3d.multisampling, lens: v0.lens, flows: v0.flows, url: v0.x3d.url };
  raw.parity = await page.evaluate(() => { const v = window.manifoldView(), n = 513, E = 11.2, out = []; for (let j = 0; j < n; j += 16) for (let i = 0; i < n; i += 16) out.push([i, j, v.heightAt((i / (n - 1) * 2 - 1) * E, (j / (n - 1) * 2 - 1) * E)]); return out; });

  // 2. playback: the field moves while running and holds when paused
  await open('#mood=0&settle=1&t=3.7&orbit=0');
  const a = await view(); await page.waitForTimeout(1500); const b = await view();
  await page.keyboard.press('Space'); await page.waitForTimeout(300); const c = await view(); await page.waitForTimeout(1200); const d = await view();
  raw.playback = { running: [a.time, b.time], paused: [c.time, d.time], frames: [a.frame, d.frame], state: d.running };

  // 3. resilience: the frame's own path throws once (the label layer); frames and the X3D clock must go on
  await page.keyboard.press('Space');
  raw.resilience = await page.evaluate(async () => {
    const orig = window.AffectLabels; let thrown = 0, uncaught = 0;
    const onerr = () => uncaught++; window.addEventListener('error', onerr);
    window.AffectLabels = { ...orig, update(o) { if (!thrown) { thrown++; throw Error('resilience probe: the label layer threw once'); } return orig.update(o); } };
    const clock = document.getElementById('scene').browser.currentScene.getNamedNode('Clock');
    const f0 = window.manifoldView().frame, t0 = window.manifoldView().time, e0 = clock.elapsedTime;
    await new Promise(r => setTimeout(r, 1500));
    const f1 = window.manifoldView().frame, t1 = window.manifoldView().time, e1 = clock.elapsedTime;
    window.AffectLabels = orig; window.removeEventListener('error', onerr);
    return { thrown, uncaught, frames_after: f1 - f0, time_after: t1 - t0, clock_after: e1 - e0 };
  });

  // 4. a click sends a ripple through the field
  await page.mouse.click(660, 420); await page.waitForTimeout(600);
  raw.ripple = { impulses: (await view()).impulses };

  // 5. the original page and this one at the same moments, four moods (film grain off on both)
  await page.goto('about:blank');
  await page.goto(BASE + 'reference/Manifold-of-Emotion.html');
  await page.waitForTimeout(1500);
  await page.evaluate(() => { const q = document.getElementById('quality'); q.value = 'ultra'; q.dispatchEvent(new Event('change', { bubbles: true })); const g = document.getElementById('grain'); g.checked = false; g.dispatchEvent(new Event('change', { bubbles: true })); });
  raw.original = [];
  for (let mood = 0; mood < 4; mood++) {
    if (mood > 0) await page.click(`[data-mood="${mood}"]`);
    await page.waitForTimeout(11000);
    await page.click('#play'); await page.waitForTimeout(900);
    const s = await page.evaluate(() => { const r = window.manifoldDiagnostics(); return { time: r.time, camera: r.camera, mood: r.mood, state: r.state, quality: r.quality, width: r.width, height: r.height }; });
    await page.screenshot({ path: `${ROOT}/.work/frames/original-${mood}.png` });
    raw.original.push(s);
    if (mood === 0) {   // control: the same view 3 time units later must match worse
      await page.click('#play'); await page.waitForTimeout(3000 / 0.65); await page.click('#play'); await page.waitForTimeout(900);
      raw.original_later = await page.evaluate(() => window.manifoldDiagnostics().time);
      await page.screenshot({ path: `${ROOT}/.work/frames/original-0-later.png` });
    }
    await page.click('#play');
  }
  raw.x3d = [];
  for (let mood = 0; mood < 4; mood++) {
    const s = raw.original[mood], c = s.camera;
    await open(`#mood=${mood}&settle=1&t=${s.time}&az=${c.az}&el=${c.el}&dist=${c.dist}&target=${c.target.join(',')}&paused=1&orbit=0&grain=0&quality=1`);
    await page.screenshot({ path: `${ROOT}/.work/frames/x3d-${mood}.png` });
    const v = await view(); raw.x3d.push({ time: v.time, mood: v.mood, camera: v.camera, flows: v.flows, contentScale: v.quality.contentScale });
  }

  // 6. the saved moment is a portable X3D scene: load it alone and draw it (no page logic, no lens)
  {
    const s = raw.original[0], c = s.camera;
    await open(`#mood=0&settle=1&t=${s.time}&az=${c.az}&el=${c.el}&dist=${c.dist}&target=${c.target.join(',')}&paused=1&orbit=0&grain=0&quality=1&lens=0`);
    await page.screenshot({ path: `${ROOT}/.work/frames/live-nolens-0.png` });
    const [dl] = await Promise.all([page.waitForEvent('download'), page.click('#saveX3D')]);   // the real Save X3D path
    await dl.saveAs(`${ROOT}/.work/moment-0.x3d`);
    raw.moment_download = dl.suggestedFilename();
    const text = await page.evaluate(() => window.manifoldMomentX3D());
    raw.moment = await page.evaluate(async (text) => {
      const B = X3D.getBrowser(document.getElementById('scene'));
      const sc = await B.createX3DFromString(text); B.replaceWorld(sc);
      await new Promise(r => setTimeout(r, 4000));
      const cur = B.currentScene, names = ['SkyShader', 'SurfaceShader', 'VeilShader', 'FlowShader', 'FiberShader', 'NodeShader', 'MoteShader'];
      return { bytes: text.length, shaders: names.map(n => [n, cur.getNamedNode(n).isValid]) };
    }, text);
    await page.evaluate(() => { document.getElementById('lens').hidden = true; });
    await page.waitForTimeout(500);
    await page.screenshot({ path: `${ROOT}/.work/frames/moment-0.png` });
  }
  const json = JSON.stringify(raw, null, 1);
  const [dj] = await Promise.all([page.waitForEvent('download'), page.evaluate((json) => { const a = document.createElement('a'); a.href = URL.createObjectURL(new Blob([json], { type: 'application/json' })); a.download = 'browser-raw.json'; document.body.append(a); a.click(); }, json)]);
  await dj.saveAs(ROOT + '/.work/browser-raw.json');
  return { errors: raw.errors.length, failed: raw.failed.length, resilience: raw.resilience, moment: raw.moment };
}
