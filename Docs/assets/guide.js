/* GaesinLight 참고서 상호작용: 검색(접힌 내용까지), 모두 펼치기/접기, 주소 #링크 자동 펼침, 인쇄 시 전체 펼침. */
(() => {
  'use strict';
  const chapters = [...document.querySelectorAll('main details.chapter')];
  const input = document.getElementById('guide-search');
  const result = document.getElementById('search-result');
  const allDetails = () => [...document.querySelectorAll('main details')];
  const normal = s => s.normalize('NFKC').toLocaleLowerCase().replace(/\s+/g, ' ').trim();
  let snapshot = null;

  function filter() {
    const query = normal(input ? input.value : '');
    if (query && !snapshot) snapshot = allDetails().map(el => [el, el.open]);
    let matches = 0;
    chapters.forEach(chapter => {
      const nodes = [...chapter.querySelectorAll(':scope > .chapter-body > details.node')];
      const summaryHit = query && normal(chapter.querySelector(':scope > summary').textContent).includes(query);
      let visible = 0;
      nodes.forEach(node => {
        const hit = !query || summaryHit || normal(node.textContent).includes(query);
        node.hidden = !hit;
        if (hit) { visible++; if (query) node.open = true; }
      });
      const bodyHit = query && normal(chapter.textContent).includes(query);
      const hit = !query || summaryHit || visible > 0 || (bodyHit && !nodes.length);
      chapter.hidden = !hit;
      if (hit) { matches++; if (query) chapter.open = true; }
    });
    if (!query && snapshot) { snapshot.forEach(([el, open]) => { el.open = open; }); snapshot = null; }
    if (result) {
      result.textContent = query
        ? (matches ? `${matches}개 장에서 찾았습니다.` : '검색 결과가 없습니다. 검색어를 줄이거나 지워 보세요.')
        : '필요한 장만 펼쳐 보세요. 검색은 접힌 설명까지 찾습니다.';
    }
  }

  function revealHash() {
    let target;
    try { target = document.getElementById(decodeURIComponent(location.hash.slice(1))); } catch (_) { return; }
    if (!target) return;
    if (input && input.value) { input.value = ''; filter(); }
    for (let el = target; el; el = el.parentElement) {
      if (el.tagName === 'DETAILS') el.open = true;
      el.hidden = false;
    }
    requestAnimationFrame(() => target.scrollIntoView({ block: 'start' }));
  }

  input?.addEventListener('input', filter);
  document.getElementById('clear-search')?.addEventListener('click', () => { input.value = ''; filter(); input.focus(); });
  document.getElementById('expand-all')?.addEventListener('click', () => allDetails().filter(el => !el.hidden).forEach(el => { el.open = true; }));
  document.getElementById('collapse-all')?.addEventListener('click', () => allDetails().forEach(el => { el.open = false; }));
  window.addEventListener('hashchange', revealHash);
  let printSnapshot;
  window.addEventListener('beforeprint', () => { printSnapshot = allDetails().map(el => [el, el.open, el.hidden]); allDetails().forEach(el => { el.open = true; el.hidden = false; }); });
  window.addEventListener('afterprint', () => printSnapshot?.forEach(([el, open, hidden]) => { el.open = open; el.hidden = hidden; }));
  filter();
  if (location.hash) revealHash();
})();
