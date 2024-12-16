document.addEventListener("DOMContentLoaded", () => {
  const params = new URLSearchParams(window.location.search);
  const username = params.get("username");
  const paymentInfo = document.getElementById("paymentInfo");
  const payButton = document.getElementById("payButton");

  if (!username) {
    alert("Usuário não encontrado. Redirecionando...");
    window.location.href = "main.html";
    return;
  }

  const items = [];
  params.forEach((value, key) => {
    const match = key.match(/items\[(\d+)\]\[(\w+)\]/);
    if (match) {
      const index = match[1];
      const field = match[2];

      if (!items[index]) {
        items[index] = {};
      }

      items[index][field] = field === "quantidade" ? parseInt(value, 10) : value;
    }
  });

  // Exibir resumo do pagamento
  const summary = document.createElement("div");
  summary.innerHTML = `<h2>Resumo do Pedido</h2><p>Cliente: ${username}</p>`;
  const itemList = document.createElement("ul");

  items.forEach((item) => {
    const listItem = document.createElement("li");
    listItem.textContent = `Produto: ${item.nome} | Quantidade: ${item.quantidade}`;
    itemList.appendChild(listItem);
  });

  summary.appendChild(itemList);
  paymentInfo.appendChild(summary);

  // Adicionar evento ao botão "Pagar"
  payButton.addEventListener("click", async () => {
    const payload = {
      transaction_id: username,
      quantidade: 10,
      cliente: username,
    };

    try {
      const response = await fetch("http://localhost:5002/pagamento/create", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(payload),
      });

      if (response.ok) {
        const data = await response.json();
        alert("Pagamento realizado com sucesso!");
        console.log("Resposta da API:", data);
      } else {
        const errorData = await response.json();
        alert("Erro ao realizar o pagamento.");
        console.error("Erro:", errorData);
      }
    } catch (error) {
      alert("Erro de conexão com a API.");
      console.error("Erro de conexão:", error);
    }
  });
});
