document.addEventListener("DOMContentLoaded", () => {
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
  
      // Remove a mensagem de "Aguardando notificações" se existia
      const placeholder = notificationsContainer.querySelector("p");
      if (placeholder) placeholder.remove();
  
      // Rola automaticamente para a última notificação
      notificationsContainer.scrollTop = notificationsContainer.scrollHeight;
    };
  
    eventSource.onerror = () => {
      console.error("Erro na conexão com o servidor SSE.");
    };
  });
  