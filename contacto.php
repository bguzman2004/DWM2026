<!DOCTYPE html>
<html lang="es">
    <head>
        <title>Contacto | El Mariachi</title>
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
                        <li class="nav-item"><a class="nav-link" href="servicios.php">Servicios</a></li>
                        <li class="nav-item"><a class="nav-link" href="productos.php">Menú</a></li>
                        <li class="nav-item"><a class="nav-link active" href="contacto.php">Contacto</a></li>
                    </ul>
                </div>
                <a href="https://wa.me/56900000000" class="btn btn-mariachi" target="_blank" rel="noopener">
                    <i class="fa fa-whatsapp"></i> Pedir ahora
                </a>
            </div>
        </nav>

        <div class="page-header text-center">
            <div class="container">
                <h1 class="fw-bold">Contacto</h1>
                <p class="mb-0">Escríbenos, reserva tu mesa o cotiza tu evento</p>
            </div>
        </div>

        <div class="container my-5">
            <div class="row g-5">
                <div class="col-12 col-md-6">
                    <h2 class="h5 fw-bold mb-3">Envíanos un mensaje</h2>
                    <form action="#" method="post">
                        <div class="mb-3">
                            <label for="nombre" class="form-label">Nombre</label>
                            <input type="text" class="form-control" id="nombre" name="nombre" placeholder="Tu nombre" required>
                        </div>
                        <div class="mb-3">
                            <label for="email" class="form-label">Correo</label>
                            <input type="email" class="form-control" id="email" name="email" placeholder="tu@correo.com" required>
                        </div>
                        <div class="mb-3">
                            <label for="telefono" class="form-label">Teléfono (opcional)</label>
                            <input type="tel" class="form-control" id="telefono" name="telefono" placeholder="+56 9 1234 5678">
                        </div>
                        <div class="mb-3">
                            <label for="mensaje" class="form-label">Mensaje</label>
                            <textarea class="form-control" id="mensaje" name="mensaje" rows="4" placeholder="Cuéntanos qué necesitas: reserva, evento, o alguna consulta" required></textarea>
                        </div>
                        <button type="submit" class="btn btn-mariachi">Enviar mensaje</button>
                    </form>
                </div>

                <div class="col-12 col-md-6">
                    <h2 class="h5 fw-bold mb-3">Encuéntranos</h2>
                    <div class="mapa-placeholder mb-3">
                        <span><i class="fa fa-map-marker fa-2x d-block mb-2"></i>Mapa — Av. Ejemplo 123, Santiago</span>
                    </div>
                    <ul class="list-unstyled">
                        <li class="mb-2"><i class="fa fa-map-marker me-2" style="color:var(--rojo)"></i>Av. Ejemplo 123, Santiago</li>
                        <li class="mb-2"><i class="fa fa-phone me-2" style="color:var(--rojo)"></i>+56 9 0000 0000</li>
                        <li class="mb-2"><i class="fa fa-envelope me-2" style="color:var(--rojo)"></i>contacto@elmariachi.cl</li>
                        <li class="mb-2"><i class="fa fa-clock-o me-2" style="color:var(--rojo)"></i>Mar–Dom, 12:00–22:00 (lunes cerrado)</li>
                    </ul>
                    <a href="https://wa.me/56900000000" class="btn btn-outline-mariachi" target="_blank" rel="noopener">
                        <i class="fa fa-whatsapp"></i> Escríbenos por WhatsApp
                    </a>
                </div>
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
