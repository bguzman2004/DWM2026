// ============================
// DATOS DEL MENÚ
// ============================
const menu = [
    { id: 1, nombre: "Tacos al Pastor", categoria: "Tacos", precio: 2500, descripcion: "Cerdo marinado, piña, cebolla y cilantro.", icono: "fa-solid fa-pepper-hot" },
    { id: 2, nombre: "Tacos de Carnitas", categoria: "Tacos", precio: 2500, descripcion: "Cerdo cocido lento, salsa verde.", icono: "fa-solid fa-pepper-hot" },
    { id: 3, nombre: "Tacos de Birria", categoria: "Tacos", precio: 3000, descripcion: "Res braseada, consomé para remojar.", icono: "fa-solid fa-pepper-hot" },
    { id: 4, nombre: "Burrito Especial", categoria: "Burritos", precio: 4500, descripcion: "Arroz, frijoles, carne asada, queso y salsa.", icono: "fa-solid fa-bacon" },
    { id: 5, nombre: "Burrito de Pollo", categoria: "Burritos", precio: 4200, descripcion: "Pollo asado, arroz, frijoles y pico de gallo.", icono: "fa-solid fa-bacon" },
    { id: 6, nombre: "Burrito Vegetariano", categoria: "Burritos", precio: 4000, descripcion: "Frijoles, arroz, verduras salteadas, queso.", icono: "fa-solid fa-bacon" },
    { id: 7, nombre: "Nachos Supreme", categoria: "Nachos", precio: 3500, descripcion: "Queso derretido, jalapeños, pico de gallo, guacamole.", icono: "fa-solid fa-cheese" },
    { id: 8, nombre: "Nachos con Carne", categoria: "Nachos", precio: 4200, descripcion: "Carne molida sazonada, queso, guacamole.", icono: "fa-solid fa-cheese" },
    { id: 9, nombre: "Agua de Horchata", categoria: "Bebidas", precio: 1800, descripcion: "Arroz, canela y vainilla.", icono: "fa-solid fa-mug-saucer" },
    { id: 10, nombre: "Agua de Jamaica", categoria: "Bebidas", precio: 1800, descripcion: "Flor de jamaica, refrescante y natural.", icono: "fa-solid fa-mug-saucer" },
    { id: 11, nombre: "Quesadilla Mixta", categoria: "Otros", precio: 3200, descripcion: "Queso, pollo y pimientos gratinados.", icono: "fa-solid fa-utensils" },
    { id: 12, nombre: "Elote Preparado", categoria: "Otros", precio: 2000, descripcion: "Mayonesa, queso rallado y chile en polvo.", icono: "fa-solid fa-utensils" }
];

const claseImagenPorCategoria = {
    "Tacos": "img-tacos",
    "Burritos": "img-burritos",
    "Nachos": "img-nachos",
    "Bebidas": "img-bebidas",
    "Otros": "img-otros"
};

const PROMO_2X1 = [1];
const MAX_CANTIDAD = 20;
const CLAVE_CARRITO = "mariachi-carrito";

let carrito = [];
let filtroCategoriaActual = "Todos";
let platilloSeleccionado = null;
let cantidadDetalle = 1;

// ============================
// UTILIDADES
// ============================
function formatoPesos(monto) {
    return `$${monto.toLocaleString("es-CL")}`;
}

function normalizar(texto) {
    return texto.normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase().trim();
}

function tienePromo(id) {
    return PROMO_2X1.includes(id);
}

function descuentoLinea(id, precio, cantidad) {
    return tienePromo(id) ? Math.floor(cantidad / 2) * precio : 0;
}

function calcularSubtotal() {
    return carrito.reduce((total, item) => total + item.precio * item.cantidad, 0);
}

function calcularDescuento() {
    return carrito.reduce((total, item) => total + descuentoLinea(item.id, item.precio, item.cantidad), 0);
}

function calcularTotal() {
    return calcularSubtotal() - calcularDescuento();
}

function guardarCarrito() {
    try {
        localStorage.setItem(CLAVE_CARRITO, JSON.stringify(carrito.map((item) => ({ id: item.id, cantidad: item.cantidad }))));
    } catch (error) {
        return;
    }
}

function cargarCarrito() {
    try {
        const guardado = JSON.parse(localStorage.getItem(CLAVE_CARRITO) || "[]");
        carrito = guardado
            .map((linea) => {
                const platillo = menu.find((p) => p.id === linea.id);
                const cantidad = Math.min(Math.max(parseInt(linea.cantidad, 10) || 0, 0), MAX_CANTIDAD);
                return platillo && cantidad > 0 ? { ...platillo, cantidad } : null;
            })
            .filter(Boolean);
    } catch (error) {
        carrito = [];
    }
}

function mostrarAviso(mensaje) {
    const aviso = document.getElementById("avisoCarrito");
    aviso.textContent = mensaje;
    aviso.classList.remove("hidden");
}

function ocultarAviso() {
    const aviso = document.getElementById("avisoCarrito");
    aviso.textContent = "";
    aviso.classList.add("hidden");
}

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

    // Cierra el menú colapsable de Bootstrap en mobile al navegar
    const navCollapse = document.getElementById("navMenu");
    if (navCollapse.classList.contains("show")) {
        bootstrap.Collapse.getOrCreateInstance(navCollapse).hide();
    }

    window.scrollTo({ top: 0, behavior: "smooth" });
}

function initNavegacion() {
    document.querySelectorAll("[data-vista]").forEach((el) => {
        el.addEventListener("click", (e) => {
            e.preventDefault();
            mostrarVista(el.dataset.vista);
        });
    });

    document.getElementById("btnVerMenu").addEventListener("click", () => {
        mostrarVista("menu");
    });

    document.getElementById("btnVerPromo").addEventListener("click", () => {
        mostrarDetalle(menu.find((p) => p.id === PROMO_2X1[0]));
    });
}

// ============================
// VISTA MENÚ: render + filtros + búsqueda
// ============================
function renderMenu() {
    const listaMenu = document.getElementById("listaMenu");
    const sinResultados = document.getElementById("sinResultados");
    const textoBusqueda = normalizar(document.getElementById("buscarPlatillo").value);

    listaMenu.innerHTML = "";

    const platillosFiltrados = menu.filter((platillo) => {
        const coincideCategoria = filtroCategoriaActual === "Todos" || platillo.categoria === filtroCategoriaActual;
        const coincideBusqueda = normalizar(platillo.nombre).includes(textoBusqueda);
        return coincideCategoria && coincideBusqueda;
    });

    sinResultados.classList.toggle("hidden", platillosFiltrados.length !== 0);

    platillosFiltrados.forEach((platillo) => {
        const col = document.createElement("div");
        col.classList.add("col-sm-6", "col-lg-4");

        const card = document.createElement("div");
        card.classList.add("platillo-card");
        card.setAttribute("role", "button");
        card.setAttribute("tabindex", "0");
        card.setAttribute("aria-label", `Ver detalle de ${platillo.nombre}`);
        card.addEventListener("click", () => mostrarDetalle(platillo));
        card.addEventListener("keydown", (e) => {
            if (e.target === card && (e.key === "Enter" || e.key === " ")) {
                e.preventDefault();
                mostrarDetalle(platillo);
            }
        });

        const imagen = document.createElement("div");
        imagen.classList.add("platillo-imagen", claseImagenPorCategoria[platillo.categoria]);
        const iconoImg = document.createElement("i");
        iconoImg.className = platillo.icono;
        imagen.appendChild(iconoImg);

        if (tienePromo(platillo.id)) {
            const promoTag = document.createElement("span");
            promoTag.classList.add("promo-tag");
            promoTag.textContent = "2x1 hoy";
            imagen.appendChild(promoTag);
        }

        const body = document.createElement("div");
        body.classList.add("platillo-body");

        const catTag = document.createElement("span");
        catTag.classList.add("categoria-tag");
        catTag.textContent = platillo.categoria;

        const titulo = document.createElement("h3");
        titulo.textContent = platillo.nombre;

        const descripcion = document.createElement("p");
        descripcion.classList.add("platillo-descripcion");
        descripcion.textContent = platillo.descripcion;

        const precio = document.createElement("p");
        precio.classList.add("platillo-precio");
        precio.textContent = formatoPesos(platillo.precio);

        const btnAgregar = document.createElement("button");
        btnAgregar.type = "button";
        btnAgregar.classList.add("btn-agregar");
        btnAgregar.innerHTML = `<i class="fa-solid fa-cart-plus"></i> Agregar`;
        btnAgregar.addEventListener("click", (e) => {
            e.stopPropagation(); // no abrir el detalle, es un agregado rápido
            agregarAlCarrito(platillo, 1);
        });

        body.appendChild(catTag);
        body.appendChild(titulo);
        body.appendChild(descripcion);
        body.appendChild(precio);
        body.appendChild(btnAgregar);

        card.appendChild(imagen);
        card.appendChild(body);
        col.appendChild(card);
        listaMenu.appendChild(col);
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
function agregarAlCarrito(platillo, cantidad = 1) {
    const existente = carrito.find((item) => item.id === platillo.id);
    const actual = existente ? existente.cantidad : 0;
    const nueva = Math.min(actual + cantidad, MAX_CANTIDAD);

    if (existente) {
        existente.cantidad = nueva;
    } else {
        carrito.push({ ...platillo, cantidad: nueva });
    }

    renderCarrito();
    mostrarVista("pedido");

    if (actual + cantidad > MAX_CANTIDAD) {
        mostrarAviso(`Puedes pedir hasta ${MAX_CANTIDAD} unidades de ${platillo.nombre} por pedido.`);
    } else {
        ocultarAviso();
    }
}

function cambiarCantidad(id, delta) {
    const item = carrito.find((linea) => linea.id === id);
    if (!item) return;

    const nueva = item.cantidad + delta;
    if (nueva < 1) {
        quitarDelCarrito(id);
        return;
    }
    if (nueva > MAX_CANTIDAD) {
        mostrarAviso(`Puedes pedir hasta ${MAX_CANTIDAD} unidades de ${item.nombre} por pedido.`);
        return;
    }

    item.cantidad = nueva;
    ocultarAviso();
    renderCarrito();
}

// ============================
// VISTA DETALLE PRODUCTO (Menú -> Detalle -> Carrito, como en el boceto)
// ============================
function mostrarDetalle(platillo) {
    platilloSeleccionado = platillo;
    cantidadDetalle = 1;
    renderDetalle();
    mostrarVista("detalle");
}

function renderDetalle() {
    if (!platilloSeleccionado) return;

    const imagen = document.getElementById("detalleImagen");
    imagen.className = `detalle-imagen ${claseImagenPorCategoria[platilloSeleccionado.categoria]}`;
    imagen.innerHTML = `<i class="${platilloSeleccionado.icono}"></i>`;

    const descuento = descuentoLinea(platilloSeleccionado.id, platilloSeleccionado.precio, cantidadDetalle);
    const subtotal = platilloSeleccionado.precio * cantidadDetalle - descuento;

    document.getElementById("detalleCategoria").textContent = platilloSeleccionado.categoria;
    document.getElementById("detalleNombre").textContent = platilloSeleccionado.nombre;
    document.getElementById("detalleDescripcion").textContent = platilloSeleccionado.descripcion;
    document.getElementById("detallePrecioUnitario").textContent = `${formatoPesos(platilloSeleccionado.precio)} c/u`;
    document.getElementById("detalleCantidad").textContent = cantidadDetalle;
    document.getElementById("detalleSubtotal").textContent = formatoPesos(subtotal);
    document.getElementById("detalleMenos").disabled = cantidadDetalle <= 1;
    document.getElementById("detalleMas").disabled = cantidadDetalle >= MAX_CANTIDAD;

    const promo = document.getElementById("detallePromo");
    if (tienePromo(platilloSeleccionado.id)) {
        promo.textContent = descuento > 0
            ? `Promoción 2x1 aplicada: ahorras ${formatoPesos(descuento)}.`
            : "Promoción 2x1: agrega otra unidad y te sale gratis.";
        promo.classList.remove("hidden");
    } else {
        promo.classList.add("hidden");
    }
}

function initDetalle() {
    document.getElementById("detalleMenos").addEventListener("click", () => {
        if (cantidadDetalle > 1) {
            cantidadDetalle -= 1;
            renderDetalle();
        }
    });

    document.getElementById("detalleMas").addEventListener("click", () => {
        if (cantidadDetalle < MAX_CANTIDAD) {
            cantidadDetalle += 1;
            renderDetalle();
        }
    });

    document.getElementById("btnAgregarDesdeDetalle").addEventListener("click", () => {
        agregarAlCarrito(platilloSeleccionado, cantidadDetalle);
    });

    document.getElementById("btnVolverAlMenu").addEventListener("click", () => {
        mostrarVista("menu");
    });
}

function quitarDelCarrito(id) {
    carrito = carrito.filter((item) => item.id !== id);
    ocultarAviso();
    renderCarrito();
}

function textoLinea(item) {
    const descuento = descuentoLinea(item.id, item.precio, item.cantidad);
    const promo = descuento > 0 ? ` (2x1: -${formatoPesos(descuento)})` : "";
    return `${item.nombre} - ${formatoPesos(item.precio * item.cantidad - descuento)}${promo}`;
}

function renderTotales(prefijo) {
    const descuento = calcularDescuento();
    document.getElementById(`${prefijo}Subtotal`).textContent = formatoPesos(calcularSubtotal());
    document.getElementById(`${prefijo}Descuento`).textContent = `-${formatoPesos(descuento)}`;
    document.getElementById(`${prefijo}DescuentoFila`).classList.toggle("hidden", descuento === 0);
    document.getElementById(`${prefijo}Total`).textContent = formatoPesos(calcularTotal());
}

function renderCarrito() {
    const lista = document.getElementById("carritoLista");
    const vacioMsg = document.getElementById("carritoVacioMsg");
    const contador = document.getElementById("carritoContador");

    lista.innerHTML = "";
    vacioMsg.classList.toggle("hidden", carrito.length !== 0);

    carrito.forEach((item) => {
        const li = document.createElement("li");

        const textoSpan = document.createElement("span");
        textoSpan.classList.add("linea-texto");
        textoSpan.textContent = textoLinea(item);

        const acciones = document.createElement("div");
        acciones.classList.add("linea-acciones");

        const btnMenos = document.createElement("button");
        btnMenos.type = "button";
        btnMenos.classList.add("cantidad-btn");
        btnMenos.textContent = "−";
        btnMenos.setAttribute("aria-label", `Quitar una unidad de ${item.nombre}`);
        btnMenos.addEventListener("click", () => cambiarCantidad(item.id, -1));

        const cantidad = document.createElement("span");
        cantidad.classList.add("cantidad-valor");
        cantidad.textContent = item.cantidad;

        const btnMas = document.createElement("button");
        btnMas.type = "button";
        btnMas.classList.add("cantidad-btn");
        btnMas.textContent = "+";
        btnMas.disabled = item.cantidad >= MAX_CANTIDAD;
        btnMas.setAttribute("aria-label", `Agregar una unidad de ${item.nombre}`);
        btnMas.addEventListener("click", () => cambiarCantidad(item.id, 1));

        const btnQuitar = document.createElement("button");
        btnQuitar.type = "button";
        btnQuitar.classList.add("quitar");
        btnQuitar.textContent = "Quitar";
        btnQuitar.addEventListener("click", () => quitarDelCarrito(item.id));

        acciones.appendChild(btnMenos);
        acciones.appendChild(cantidad);
        acciones.appendChild(btnMas);
        acciones.appendChild(btnQuitar);

        li.appendChild(textoSpan);
        li.appendChild(acciones);
        lista.appendChild(li);
    });

    renderTotales("carrito");
    contador.textContent = carrito.reduce((total, item) => total + item.cantidad, 0);
    guardarCarrito();
}

// ============================
// VALIDACIONES DEL FORMULARIO
// ============================
function validarNombre(valor) {
    return valor.trim().length >= 3;
}

function validarTelefono(valor) {
    const regex = /^(\+?56)?\s?9\d{8}$/;
    return regex.test(valor.replace(/\s/g, ""));
}

function validarEmail(valor) {
    if (valor.trim() === "") return true; // opcional
    const regex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return regex.test(valor.trim());
}

function mostrarError(idCampo, idError, mensaje) {
    const campo = document.getElementById(idCampo);
    campo.classList.add("input-error");
    campo.setAttribute("aria-invalid", "true");
    document.getElementById(idError).textContent = mensaje;
}

function limpiarError(idCampo, idError) {
    const campo = document.getElementById(idCampo);
    campo.classList.remove("input-error");
    campo.removeAttribute("aria-invalid");
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
        mostrarAviso("Tu carrito está vacío. Agrega al menos un platillo desde el Menú antes de confirmar.");
        esValido = false;
    }

    const primerError = document.querySelector("#formPedido .input-error");
    if (primerError) {
        primerError.focus();
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
        const notas = document.getElementById("notasCliente").value.trim();

        document.getElementById("confNumero").textContent = generarNumeroOrden();
        document.getElementById("confFecha").textContent = new Date().toLocaleString("es-CL");
        document.getElementById("confCliente").textContent = nombre;
        document.getElementById("confTelefono").textContent = telefono;
        document.getElementById("confNotas").textContent = notas;
        document.getElementById("confNotasFila").classList.toggle("hidden", notas === "");
        renderTotales("conf");

        const confItems = document.getElementById("confItems");
        confItems.innerHTML = "";
        carrito.forEach((item) => {
            const li = document.createElement("li");
            li.textContent = `${item.cantidad}x ${textoLinea(item)}`;
            confItems.appendChild(li);
        });

        ocultarAviso();
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
// PEDIDO RÁPIDO (cotización directa, sin pasar por el menú completo)
// ============================
function initPedidoRapido() {
    const form = document.getElementById("formPedidoRapido");
    form.addEventListener("submit", (evento) => {
        evento.preventDefault();
        const mensaje = document.getElementById("mensajeRapido").value.trim();
        if (mensaje === "") return;

        const texto = encodeURIComponent(`Hola El Mariachi, quiero cotizar: ${mensaje}`);
        window.open(`https://wa.me/56900000000?text=${texto}`, "_blank", "noopener");
        form.reset();
    });
}

// ============================
// INICIALIZACIÓN
// ============================
document.addEventListener("DOMContentLoaded", () => {
    cargarCarrito();
    initNavegacion();
    renderMenu();
    initFiltrosYBusqueda();
    renderCarrito();
    initContadorNotas();
    initFormPedido();
    initDetalle();
    initPedidoRapido();
});
