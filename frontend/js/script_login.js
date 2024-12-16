// Função para redirecionar o usuário após confirmar o username
document.getElementById('confirmBtn').addEventListener('click', () => {
  const username = document.getElementById('username').value.trim();

  if (username) {
    // Redirecionar para a página principal com o username como parâmetro na URL
    window.location.href = `main_page.html?username=${encodeURIComponent(username)}`;
  } else {
    alert("Por favor, insira um nome válido.");
  }
});

// Função para iniciar a conexão SSE e receber notificações
document.getElementById('sseBtn').addEventListener('click', () => {
  const notificationsContainer = document.getElementById("notifications");

  // Conexão ao endpoint SSE
  const eventSource = new EventSource("http://localhost:5004/stream");

  eventSource.onmessage = (event) => {
    alert(event.data);
    // Parsea a notificação recebida
    const data = JSON.parse(event.data);

    // Cria o elemento de notificação
    const notificationElement = document.createElement("div");
    notificationElement.className = "notification";
    notificationElement.innerHTML = `
      <strong>ID do Pedido:</strong> ${data}<br>
    `;

    // Adiciona um estilo diferente para erros
    if (data[1].includes("Recusado")) {
      notificationElement.classList.add("error");
    }

    // Adiciona a notificação ao container
    notificationsContainer.appendChild(notificationElement);

    // Remove a mensagem de "Aguardando notificações" se existir
    const placeholder = notificationsContainer.querySelector("p");
    if (placeholder) placeholder.remove();

    // Rola automaticamente para a última notificação
    notificationsContainer.scrollTop = notificationsContainer.scrollHeight;
  };

  eventSource.onerror = () => {
    console.error("Erro na conexão com o servidor SSE.");
  };

  // Desabilita o botão para evitar múltiplas conexões
  document.getElementById('sseBtn').disabled = true;
  alert("Conexão com o servidor iniciada. Aguardando notificações...");
});
