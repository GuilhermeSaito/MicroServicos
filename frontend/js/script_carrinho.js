document.addEventListener("DOMContentLoaded", () => {
  const params = new URLSearchParams(window.location.search);
  const username = params.get("username");
  const cartInfo = document.getElementById("cartInfo");

  if (!username) {
    alert("Nome de usuário não encontrado. Redirecionando para a página principal...");
    window.location.href = "main.html";
    return;
  }

  // Exibir o nome do usuário
  const userInfo = document.createElement("h2");
  userInfo.textContent = `Cliente: ${username}`;
  cartInfo.appendChild(userInfo);

  // Processar os itens selecionados
  const items = [];
  params.forEach((value, key) => {
    const match = key.match(/items\[(\d+)\]\[(\w+)\]/);
    if (match) {
      const index = match[1];
      const field = match[2];

      if (!items[index]) {
        items[index] = {};
      }
      items[index][field] = field === "quantidade" ? parseInt(value) : value;
    }
  });

  if (items.length === 0) {
    alert("Nenhum item encontrado no carrinho.");
    window.location.href = "main.html";
    return;
  }

  // Exibir os itens selecionados
  const itemList = document.createElement("ul");

  items.forEach((item, index) => {
    const listItem = document.createElement("li");
    listItem.dataset.index = index;

    const itemInfo = document.createElement("span");
    itemInfo.textContent = `Produto: ${item.nome} | Quantidade: ${item.quantidade}`;

    const deleteButton = document.createElement("button");
    deleteButton.textContent = "Deletar";
    deleteButton.classList.add("delete-button");
    deleteButton.addEventListener("click", () => deleteItem(item, index));

    listItem.appendChild(itemInfo);
    listItem.appendChild(deleteButton);
    itemList.appendChild(listItem);
  });

  cartInfo.appendChild(itemList);

  const buyButton = document.createElement("button");
  buyButton.textContent = "Comprar";
  buyButton.classList.add("buy-button");
  buyButton.addEventListener("click", () => processPurchase(username, items));
  cartInfo.appendChild(buyButton);
});

// Função para deletar um item
function deleteItem(item, index) {
  const cartInfo = document.getElementById("cartInfo");

  fetch("http://localhost:5000/produtos/remove", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      nome: item.nome,
      quantidade: item.quantidade,
      cliente: document.querySelector("h2").textContent.replace("Cliente: ", ""),
    }),
  })
    .then((response) => {
      if (!response.ok) {
        throw new Error("Erro ao deletar o item.");
      }
      return response.json();
    })
    .then(() => {
      alert(`Item "${item.nome}" foi deletado com sucesso.`);
      const listItem = document.querySelector(`li[data-index="${index}"]`);
      listItem.remove();

      // Verifica se há mais itens no carrinho
      if (!document.querySelector("ul").hasChildNodes()) {
        const noItemsMessage = document.createElement("p");
        noItemsMessage.textContent = "Seu carrinho está vazio.";
        cartInfo.appendChild(noItemsMessage);
      }
    })
    .catch((error) => {
      console.error("Erro:", error);
      alert("Não foi possível deletar o item. Tente novamente.");
    });
}

// Função para processar a compra
function processPurchase(username, items) {
  if (items.length === 0) {
    alert("Seu carrinho está vazio. Adicione itens antes de comprar.");
    return;
  }

  // Chamar a API para criar pedidos
  fetch("http://localhost:5000/produtos/pedidos/create", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      cliente: username,
    }),
  })
    .then((response) => {
      if (!response.ok) {
        throw new Error("Erro ao processar o pedido.");
      }
      return response.json();
    })
    .then(() => {
      // Após criar o pedido, redirecionar para a página de pagamento
      const urlParams = new URLSearchParams();
      urlParams.append("username", username);

      items.forEach((item, index) => {
        urlParams.append(`items[${index}][nome]`, item.nome);
        urlParams.append(`items[${index}][quantidade]`, item.quantidade);
      });

      window.location.href = `pagamento.html?${urlParams.toString()}`;
    })
    .catch((error) => {
      console.error("Erro:", error);
      alert("Não foi possível finalizar a compra. Tente novamente.");
    });
}
