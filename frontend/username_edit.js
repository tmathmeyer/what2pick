const username = document.getElementById('current-username').textContent;
document.getElementById('username-edit').addEventListener('click', e => {
  let newname = prompt('Change Username', username);
  fetch('/setname', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({'name': newname})
  }).then((_) => {
    window.location.reload();
  });
});