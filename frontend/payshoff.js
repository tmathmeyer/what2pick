document.getElementById('add-new-item').addEventListener('click', e => {
  let option = prompt('Add Option');
  if (option === null)
    return
  const gameid = e.target.attributes["gameid"].value;
  fetch(`/p/${gameid}/add`, {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({'option': option})
  }).then((_) => {
    window.location.reload();
  });
});

document.getElementById('select-item').addEventListener('click', e => {
  const gameid = e.target.attributes["gameid"].value;
  fetch(`/p/${gameid}/sel`, {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({})
  }).then((_) => {
    window.location.reload();
  });
});

for (elem of document.getElementsByClassName('fa-trash')) {
  elem.addEventListener('click', e => {
    const gameid = e.target.attributes["gameid"].value;
    const option = parseInt(e.target.attributes["option"].value) - 1;
    fetch(`/p/${gameid}/del`, {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({'option': option})
    }).then((e) => {
      if (e.status == 200)
        window.location.reload();
      return e.text();
    }).then(err => {
      if (err != 'OK')
        alert(err);
    });
  });
}