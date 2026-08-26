const input = document.querySelector('#person-search');
const rows = [...document.querySelectorAll('[data-person-search]')];
const count = document.querySelector('#person-search-count');
const empty = document.querySelector('#person-search-empty');

if (input && count && empty) {
  input.addEventListener('input', () => {
    const term = input.value.trim().toLocaleLowerCase('zh-Hant');
    let visible = 0;
    for (const row of rows) {
      const matches = !term || row.dataset.personSearch.includes(term);
      row.hidden = !matches;
      if (matches) visible += 1;
    }
    count.textContent = term ? `找到 ${visible} 人` : `共 ${rows.length} 人`;
    empty.hidden = visible !== 0;
  });
}
