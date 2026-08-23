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

        <!-- Hero Empresa -->
        <div class="container-fluid bg-light py-5">
            <div class="container text-center">
                <h1 class="fw-bold display-5">NUESTRA EMPRESA</h1>
                <p class="fs-4 text-secondary mb-0">Conoce quiénes somos y qué nos mueve.</p>
            </div>
        </div>

        <!-- Historia -->
        <div class="container my-5">
            <div class="row align-items-center">
                <div class="col-md-5 text-center mb-4 mb-md-0">
                    <i class="fa fa-building" style="font-size: 140px; color:#0d6efd;"></i>
                </div>
                <div class="col-md-7">
                    <h2 class="fw-bold mb-3">Nuestra Historia</h2>
                    <p class="fs-5 text-secondary">INFORMATICS nació de la idea de acercar la tecnología a cualquier persona o negocio, sin importar su tamaño. Desde entonces, hemos trabajado en proyectos de desarrollo web, infraestructura y datos, siempre buscando soluciones simples para problemas complejos.</p>
                </div>
            </div>
        </div>

        <!-- Misión y Visión -->
        <div class="container-fluid bg-light py-5">
            <div class="container">
                <div class="row g-4 text-center">
                    <div class="col-md-6">
                        <i class="fa fa-bullseye fs-1 text-primary mb-3"></i>
                        <h4 class="fw-bold">Misión</h4>
                        <p class="text-secondary">Entregar soluciones tecnológicas de calidad que impulsen el crecimiento de nuestros clientes.</p>
                    </div>
                    <div class="col-md-6">
                        <i class="fa fa-eye fs-1 text-primary mb-3"></i>
                        <h4 class="fw-bold">Visión</h4>
                        <p class="text-secondary">Ser referentes en desarrollo de software e innovación tecnológica en Latinoamérica.</p>
                    </div>
                </div>
            </div>
        </div>

        <!-- Nuestro Equipo -->
        <div class="container my-5">
            <h2 class="fw-bold text-center mb-2">Nuestro Equipo</h2>
            <p class="text-secondary text-center mb-5">Las personas detrás de INFORMATICS.</p>
            <!-- Las tarjetas del equipo se generan dinámicamente con JavaScript, ver script al final -->
            <div class="row g-4" id="contenedorEquipo"></div>
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
                                <input type="email" class="form-control" id="email" placeholder="Ingresar Correo " name="email">
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
                            <button type="submit" class="btn btn-primary">Ingresar <i class="fa fa-check-circle"></i></button>
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
            const equipo = [
                { nombre: "Matías Cañete", cargo: "Full Stack Developer", icono: "fa-user" },
                { nombre: "Benjamín Guzmán", cargo: "Backend Developer", icono: "fa-user" },
                { nombre: "Camila Rojas", cargo: "Diseñadora UX/UI", icono: "fa-user" },
                { nombre: "Diego Fuentes", cargo: "Analista de Datos", icono: "fa-user" }
            ];

            const contenedorEquipo = document.getElementById("contenedorEquipo");

            equipo.forEach((persona) => {
                let col = document.createElement("div");
                col.setAttribute("class", "col-md-6 col-lg-3");

                let card = document.createElement("div");
                card.setAttribute("class", "card h-100 border-0 shadow-sm text-center p-4");

                let icono = document.createElement("i");
                icono.setAttribute("class", "fa " + persona.icono);
                icono.style.fontSize = "70px";
                icono.style.color = "#0d6efd";

                let nombre = document.createElement("h5");
                nombre.setAttribute("class", "fw-bold mt-3");
                nombre.innerText = persona.nombre;

                let cargo = document.createElement("p");
                cargo.setAttribute("class", "text-secondary mb-0");
                cargo.innerText = persona.cargo;

                card.appendChild(icono);
                card.appendChild(nombre);
                card.appendChild(cargo);
                col.appendChild(card);

                contenedorEquipo.appendChild(col);
            });
        </script>
    </body>
</html>