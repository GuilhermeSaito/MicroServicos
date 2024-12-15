document.addEventListener("DOMContentLoaded", () => {
  const params = new URLSearchParams(window.location.search);
  const username = params.get("username");
  const usernameDisplay = document.getElementById("usernameDisplay");

  if (username) {
    usernameDisplay.textContent = username;
  } else {
    alert("Nome de usuário não encontrado. Redirecionando para a página de login...");
    window.location.href = "login.html";
    return;
  }

  // Chamar a API para buscar os produtos
  fetch("http://localhost:5001/estoque/getall")
    .then((response) => {
      if (!response.ok) {
        throw new Error("Erro ao buscar produtos.");
      }
      return response.json();
    })
    .then((products) => renderProducts(products))
    .catch((error) => console.error("Erro:", error));
});

// Mapeamento para armazenar os produtos
let productMap = {};

function renderProducts(products) {
  const productList = document.getElementById("productList");
  let totalQuantity = 0;

  products.forEach((product) => {
    // Atualiza a quantidade total
    totalQuantity += product.quantidade;

    // Adiciona o produto ao mapeamento
    productMap[product.id] = product.nome;

    // Criação do elemento do produto
    const productDiv = document.createElement("div");
    productDiv.classList.add("product");

    const productName = document.createElement("span");
    productName.textContent = `${product.nome} (Em estoque: ${product.quantidade})`;

    const controls = document.createElement("div");

    const decreaseBtn = document.createElement("button");
    decreaseBtn.textContent = "-";
    decreaseBtn.addEventListener("click", () => updateQuantity(product.id, -1));

    const selectedQuantity = document.createElement("span");
    selectedQuantity.id = `quantity-${product.id}`;
    selectedQuantity.textContent = "0";

    const increaseBtn = document.createElement("button");
    increaseBtn.textContent = "+";
    increaseBtn.addEventListener("click", () => updateQuantity(product.id, 1));

    controls.appendChild(decreaseBtn);
    controls.appendChild(selectedQuantity);
    controls.appendChild(increaseBtn);

    productDiv.appendChild(productName);
    productDiv.appendChild(controls);
    productList.appendChild(productDiv);
  });

  // Exibir a quantidade total
  const totalQuantityDiv = document.createElement("div");
  totalQuantityDiv.textContent = `Quantidade total de produtos no estoque: ${totalQuantity}`;
  productList.appendChild(totalQuantityDiv);
}

// Armazenar as quantidades selecionadas pelo usuário
const selectedQuantities = {};

function updateQuantity(productId, change) {
  if (!selectedQuantities[productId]) {
    selectedQuantities[productId] = 0;
  }
  selectedQuantities[productId] += change;

  if (selectedQuantities[productId] < 0) {
    selectedQuantities[productId] = 0;
  }

  const quantityDisplay = document.getElementById(`quantity-${productId}`);
  quantityDisplay.textContent = selectedQuantities[productId];
}

// Função para enviar os pedidos
function sendOrders(itemsToBuy, username) {
  // Cria um array de Promises para a primeira API
  const itemRequests = itemsToBuy.map((item) => {
    const body = {
      nome: item.nome,
      quantidade: item.quantidade,
      cliente: username,
    };

    return fetch("http://localhost:5000/produtos/create", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(body),
    }).then((response) => {
      if (!response.ok) {
        throw new Error(`Erro ao enviar o produto ${item.nome}`);
      }
      // Após o sucesso da segunda API, redireciona para a tela de pagamento
      const username = document.getElementById("usernameDisplay").textContent;

      // Montar os parâmetros da URL
      const queryParams = new URLSearchParams();
      queryParams.append("username", username);

      itemsToBuy.forEach((item, index) => {
        queryParams.append(`items[${index}][nome]`, item.nome);
        queryParams.append(`items[${index}][quantidade]`, item.quantidade);
      });

      window.location.href = `carrinho.html?${queryParams.toString()}`;
      // return response.json();
    });
  });

  // Executa todas as requisições para a primeira API
  // Promise.all(itemRequests)
  //   .then(() => {
  //     // Após o sucesso da primeira API, chama a segunda API
  //     const orderBody = {
  //       cliente: username,
  //     };

  //     return fetch("http://localhost:5000/produtos/pedidos/create", {
  //       method: "POST",
  //       headers: {
  //         "Content-Type": "application/json",
  //       },
  //       body: JSON.stringify(orderBody),
  //     });
  //   })
  //   .then((response) => {
  //     if (!response.ok) {
  //       throw new Error("Erro ao criar o pedido.");
  //     }
  //     return response.json();
  //   })
  //   .then(() => {
      
  //   })
  //   .catch((error) => {
  //     console.error("Erro no processo de compra:", error);
  //     alert("Ocorreu um erro ao realizar a compra. Tente novamente.");
  //   });
}

// Evento de clique no botão "Comprar"
document.getElementById("cartButton").addEventListener("click", () => {
  const itemsToBuy = Object.entries(selectedQuantities)
    .filter(([_, quantity]) => quantity > 0)
    .map(([id, quantity]) => ({
      nome: productMap[id], // Nome do produto conforme exibido
      quantidade: quantity,
    }));

  if (itemsToBuy.length === 0) {
    alert("Nenhum item selecionado para compra!");
    return;
  }

  const username = document.getElementById("usernameDisplay").textContent;

  // Enviar os pedidos
  sendOrders(itemsToBuy, username);
});
