<!DOCTYPE html>
<html lang="es">
    <head>
        <title>Menú | El Mariachi</title>
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
                        <li class="nav-item"><a class="nav-link active" href="productos.php">Menú</a></li>
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
                <h1 class="fw-bold">Nuestro menú</h1>
                <p class="mb-0">Todo preparado al momento de tu pedido</p>
            </div>
        </div>

        <div class="container my-5">
            <!-- Pestañas de categoría -->
            <ul class="nav nav-tabs nav-tabs-mariachi justify-content-center mb-4" id="menuTabs" role="tablist">
                <li class="nav-item" role="presentation">
                    <button class="nav-link active" id="tab-tacos-btn" data-bs-toggle="tab" data-bs-target="#tacos" type="button">Tacos</button>
                </li>
                <li class="nav-item" role="presentation">
                    <button class="nav-link" id="tab-burritos-btn" data-bs-toggle="tab" data-bs-target="#burritos" type="button">Burritos</button>
                </li>
                <li class="nav-item" role="presentation">
                    <button class="nav-link" id="tab-nachos-btn" data-bs-toggle="tab" data-bs-target="#nachos" type="button">Nachos</button>
                </li>
                <li class="nav-item" role="presentation">
                    <button class="nav-link" id="tab-bebidas-btn" data-bs-toggle="tab" data-bs-target="#bebidas" type="button">Bebidas</button>
                </li>
            </ul>

            <div class="tab-content">
                <div class="tab-pane fade show active" id="tacos" role="tabpanel">
                    <div class="row g-3">
                        <div class="col-12 col-md-6">
                            <div class="platillo-card d-flex justify-content-between align-items-start">
                                <div><h3 class="h6 fw-bold mb-1">Taco al pastor</h3><p class="text-secondary small mb-0">Cerdo marinado, piña, cebolla y cilantro.</p></div>
                                <span class="precio">$2.500</span>
                            </div>
                        </div>
                        <div class="col-12 col-md-6">
                            <div class="platillo-card d-flex justify-content-between align-items-start">
                                <div><h3 class="h6 fw-bold mb-1">Taco de carnitas</h3><p class="text-secondary small mb-0">Cerdo cocido lento, salsa verde.</p></div>
                                <span class="precio">$2.500</span>
                            </div>
                        </div>
                        <div class="col-12 col-md-6">
                            <div class="platillo-card d-flex justify-content-between align-items-start">
                                <div><h3 class="h6 fw-bold mb-1">Taco de birria</h3><p class="text-secondary small mb-0">Res braseada, consomé para remojar.</p></div>
                                <span class="precio">$3.000</span>
                            </div>
                        </div>
                        <div class="col-12 col-md-6">
                            <div class="platillo-card d-flex justify-content-between align-items-start">
                                <div><h3 class="h6 fw-bold mb-1">Taco vegetariano</h3><p class="text-secondary small mb-0">Frijoles, queso, pico de gallo, guacamole.</p></div>
                                <span class="precio">$2.200</span>
                            </div>
                        </div>
                    </div>
                </div>

                <div class="tab-pane fade" id="burritos" role="tabpanel">
                    <div class="row g-3">
                        <div class="col-12 col-md-6">
                            <div class="platillo-card d-flex justify-content-between align-items-start">
                                <div><h3 class="h6 fw-bold mb-1">Burrito de pollo</h3><p class="text-secondary small mb-0">Arroz, frijoles, pollo asado, queso y salsa.</p></div>
                                <span class="precio">$5.500</span>
                            </div>
                        </div>
                        <div class="col-12 col-md-6">
                            <div class="platillo-card d-flex justify-content-between align-items-start">
                                <div><h3 class="h6 fw-bold mb-1">Burrito de carne asada</h3><p class="text-secondary small mb-0">Res a la parrilla, pico de gallo, guacamole.</p></div>
                                <span class="precio">$6.000</span>
                            </div>
                        </div>
                        <div class="col-12 col-md-6">
                            <div class="platillo-card d-flex justify-content-between align-items-start">
                                <div><h3 class="h6 fw-bold mb-1">Burrito vegetariano</h3><p class="text-secondary small mb-0">Frijoles, arroz, verduras salteadas, queso.</p></div>
                                <span class="precio">$5.000</span>
                            </div>
                        </div>
                    </div>
                </div>

                <div class="tab-pane fade" id="nachos" role="tabpanel">
                    <div class="row g-3">
                        <div class="col-12 col-md-6">
                            <div class="platillo-card d-flex justify-content-between align-items-start">
                                <div><h3 class="h6 fw-bold mb-1">Nachos clásicos</h3><p class="text-secondary small mb-0">Queso derretido, jalapeños, pico de gallo.</p></div>
                                <span class="precio">$4.500</span>
                            </div>
                        </div>
                        <div class="col-12 col-md-6">
                            <div class="platillo-card d-flex justify-content-between align-items-start">
                                <div><h3 class="h6 fw-bold mb-1">Nachos con carne</h3><p class="text-secondary small mb-0">Carne molida sazonada, queso, guacamole.</p></div>
                                <span class="precio">$5.500</span>
                            </div>
                        </div>
                    </div>
                </div>

                <div class="tab-pane fade" id="bebidas" role="tabpanel">
                    <div class="row g-3">
                        <div class="col-12 col-md-6">
                            <div class="platillo-card d-flex justify-content-between align-items-start">
                                <div><h3 class="h6 fw-bold mb-1">Agua de horchata</h3><p class="text-secondary small mb-0">Arroz, canela y vainilla.</p></div>
                                <span class="precio">$1.800</span>
                            </div>
                        </div>
                        <div class="col-12 col-md-6">
                            <div class="platillo-card d-flex justify-content-between align-items-start">
                                <div><h3 class="h6 fw-bold mb-1">Agua de jamaica</h3><p class="text-secondary small mb-0">Flor de jamaica, refrescante y natural.</p></div>
                                <span class="precio">$1.800</span>
                            </div>
                        </div>
                    </div>
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

        <script>
            // Si llegamos con un #hash (ej. productos.php#burritos desde index.php),
            // activa esa pestaña del menú en vez de dejar siempre "Tacos" seleccionada.
            document.addEventListener("DOMContentLoaded", function () {
                const hash = window.location.hash;
                if (hash) {
                    const boton = document.querySelector('#menuTabs button[data-bs-target="' + hash + '"]');
                    if (boton) {
                        new bootstrap.Tab(boton).show();
                    }
                }
            });
        </script>
    </body>
</html>
