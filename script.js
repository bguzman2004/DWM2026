// Datos del menú de El Mariachi
const menu = [
    { nombre: "Tacos al Pastor", categoria: "Tacos", precio: 2500 },
    { nombre: "Burrito Especial", categoria: "Burritos", precio: 4500 },
    { nombre: "Nachos Supreme", categoria: "Nachos", precio: 3500 },
    { nombre: "Quesadilla Mixta", categoria: "Otros", precio: 3200 }
];

// Renderiza la lista de platillos en el menú (manipulación del DOM)
function renderMenu() {
    const listaMenu = document.getElementById("listaMenu");
    listaMenu.innerHTML = "";

    menu.forEach((platillo) => {
        const li = document.createElement("li");

        const nombreSpan = document.createElement("span");
        nombreSpan.textContent = platillo.nombre;

        const precioSpan = document.createElement("span");
        precioSpan.classList.add("precio");
        precioSpan.textContent = `$${platillo.precio.toLocaleString("es-CL")}`;

        li.appendChild(nombreSpan);
        li.appendChild(precioSpan);
        listaMenu.appendChild(li);
    });
}

// Llena el select del formulario "Pedido Rápido" con los platillos
function renderSelectPlatillos() {
    const select = document.getElementById("selectPlatillo");

    menu.forEach((platillo) => {
        const option = document.createElement("option");
        option.value = platillo.nombre;
        option.textContent = `${platillo.nombre} - $${platillo.precio.toLocaleString("es-CL")}`;
        select.appendChild(option);
    });
}

// Maneja el envío del formulario de pedido rápido
function initFormPedido() {
    const form = document.getElementById("formPedido");
    const mensaje = document.getElementById("mensajePedido");

    form.addEventListener("submit", (evento) => {
        evento.preventDefault();

        const platillo = document.getElementById("selectPlatillo").value;
        const nombre = document.getElementById("nombreCliente").value;

        mensaje.textContent = `¡Gracias ${nombre}! Tu pedido de "${platillo}" fue recibido.`;

        form.reset();
    });
}

// Maneja el cambio entre las pestañas "Menú" y "Nosotros"
function initTabs() {
    const botones = document.querySelectorAll(".tab-btn");
    const menuContenido = document.getElementById("menuContenido");
    const nosotrosContenido = document.getElementById("nosotrosContenido");

    botones.forEach((boton) => {
        boton.addEventListener("click", () => {
            botones.forEach((b) => b.classList.remove("active"));
            boton.classList.add("active");

            if (boton.dataset.categoria === "Nosotros") {
                menuContenido.classList.add("hidden");
                nosotrosContenido.classList.remove("hidden");
            } else {
                menuContenido.classList.remove("hidden");
                nosotrosContenido.classList.add("hidden");
            }
        });
    });
}

// Inicializa todo cuando el DOM está listo
document.addEventListener("DOMContentLoaded", () => {
    renderMenu();
    renderSelectPlatillos();
    initFormPedido();
    initTabs();
});
