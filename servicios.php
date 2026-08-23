<!DOCTYPE html>
<html lang="es">
    <head>
        <title>Página Principal</title>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.8/dist/css/bootstrap.min.css" rel="stylesheet">
        <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.8/dist/js/bootstrap.bundle.min.js"></script>
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/4.7.0/css/font-awesome.min.css">
    </head>
    <body>
        <!-- Navbar -->
        <nav class="navbar navbar-expand-sm bg-white navbar-light shadow-sm border-bottom">
            <div class="container-fluid">
                <a class="navbar-brand" href="index.php">
                    <img src="img/logo.jpg" alt="Logo" height="60">
                </a>
                <button class="navbar-toggler" type="button" data-bs-toggle="collapse" data-bs-target="#collapsibleNavbar">
                    <span class="navbar-toggler-icon"></span>
                </button>
                <div class="collapse navbar-collapse" id="collapsibleNavbar">
                    <ul class="navbar-nav">
                        <li class="nav-item dropdown">
                            <a class="nav-link dropdown-toggle text-dark" href="#" role="button" data-bs-toggle="dropdown">Empresa</a>
                            <ul class="dropdown-menu">
                                <li><a class="dropdown-item" href="empresa.php">Nuestro Empresa</a></li>
                                <li><a class="dropdown-item" href="#">Nuestro Equipo</a></li>
                                <li><a class="dropdown-item" href="#">Misión</a></li>
                            </ul>
                        </li>                        
                        <li class="nav-item">
                            <a class="nav-link text-dark" href="productos.php">Productos</a>
                        </li>
                        <li class="nav-item">
                            <a class="nav-link text-dark" href="servicios.php">Servicios</a>
                        </li>
                        <li class="nav-item">
                            <a class="nav-link text-dark" href="contacto.php">Contacto</a>
                        </li>
                    </ul>
                </div>
                <button type="button" class="btn btn-outline-primary" data-bs-toggle="modal" data-bs-target="#myModal">Acceder</button>
            </div>
        </nav>

        <!-- Hero Servicios -->
        <div class="container-fluid bg-light py-5">
            <div class="container text-center">
                <h1 class="fw-bold display-5">SERVICIOS</h1>
                <p class="fs-4 text-secondary mb-3">Soluciones informáticas para tus necesidades.</p>
                <p class="fs-5 mx-auto" style="max-width: 700px;">En <strong>INFORMATICS</strong> desarrollamos soluciones tecnológicas adaptadas a cada proyecto, combinando ingeniería informática, desarrollo de software, datos e infraestructura TI.</p>
            </div>
        </div>

        <!-- Nuestros servicios: carrusel de tarjetas -->
        <div class="container my-5">
            <h2 class="fw-bold text-center mb-5">Nuestros servicios</h2>

            <div id="serviciosCarousel" class="carousel slide" data-bs-ride="carousel">
                <!-- Los carousel-item se generan dinámicamente con JavaScript, ver script al final -->
                <div class="carousel-inner" id="serviciosInner"></div>

                <button class="carousel-control-prev" type="button" data-bs-target="#serviciosCarousel" data-bs-slide="prev">
                    <span class="carousel-control-prev-icon" style="filter: invert(1);"></span>
                </button>
                <button class="carousel-control-next" type="button" data-bs-target="#serviciosCarousel" data-bs-slide="next">
                    <span class="carousel-control-next-icon" style="filter: invert(1);"></span>
                </button>

                <div class="carousel-indicators" id="serviciosIndicadores" style="position: static; margin-top: 1.5rem;"></div>
            </div>
        </div>

        <!-- Llamado a la acción -->
        <div class="container-fluid bg-primary py-5">
            <div class="container text-center text-white">
                <h2 class="fw-bold mb-3">¿Tienes un proyecto?</h2>
                <p class="fs-5 mb-4">Cuéntanos qué necesitas y encontraremos una solución tecnológica adecuada para ti.</p>
                <a href="contacto.php" class="btn btn-light btn-lg fw-semibold">Contáctanos →</a>
            </div>
        </div>

        <!-- Footer -->
        <div class="container-fluid bg-dark">
            <div class="row">
                <div class="col-4"></div>
                <div class="col-4 d-flex justify-content-center" 
                style="color:white"><strong>© 2026 INFORMATICS                         Creado por M.CAETEMORA × B.GZMN</strong></div>
                <div class="col-4"></div>
            </div>
        </div>

        <!-- Modal -->
        <div class="modal" id="myModal">
            <div class="modal-dialog">
                <div class="modal-content">
                    <!-- Modal Header -->
                    <div class="modal-header">
                        <h4 class="modal-title">Autenticar</h4>
                        <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                    </div>
                    <!-- Modal body -->
                    <div class="modal-body">
                        <form action="empresa.php">
                            <div class="mb-2 mt-2">
                                <label for="email" class="form-label">Correo:</label>
                                <input type="email" class="form-control" id="email" placeholder="Ingresar Correo" name="email">
                            </div>
                            <div class="mb-2">
                                <label for="pwd" class="form-label">Contraseña:</label>
                                <input type="password" class="form-control" id="pwd" placeholder="Ingresar Contraseña" name="pswd">
                            </div>
                            <div class="form-check mb-2">
                                <label class="form-check-label">
                                <input class="form-check-input" type="checkbox" name="Recordarme"> Recordarme
                                </label>
                            </div>
                            <button type="submit" class="btn btn-primary">Ingresar  <i class="fa fa-check-circle"></i></button>
                        </form>
                    </div>
                    <!-- Modal footer -->
                    <div class="modal-footer">
                        <button type="button" class="btn btn-danger" data-bs-dismiss="modal">Cerrar</button>
                    </div>
                </div>
            </div>
        </div>

        <script>
            const servicios = [
                {
                    numero: "01",
                    titulo: "Desarrollo Web",
                    descripcion: "Creamos páginas web modernas, rápidas y adaptadas a computadores, tablets y celulares."
                },
                {
                    numero: "02",
                    titulo: "Infraestructura TI",
                    descripcion: "Diseñamos y configuramos soluciones de infraestructura, redes y sistemas tecnológicos."
                },
                {
                    numero: "03",
                    titulo: "Minería de Datos",
                    descripcion: "Analizamos y procesamos datos para obtener información útil y apoyar la toma de decisiones."
                },
                {
                    numero: "04",
                    titulo: "Inteligencia Artificial",
                    descripcion: "Aplicamos fundamentos de IA y aprendizaje automático para desarrollar soluciones tecnológicas."
                }
            ];

            const inner = document.getElementById("serviciosInner");
            const indicadores = document.getElementById("serviciosIndicadores");

            servicios.forEach((servicio, index) => {
                // Item del carrusel
                let item = document.createElement("div");
                item.setAttribute("class", index === 0 ? "carousel-item active" : "carousel-item");

                let wrapper = document.createElement("div");
                wrapper.setAttribute("class", "d-flex justify-content-center");

                let card = document.createElement("div");
                card.setAttribute("class", "card border-0 shadow-sm p-4");
                card.style.maxWidth = "500px";

                let numero = document.createElement("span");
                numero.setAttribute("class", "text-primary fw-bold fs-6");
                numero.innerText = servicio.numero + " —";

                let titulo = document.createElement("h3");
                titulo.setAttribute("class", "fw-bold");
                titulo.innerText = servicio.titulo;

                let descripcion = document.createElement("p");
                descripcion.setAttribute("class", "fs-5 text-secondary");
                descripcion.innerText = servicio.descripcion;

                let link = document.createElement("a");
                link.setAttribute("href", "#");
                link.setAttribute("class", "text-primary fw-semibold text-decoration-none");
                link.innerText = "Ver más →";

                card.appendChild(numero);
                card.appendChild(titulo);
                card.appendChild(descripcion);
                card.appendChild(link);

                wrapper.appendChild(card);
                item.appendChild(wrapper);
                inner.appendChild(item);

                // Indicador (punto) correspondiente
                let punto = document.createElement("button");
                punto.setAttribute("type", "button");
                punto.setAttribute("data-bs-target", "#serviciosCarousel");
                punto.setAttribute("data-bs-slide-to", index);
                punto.style.backgroundColor = "#0d6efd";
                if (index === 0) {
                    punto.classList.add("active");
                }
                indicadores.appendChild(punto);
            });
        </script>
    </body>
</html>