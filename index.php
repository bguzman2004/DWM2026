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
                    <img src="img/logo.jpg" alt="Logo" height="100">
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

        <!-- Hero -->
        <div class="container-fluid bg-primary py-5">
            <div class="container text-center text-white py-4">
                <h1 class="fw-bold display-4">INFORMATICS</h1>
                <p class="fs-4 mb-4">Transformamos ideas en soluciones tecnológicas.</p>
                <p class="fs-5 mx-auto mb-4" style="max-width: 700px;">Somos un equipo de Ingenieros Civiles Informáticos especializados en desarrollo web, infraestructura TI, datos e inteligencia artificial.</p>
                <a href="contacto.php" class="btn btn-light btn-lg fw-semibold">Conversemos tu proyecto →</a>
            </div>
        </div>

        <!-- ¿Quiénes somos? -->
        <div class="container my-5">
            <div class="row align-items-center">
                <div class="col-md-5 text-center mb-4 mb-md-0">
                    <i class="fa fa-users" style="font-size: 140px; color:#0d6efd;"></i>
                </div>
                <div class="col-md-7">
                    <h2 class="fw-bold mb-3">¿Quiénes somos?</h2>
                    <p class="fs-5 text-secondary">En INFORMATICS combinamos ingeniería, creatividad y tecnología para desarrollar soluciones digitales que realmente resuelven problemas. Cada proyecto nace de escuchar a nuestros clientes y transformar sus necesidades en resultados concretos.</p>
                </div>
            </div>
        </div>

        <!-- Resumen de Servicios -->
        <div class="container-fluid bg-light py-5">
            <div class="container">
                <h2 class="fw-bold text-center mb-5">Lo que hacemos</h2>
                <div class="row g-4 text-center">
                    <div class="col-md-3">
                        <i class="fa fa-code fs-1 text-primary mb-3"></i>
                        <h5 class="fw-bold">Desarrollo Web</h5>
                        <p class="text-secondary">Páginas modernas, rápidas y responsivas.</p>
                    </div>
                    <div class="col-md-3">
                        <i class="fa fa-server fs-1 text-primary mb-3"></i>
                        <h5 class="fw-bold">Infraestructura TI</h5>
                        <p class="text-secondary">Redes y sistemas configurados a medida.</p>
                    </div>
                    <div class="col-md-3">
                        <i class="fa fa-bar-chart fs-1 text-primary mb-3"></i>
                        <h5 class="fw-bold">Minería de Datos</h5>
                        <p class="text-secondary">Información útil para decidir mejor.</p>
                    </div>
                    <div class="col-md-3">
                        <i class="fa fa-cogs fs-1 text-primary mb-3"></i>
                        <h5 class="fw-bold">Inteligencia Artificial</h5>
                        <p class="text-secondary">Automatización y aprendizaje aplicado.</p>
                    </div>
                </div>
                <div class="text-center mt-5">
                    <a href="servicios.php" class="btn btn-primary">Ver todos los servicios →</a>
                </div>
            </div>
        </div>

        <!-- Proyectos destacados -->
        <div class="container my-5">
            <h2 class="fw-bold text-center mb-2">Proyectos destacados</h2>
            <p class="text-secondary text-center mb-5">Algunos trabajos que hemos desarrollado.</p>
            <div class="row g-4">
                <div class="col-md-4">
                    <div class="card h-100 border-0 shadow-sm">
                        <div class="d-flex align-items-center justify-content-center bg-light" style="height: 150px;">
                            <i class="fa fa-shopping-cart" style="font-size: 60px; color:#0d6efd;"></i>
                        </div>
                        <div class="card-body">
                            <h5 class="card-title fw-bold">TiendaExpress</h5>
                            <p class="card-text text-secondary">Tienda online con carrito de compras y pasarela de pago.</p>
                        </div>
                    </div>
                </div>
                <div class="col-md-4">
                    <div class="card h-100 border-0 shadow-sm">
                        <div class="d-flex align-items-center justify-content-center bg-light" style="height: 150px;">
                            <i class="fa fa-heartbeat" style="font-size: 60px; color:#0d6efd;"></i>
                        </div>
                        <div class="card-body">
                            <h5 class="card-title fw-bold">Clínica Salud+</h5>
                            <p class="card-text text-secondary">Sistema de agendamiento de horas médicas en línea.</p>
                        </div>
                    </div>
                </div>
                <div class="col-md-4">
                    <div class="card h-100 border-0 shadow-sm">
                        <div class="d-flex align-items-center justify-content-center bg-light" style="height: 150px;">
                            <i class="fa fa-cutlery" style="font-size: 60px; color:#0d6efd;"></i>
                        </div>
                        <div class="card-body">
                            <h5 class="card-title fw-bold">RestoGourmet</h5>
                            <p class="card-text text-secondary">Reservas online con menú digital y confirmación automática.</p>
                        </div>
                    </div>
                </div>
            </div>
            <div class="text-center mt-5">
                <a href="productos.php" class="btn btn-outline-primary">Ver todos los proyectos →</a>
            </div>
        </div>

        <!-- Llamado a la acción -->
        <div class="container-fluid bg-dark py-5">
            <div class="container text-center text-white">
                <h2 class="fw-bold mb-3">¿Tienes un proyecto en mente?</h2>
                <p class="fs-5 mb-4">Cuéntanos qué necesitas y encontraremos la mejor solución tecnológica para ti.</p>
                <a href="contacto.php" class="btn btn-primary btn-lg fw-semibold">Contáctanos →</a>
            </div>
        </div>

        <!-- Footer -->
        <div class="container-fluid bg-dark border-top border-secondary">
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

