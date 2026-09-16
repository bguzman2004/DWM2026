<!DOCTYPE html>
<html lang="es">
    <head>
        <title>El Mariachi | Comida Mexicana</title>
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
        <!-- Navbar -->
        <nav class="navbar navbar-expand-sm navbar-mariachi">
            <div class="container-fluid">
                <a class="navbar-brand brand-logo" href="index.php">El <span>Mariachi</span></a>
                <button class="navbar-toggler" type="button" data-bs-toggle="collapse" data-bs-target="#collapsibleNavbar">
                    <span class="navbar-toggler-icon"></span>
                </button>
                <div class="collapse navbar-collapse" id="collapsibleNavbar">
                    <ul class="navbar-nav me-auto">
                        <li class="nav-item"><a class="nav-link active" href="index.php">Inicio</a></li>
                        <li class="nav-item"><a class="nav-link" href="empresa.php">Nosotros</a></li>
                        <li class="nav-item"><a class="nav-link" href="servicios.php">Servicios</a></li>
                        <li class="nav-item"><a class="nav-link" href="productos.php">Menú</a></li>
                        <li class="nav-item"><a class="nav-link" href="contacto.php">Contacto</a></li>
                    </ul>
                </div>
                <a href="https://wa.me/56900000000" class="btn btn-mariachi" target="_blank" rel="noopener">
                    <i class="fa fa-whatsapp"></i> Pedir ahora
                </a>
            </div>
        </nav>

        <!-- Hero -->
        <div class="hero-mariachi py-5">
            <div class="container text-center py-4">
                <h1 class="fw-bold">Sabor auténtico de México, directo a tu mesa</h1>
                <p class="lead mx-auto mb-4" style="max-width:640px;">Tacos, burritos y antojitos preparados al momento, con recetas de familia. Pide online o ven a visitarnos.</p>
                <a href="productos.php" class="btn btn-mariachi btn-lg me-2">Ver menú</a>
                <a href="https://wa.me/56900000000" class="btn btn-outline-mariachi btn-lg" style="color:#F4E9DA;border-color:#F4E9DA;" target="_blank" rel="noopener">Pedir por WhatsApp</a>
            </div>
        </div>

        <!-- Categorías -->
        <div class="container my-5">
            <h2 class="text-center fw-bold mb-2">Nuestras categorías</h2>
            <p class="text-center text-secondary mb-5">Elige y arma tu pedido</p>
            <div class="row g-4">
                <div class="col-12 col-md-4">
                    <div class="card-mariachi card-tacos text-center">
                        <div class="icono mx-auto"><i class="fa fa-cutlery"></i></div>
                        <h3 class="h5 fw-bold">Tacos</h3>
                        <p class="text-secondary mb-3">Al pastor, carnitas, birria y vegetarianos.</p>
                        <a href="productos.php#tacos" class="btn btn-outline-mariachi btn-sm">Ver tacos</a>
                    </div>
                </div>
                <div class="col-12 col-md-4">
                    <div class="card-mariachi card-burritos text-center">
                        <div class="icono mx-auto"><i class="fa fa-cutlery"></i></div>
                        <h3 class="h5 fw-bold">Burritos</h3>
                        <p class="text-secondary mb-3">Bien cargados, a tu elección de relleno.</p>
                        <a href="productos.php#burritos" class="btn btn-outline-mariachi btn-sm">Ver burritos</a>
                    </div>
                </div>
                <div class="col-12 col-md-4">
                    <div class="card-mariachi card-bebidas text-center">
                        <div class="icono mx-auto"><i class="fa fa-glass"></i></div>
                        <h3 class="h5 fw-bold">Bebidas</h3>
                        <p class="text-secondary mb-3">Aguas frescas, horchata y refrescos.</p>
                        <a href="productos.php#bebidas" class="btn btn-outline-mariachi btn-sm">Ver bebidas</a>
                    </div>
                </div>
            </div>
        </div>

        <!-- Promo -->
        <div class="promo-banda text-center">
            <div class="container">
                <strong>2x1 en Tacos</strong> — todos los martes, para pedidos por WhatsApp.
            </div>
        </div>

        <!-- Nosotros + Reseñas -->
        <div class="container my-5">
            <div class="row g-4">
                <div class="col-12 col-md-6">
                    <h2 class="h4 fw-bold">Sobre nosotros</h2>
                    <p class="text-secondary">El Mariachi nació de una receta familiar y de las ganas de compartir la comida mexicana de verdad en Chile. Cada platillo se prepara al momento, con ingredientes frescos y las salsas hechas en casa.</p>
                    <a href="empresa.php" class="btn btn-outline-mariachi btn-sm">Conócenos</a>
                </div>
                <div class="col-12 col-md-6">
                    <h2 class="h4 fw-bold">Lo que dicen nuestros clientes</h2>
                    <div class="mb-3">
                        <div class="text-warning mb-1"><i class="fa fa-star"></i><i class="fa fa-star"></i><i class="fa fa-star"></i><i class="fa fa-star"></i><i class="fa fa-star"></i></div>
                        <p class="text-secondary fst-italic mb-0">"Los tacos al pastor son iguales a los de México. Pedimos casi todas las semanas."</p>
                    </div>
                    <div>
                        <div class="text-warning mb-1"><i class="fa fa-star"></i><i class="fa fa-star"></i><i class="fa fa-star"></i><i class="fa fa-star"></i><i class="fa fa-star"></i></div>
                        <p class="text-secondary fst-italic mb-0">"Rapidísimo el delivery y todo llega calientito."</p>
                    </div>
                </div>
            </div>
        </div>

        <!-- Footer -->
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
