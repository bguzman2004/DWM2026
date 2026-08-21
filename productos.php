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

        <!-- Container -->
        <div class="container-fluid bg-warning py-4">
            <div class="container">
                <div id="demo" class="carousel slide mx-auto" data-bs-ride="carousel" style="max-width: 600px;">

                <!-- Indicators/dots -->
                <div class="carousel-indicators">
                    <button type="button" data-bs-target="#demo" data-bs-slide-to="0" class="active"></button>
                    <button type="button" data-bs-target="#demo" data-bs-slide-to="1"></button>
                    <button type="button" data-bs-target="#demo" data-bs-slide-to="2"></button>
                </div>

                <!-- The slideshow/carousel -->
                <div class="carousel-inner rounded shadow-sm">
                    <div class="carousel-item active">
                    <img src="img/equipo.jpeg" alt="Nuestro Equipo" class="d-block w-100" style="height: 280px; object-fit: cover;">
                    </div>
                    <div class="carousel-item">
                    <img src="img/mano.jpeg" alt="Mano" class="d-block w-100" style="height: 280px; object-fit: cover;">
                    </div>
                    <div class="carousel-item">
                    <img src="img/tablet.jpeg" alt="New York" class="d-block w-100" style="height: 280px; object-fit: cover;">
                    </div>
                </div>

                <!-- Left and right controls/icons -->
                <button class="carousel-control-prev" type="button" data-bs-target="#demo" data-bs-slide="prev">
                    <span class="carousel-control-prev-icon"></span>
                </button>
                <button class="carousel-control-next" type="button" data-bs-target="#demo" data-bs-slide="next">
                    <span class="carousel-control-next-icon"></span>
                </button>
                </div>
            </div>
        </div>

        <!-- Nuestros Trabajos -->
        <div class="container my-5">
            <h2 class="fw-bold text-center mb-2">Nuestros Trabajos</h2>
            <p class="text-secondary text-center mb-5">Algunas de las páginas web que hemos desarrollado para nuestros clientes.</p>

            <div class="row g-4">

                <div class="col-md-6 col-lg-3">
                    <div class="card h-100 border-0 shadow-sm">
                        <div class="d-flex align-items-center justify-content-center bg-light" style="height: 150px;">
                            <i class="fa fa-shopping-cart" style="font-size: 60px; color:#0d6efd;"></i>
                        </div>
                        <div class="card-body">
                            <h5 class="card-title fw-bold">TiendaExpress</h5>
                            <p class="card-text text-secondary">Tienda online de venta de artículos electrónicos con carrito de compras y pasarela de pago.</p>
                            <div class="d-flex flex-wrap gap-1">
                                <span class="badge bg-primary">HTML</span>
                                <span class="badge bg-primary">CSS</span>
                                <span class="badge bg-primary">PHP</span>
                                <span class="badge bg-primary">MySQL</span>
                            </div>
                        </div>
                    </div>
                </div>

                <div class="col-md-6 col-lg-3">
                    <div class="card h-100 border-0 shadow-sm">
                        <div class="d-flex align-items-center justify-content-center bg-light" style="height: 150px;">
                            <i class="fa fa-heartbeat" style="font-size: 60px; color:#0d6efd;"></i>
                        </div>
                        <div class="card-body">
                            <h5 class="card-title fw-bold">Clínica Salud+</h5>
                            <p class="card-text text-secondary">Sistema de agendamiento de horas médicas en línea con panel para pacientes y doctores.</p>
                            <div class="d-flex flex-wrap gap-1">
                                <span class="badge bg-primary">PHP</span>
                                <span class="badge bg-primary">Bootstrap</span>
                                <span class="badge bg-primary">MySQL</span>
                            </div>
                        </div>
                    </div>
                </div>

                <div class="col-md-6 col-lg-3">
                    <div class="card h-100 border-0 shadow-sm">
                        <div class="d-flex align-items-center justify-content-center bg-light" style="height: 150px;">
                            <i class="fa fa-cutlery" style="font-size: 60px; color:#0d6efd;"></i>
                        </div>
                        <div class="card-body">
                            <h5 class="card-title fw-bold">RestoGourmet</h5>
                            <p class="card-text text-secondary">Sitio de reservas online para restaurante con menú digital y confirmación automática.</p>
                            <div class="d-flex flex-wrap gap-1">
                                <span class="badge bg-primary">JavaScript</span>
                                <span class="badge bg-primary">Node.js</span>
                                <span class="badge bg-primary">MongoDB</span>
                            </div>
                        </div>
                    </div>
                </div>

                <div class="col-md-6 col-lg-3">
                    <div class="card h-100 border-0 shadow-sm">
                        <div class="d-flex align-items-center justify-content-center bg-light" style="height: 150px;">
                            <i class="fa fa-graduation-cap" style="font-size: 60px; color:#0d6efd;"></i>
                        </div>
                        <div class="card-body">
                            <h5 class="card-title fw-bold">EduOnline</h5>
                            <p class="card-text text-secondary">Plataforma de cursos virtuales con seguimiento de progreso y certificados descargables.</p>
                            <div class="d-flex flex-wrap gap-1">
                                <span class="badge bg-primary">React</span>
                                <span class="badge bg-primary">Firebase</span>
                            </div>
                        </div>
                    </div>
                </div>

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
    </body>
</html>