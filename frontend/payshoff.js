
function do_on_click(el, get_data, gameopt, onerr) {
  el.addEventListener('click', e => {
    const gameid = e.target.attributes['gameid'].value;
    if (!gameid)
      return;

    const data = get_data(e.target);
    if (data === null)
      return;

    fetch(`/p/${gameid}/${gameopt}`, {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify(data)
    })
    .then(e => {
      if (e.status === 200)
        window.location.reload();
      else
        return e.text();
    })
    .then(err => {
      if (err && err !== 'OK')
        onerr(err);
      else
        window.location.reload();
    });
  });
}

do_on_click(document.getElementById('add-new-item'), (t) => {
  let option = prompt('Add Option');
  if (option === null)
    return null;
  return {'option': option};
}, 'add', () => {});

do_on_click(document.getElementById('select-item'), (t) => {
  return {};
}, 'sel', () => {});

do_on_click(document.getElementById('adm-skip'), (t) => {
  return {};
}, 'adm_skip', () => {});

do_on_click(document.getElementById('adm-toggle'), (t) => {
  return {};
}, 'toggle_dec_mode', () => {});

for (elem of document.getElementsByClassName('fa-trash')) {
  do_on_click(elem, (t) => {
    return {'option': parseInt(t.attributes['option'].value) - 1};
  }, 'del', alert);
}

for (elem of document.getElementsByClassName('fa-gavel')) {
  do_on_click(elem, (t) => {
    return {'target': t.attributes["name"].value};
  }, 'adm_kick', alert);
}