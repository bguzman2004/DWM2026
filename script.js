// ============================
// DATOS DEL MENÚ
// ============================
const menu = [
    { id: 1, nombre: "Tacos al Pastor", categoria: "Tacos", precio: 2500 },
    { id: 2, nombre: "Burrito Especial", categoria: "Burritos", precio: 4500 },
    { id: 3, nombre: "Nachos Supreme", categoria: "Nachos", precio: 3500 },
    { id: 4, nombre: "Quesadilla Mixta", categoria: "Otros", precio: 3200 }
];

// Carrito en memoria (no usa backend, solo estado local del navegador)
let carrito = [];
let filtroCategoriaActual = "Todos";

// ============================
// NAVEGACIÓN ENTRE VISTAS
// ============================
function mostrarVista(nombreVista) {
    document.querySelectorAll(".vista").forEach((vista) => {
        vista.classList.add("hidden");
    });
    document.getElementById(`vista-${nombreVista}`).classList.remove("hidden");

    document.querySelectorAll(".nav-btn").forEach((btn) => {
        btn.classList.toggle("active", btn.dataset.vista === nombreVista);
    });
}

function initNavegacion() {
    document.querySelectorAll(".nav-btn").forEach((btn) => {
        btn.addEventListener("click", () => mostrarVista(btn.dataset.vista));
    });

    document.getElementById("btnVerMenu").addEventListener("click", () => {
        mostrarVista("menu");
    });
}

// ============================
// VISTA MENÚ: render + filtros + búsqueda
// ============================
function renderMenu() {
    const listaMenu = document.getElementById("listaMenu");
    const sinResultados = document.getElementById("sinResultados");
    const textoBusqueda = document.getElementById("buscarPlatillo").value.trim().toLowerCase();

    listaMenu.innerHTML = "";

    const platillosFiltrados = menu.filter((platillo) => {
        const coincideCategoria = filtroCategoriaActual === "Todos" || platillo.categoria === filtroCategoriaActual;
        const coincideBusqueda = platillo.nombre.toLowerCase().includes(textoBusqueda);
        return coincideCategoria && coincideBusqueda;
    });

    if (platillosFiltrados.length === 0) {
        sinResultados.classList.remove("hidden");
    } else {
        sinResultados.classList.add("hidden");
    }

    platillosFiltrados.forEach((platillo) => {
        const li = document.createElement("li");

        const infoDiv = document.createElement("div");
        infoDiv.classList.add("info-platillo");

        const nombreSpan = document.createElement("span");
        nombreSpan.textContent = platillo.nombre;

        const catSpan = document.createElement("span");
        catSpan.classList.add("categoria-tag");
        catSpan.textContent = platillo.categoria;

        infoDiv.appendChild(nombreSpan);
        infoDiv.appendChild(catSpan);

        const precioSpan = document.createElement("span");
        precioSpan.classList.add("precio");
        precioSpan.textContent = `$${platillo.precio.toLocaleString("es-CL")}`;

        const btnAgregar = document.createElement("button");
        btnAgregar.classList.add("btn-agregar");
        btnAgregar.textContent = "Agregar";
        btnAgregar.addEventListener("click", () => agregarAlCarrito(platillo));

        li.appendChild(infoDiv);
        li.appendChild(precioSpan);
        li.appendChild(btnAgregar);
        listaMenu.appendChild(li);
    });
}

function initFiltrosYBusqueda() {
    document.querySelectorAll(".filtro-btn").forEach((btn) => {
        btn.addEventListener("click", () => {
            document.querySelectorAll(".filtro-btn").forEach((b) => b.classList.remove("active"));
            btn.classList.add("active");
            filtroCategoriaActual = btn.dataset.cat;
            renderMenu();
        });
    });

    document.getElementById("buscarPlatillo").addEventListener("input", renderMenu);
}

// ============================
// CARRITO
// ============================
function agregarAlCarrito(platillo) {
    const existente = carrito.find((item) => item.id === platillo.id);
    if (existente) {
        existente.cantidad += 1;
    } else {
        carrito.push({ ...platillo, cantidad: 1 });
    }
    renderCarrito();
    mostrarVista("pedido");
}

function quitarDelCarrito(id) {
    carrito = carrito.filter((item) => item.id !== id);
    renderCarrito();
}

function calcularTotal() {
    return carrito.reduce((total, item) => total + item.precio * item.cantidad, 0);
}

function renderCarrito() {
    const lista = document.getElementById("carritoLista");
    const totalSpan = document.getElementById("carritoTotal");
    const vacioMsg = document.getElementById("carritoVacioMsg");
    const contador = document.getElementById("carritoContador");

    lista.innerHTML = "";

    if (carrito.length === 0) {
        vacioMsg.classList.remove("hidden");
    } else {
        vacioMsg.classList.add("hidden");
    }

    carrito.forEach((item) => {
        const li = document.createElement("li");

        const textoSpan = document.createElement("span");
        textoSpan.textContent = `${item.cantidad}x ${item.nombre} - $${(item.precio * item.cantidad).toLocaleString("es-CL")}`;

        const btnQuitar = document.createElement("button");
        btnQuitar.classList.add("quitar");
        btnQuitar.textContent = "Quitar";
        btnQuitar.addEventListener("click", () => quitarDelCarrito(item.id));

        li.appendChild(textoSpan);
        li.appendChild(btnQuitar);
        lista.appendChild(li);
    });

    totalSpan.textContent = `$${calcularTotal().toLocaleString("es-CL")}`;
    contador.textContent = carrito.reduce((total, item) => total + item.cantidad, 0);
}

// ============================
// VALIDACIONES DEL FORMULARIO
// ============================
function validarNombre(valor) {
    return valor.trim().length >= 3;
}

function validarTelefono(valor) {
    // Acepta formatos como 912345678, +56912345678, 9 1234 5678
    const regex = /^(\+?56)?\s?9\d{8}$/;
    return regex.test(valor.replace(/\s/g, ""));
}

function validarEmail(valor) {
    if (valor.trim() === "") return true; // opcional
    const regex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return regex.test(valor.trim());
}

function mostrarError(idCampo, idError, mensaje) {
    document.getElementById(idCampo).classList.add("input-error");
    document.getElementById(idError).textContent = mensaje;
}

function limpiarError(idCampo, idError) {
    document.getElementById(idCampo).classList.remove("input-error");
    document.getElementById(idError).textContent = "";
}

function validarFormularioPedido() {
    let esValido = true;

    const nombre = document.getElementById("nombreCliente").value;
    const telefono = document.getElementById("telefonoCliente").value;
    const email = document.getElementById("emailCliente").value;

    if (!validarNombre(nombre)) {
        mostrarError("nombreCliente", "errorNombre", "Ingresa tu nombre completo (mínimo 3 caracteres).");
        esValido = false;
    } else {
        limpiarError("nombreCliente", "errorNombre");
    }

    if (!validarTelefono(telefono)) {
        mostrarError("telefonoCliente", "errorTelefono", "Ingresa un teléfono válido (ej: 912345678).");
        esValido = false;
    } else {
        limpiarError("telefonoCliente", "errorTelefono");
    }

    if (!validarEmail(email)) {
        mostrarError("emailCliente", "errorEmail", "El formato del correo no es válido.");
        esValido = false;
    } else {
        limpiarError("emailCliente", "errorEmail");
    }

    if (carrito.length === 0) {
        alert("Tu carrito está vacío. Agrega al menos un platillo desde el Menú antes de confirmar.");
        esValido = false;
    }

    return esValido;
}

// ============================
// CONTADOR DE CARACTERES (notas)
// ============================
function initContadorNotas() {
    const textarea = document.getElementById("notasCliente");
    const contador = document.getElementById("contadorNotas");

    textarea.addEventListener("input", () => {
        contador.textContent = `${textarea.value.length}/200`;
    });
}

// ============================
// ENVÍO DEL PEDIDO Y CONFIRMACIÓN
// ============================
function generarNumeroOrden() {
    return "MRC-" + Math.floor(100000 + Math.random() * 900000);
}

function initFormPedido() {
    const form = document.getElementById("formPedido");

    form.addEventListener("submit", (evento) => {
        evento.preventDefault();

        if (!validarFormularioPedido()) {
            return;
        }

        const nombre = document.getElementById("nombreCliente").value.trim();
        const telefono = document.getElementById("telefonoCliente").value.trim();

        // Rellena la vista de confirmación con los datos reales (manipulación del DOM)
        document.getElementById("confNumero").textContent = generarNumeroOrden();
        document.getElementById("confFecha").textContent = new Date().toLocaleString("es-CL");
        document.getElementById("confCliente").textContent = nombre;
        document.getElementById("confTelefono").textContent = telefono;
        document.getElementById("confTotal").textContent = `$${calcularTotal().toLocaleString("es-CL")}`;

        const confItems = document.getElementById("confItems");
        confItems.innerHTML = "";
        carrito.forEach((item) => {
            const li = document.createElement("li");
            li.textContent = `${item.cantidad}x ${item.nombre} - $${(item.precio * item.cantidad).toLocaleString("es-CL")}`;
            confItems.appendChild(li);
        });

        mostrarVista("confirmacion");
    });

    document.getElementById("btnNuevoPedido").addEventListener("click", () => {
        carrito = [];
        renderCarrito();
        form.reset();
        document.getElementById("contadorNotas").textContent = "0/200";
        mostrarVista("inicio");
    });
}

// ============================
// INICIALIZACIÓN
// ============================
document.addEventListener("DOMContentLoaded", () => {
    initNavegacion();
    renderMenu();
    initFiltrosYBusqueda();
    renderCarrito();
    initContadorNotas();
    initFormPedido();
});
