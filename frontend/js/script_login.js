document.getElementById('confirmBtn').addEventListener('click', () => {
  const username = document.getElementById('username').value.trim();

  if (username) {
    // Redirecionar para a página principal com o username como parâmetro na URL
    window.location.href = `main_page.html?username=${encodeURIComponent(username)}`;
  } else {
    alert("Por favor, insira um nome válido.");
  }
});
