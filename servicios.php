<!DOCTYPE html>
<html lang="es">
    <head>
        <title>Servicios | El Mariachi</title>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.8/dist/css/bootstrap.min.css" rel="stylesheet">
        <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.8/dist/js/bootstrap.bundle.min.js"></script>
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/4.7.0/css/font-awesome.min.css">
        <link rel="preconnect" href="https://fonts.googleapis.com">
        <link href="https://fonts.googleapis.com/css2?family=Fraunces:wght@500;700&family=Work+Sans:wght@400;500;600&display=swap" rel="stylesheet">
        <link rel="stylesheet" href="css/mariachi.css">
    </head>
    <body>
        <nav class="navbar navbar-expand-sm navbar-mariachi">
            <div class="container-fluid">
                <a class="navbar-brand brand-logo" href="index.php">El <span>Mariachi</span></a>
                <button class="navbar-toggler" type="button" data-bs-toggle="collapse" data-bs-target="#collapsibleNavbar">
                    <span class="navbar-toggler-icon"></span>
                </button>
                <div class="collapse navbar-collapse" id="collapsibleNavbar">
                    <ul class="navbar-nav me-auto">
                        <li class="nav-item"><a class="nav-link" href="index.php">Inicio</a></li>
                        <li class="nav-item"><a class="nav-link" href="empresa.php">Nosotros</a></li>
                        <li class="nav-item"><a class="nav-link active" href="servicios.php">Servicios</a></li>
                        <li class="nav-item"><a class="nav-link" href="productos.php">Menú</a></li>
                        <li class="nav-item"><a class="nav-link" href="contacto.php">Contacto</a></li>
                    </ul>
                </div>
                <a href="https://wa.me/56900000000" class="btn btn-mariachi" target="_blank" rel="noopener">
                    <i class="fa fa-whatsapp"></i> Pedir ahora
                </a>
            </div>
        </nav>

        <div class="page-header text-center">
            <div class="container">
                <h1 class="fw-bold">Servicios</h1>
                <p class="mb-0">Más formas de disfrutar El Mariachi</p>
            </div>
        </div>

        <div class="container my-5">
            <div class="row g-4">
                <div class="col-12 col-md-4">
                    <div class="card-mariachi card-tacos text-center h-100">
                        <div class="icono mx-auto"><i class="fa fa-motorcycle"></i></div>
                        <h3 class="h5 fw-bold">Delivery</h3>
                        <p class="text-secondary">Despacho a domicilio en un radio de 5 km. Pide por WhatsApp y te avisamos el tiempo estimado.</p>
                        <a href="https://wa.me/56900000000" class="btn btn-outline-mariachi btn-sm" target="_blank" rel="noopener">Pedir delivery</a>
                    </div>
                </div>
                <div class="col-12 col-md-4">
                    <div class="card-mariachi card-burritos text-center h-100">
                        <div class="icono mx-auto"><i class="fa fa-cutlery"></i></div>
                        <h3 class="h5 fw-bold">Reservas</h3>
                        <p class="text-secondary">Mesas para grupos de hasta 12 personas. Reserva con anticipación los fines de semana.</p>
                        <a href="contacto.php" class="btn btn-outline-mariachi btn-sm">Reservar mesa</a>
                    </div>
                </div>
                <div class="col-12 col-md-4">
                    <div class="card-mariachi card-bebidas text-center h-100">
                        <div class="icono mx-auto"><i class="fa fa-users"></i></div>
                        <h3 class="h5 fw-bold">Eventos y catering</h3>
                        <p class="text-secondary">Llevamos El Mariachi a tu cumpleaños, oficina o evento. Menús desde 10 personas.</p>
                        <a href="contacto.php" class="btn btn-outline-mariachi btn-sm">Cotizar evento</a>
                    </div>
                </div>
            </div>
        </div>

        <div class="promo-banda text-center">
            <div class="container">
                <strong>Eventos corporativos</strong> — 10% de descuento reservando con 1 semana de anticipación.
            </div>
        </div>

        <footer class="footer-mariachi">
            <div class="container">
                <div class="row g-4">
                    <div class="col-12 col-md-4">
                        <div class="brand-logo h5 mb-2">El <span>Mariachi</span></div>
                        <p class="small mb-0">Comida mexicana casera, hecha al momento.</p>
                    </div>
                    <div class="col-12 col-md-4">
                        <div class="fw-bold mb-2">Síguenos</div>
                        <a href="#" class="me-3"><i class="fa fa-facebook fa-lg"></i></a>
                        <a href="#" class="me-3"><i class="fa fa-instagram fa-lg"></i></a>
                        <a href="https://wa.me/56900000000" target="_blank" rel="noopener"><i class="fa fa-whatsapp fa-lg"></i></a>
                    </div>
                    <div class="col-12 col-md-4">
                        <div class="fw-bold mb-2">Horario</div>
                        <p class="small mb-0">Mar–Dom, 12:00–22:00<br>Lunes cerrado</p>
                    </div>
                </div>
                <hr>
                <p class="small text-center mb-0">&copy; 2026 El Mariachi — Creado por M.CAÑETE × B.GZMN</p>
            </div>
        </footer>

        <a href="https://wa.me/56900000000" class="wsp-flotante" target="_blank" rel="noopener">
            <i class="fa fa-whatsapp"></i> Escríbenos
        </a>
    </body>
</html>
