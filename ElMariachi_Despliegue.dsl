workspace "El Mariachi" "Plataforma de pedidos del restaurante El Mariachi (DWM2026)" {

    !identifiers hierarchical

    model {
        visitante = person "Visitante" "Persona que consulta el menú y la promoción del día sin iniciar sesión."
        cliente = person "Cliente" "Persona autenticada que arma pedidos, los paga y revisa su historial."
        cocina = person "Personal de cocina" "Prepara los pedidos pagados y controla las existencias."
        administrador = person "Administrador" "Dueño del local: gestiona carta, stock, promociones, clientes y ventas."

        proveedorPago = softwareSystem "Proveedor de pagos" "Procesa los cobros (Flow, Transbank u otro). En esta entrega es un adaptador simulado con el mismo contrato." {
            tags "SistemaExterno"
        }

        sistema = softwareSystem "Plataforma El Mariachi" "Sistema de pedidos del restaurante: menú, pedidos, pagos, cocina y ventas." {
            tags "SistemaEvaluado"

            frontend = container "Frontend responsivo" "Interfaz web de la Evaluación 1: Inicio, Menú, Detalle, Pedido, Confirmación, Nosotros y Contacto." "HTML, CSS, JavaScript, Bootstrap" {
                tags "Frontend"
            }

            apiGateway = container "API Gateway" "Única puerta pública: enruta solicitudes y aplica sesión, roles, límites de tasa y tamaño." "Python, FastAPI" {
                tags "Gateway"

                adaptadorHttp = component "Adaptador HTTP" "Recibe solicitudes y arma respuestas HTTP; asigna un X-Request-Id nuevo a cada solicitud." "FastAPI" {
                    tags "EntradaC3"
                }
                limitador = component "Limitador de solicitudes" "Límite de tasa por IP, cuerpo de hasta 64 KiB y solo JSON." "RateLimiter" {
                    tags "ControlC3"
                }
                tablaRutas = component "Tabla de rutas" "Lista explícita de rutas, verbos, acceso y roles; lo no listado responde 404 o 405." "routes.py" {
                    tags "ControlC3"
                }
                filtroAcceso = component "Filtro de acceso" "Distingue rutas públicas, valida la sesión con Auth, exige roles y descarta las cabeceras de identidad del navegador." "authenticate" {
                    tags "ControlC3"
                }
                despachador = component "Despachador de rutas" "Reenvía la solicitud al servicio privado con la identidad verificada y el secreto de la integración." "ServiceClient, httpx" {
                    tags "AplicacionC3"
                }
                clienteSecretos = component "Cliente de secretos" "Lee y guarda por 30 segundos los secretos de cada integración del gateway." "SecretProvider" {
                    tags "IntegracionC3"
                }
                traductorErrores = component "Traductor de errores" "Convierte fallos en {status, message, request_id} sin revelar detalles internos." "Manejadores de excepciones" {
                    tags "ErrorC3"
                }
            }

            authService = container "Auth Service" "Registra usuarios, inicia, valida y revoca sesiones." "Python, FastAPI" {
                tags "Seguridad"

                apiIdentidad = component "API de identidad" "Atiende /login, /register, /introspect y /logout; solo acepta llamadas del API Gateway." "FastAPI" {
                    tags "EntradaC3"
                }
                verificador = component "Verificador de credenciales" "Compara la clave con su hash scrypt en tiempo constante y bloquea tras 5 intentos fallidos." "scrypt" {
                    tags "ControlC3"
                }
                gestorSesiones = component "Gestor de sesiones" "Emite tokens opacos de 15 minutos, guarda solo su hash, controla vigencia y revoca." "secrets, hashlib" {
                    tags "AplicacionC3"
                }
                registro = component "Registro de usuarios" "Crea el usuario pendiente, pide el perfil a clients y lo activa; si falla, lo elimina." "Saga con compensación" {
                    tags "AplicacionC3"
                }
                repoIdentidad = component "Repositorio de identidades" "Acceso a usuarios, sesiones e intentos fallidos." "SQL" {
                    tags "PersistenciaC3"
                }
                conectorClientes = component "Conector de clientes" "Pide a clients crear el perfil del nuevo cliente." "ServiceClient, httpx" {
                    tags "IntegracionC3"
                }
                clienteSecretos = component "Cliente de secretos" "Obtiene de forma controlada los secretos de Auth." "SecretProvider" {
                    tags "IntegracionC3"
                }
            }

            secretManager = container "Administrador de secretos" "Guarda un secreto por integración y el secreto del webhook; cada servicio tiene un token con permisos mínimos." "HashiCorp Vault" {
                tags "Seguridad"
            }

            inventory = container "inventory" "Gestiona el menú de 12 platillos, la promoción 2x1, las existencias y las reservas de stock." "Python, FastAPI" {
                tags "Privado"
            }

            orders = container "orders" "Gestiona el ciclo de vida de los pedidos y sus cambios de estado." "Python, FastAPI" {
                tags "Privado"

                apiPedidos = component "API de pedidos" "Recibe solicitudes de los gateways y llamadas internas de payments y analytics." "FastAPI" {
                    tags "EntradaC3"
                }
                politicaAcceso = component "Política de acceso a pedidos" "Un cliente ve solo sus pedidos (otro responde 404); cocina ve pagados y en preparación; admin ve todos." "require_user, require_roles" {
                    tags "ControlC3"
                }
                idempotencia = component "Control de idempotencia" "Detecta reintentos con la misma Idempotency-Key y devuelve el mismo pedido." "Tabla idempotency" {
                    tags "ControlC3"
                }
                servicioPedidos = component "Servicio de pedidos" "Coordina reglas, total calculado en el servidor, transiciones de estado, expiración y recuperación de stock." "main.py" {
                    tags "AplicacionC3"
                }
                adaptadorInventario = component "Adaptador de inventario" "Reserva, libera y confirma stock; recibe precios y descuento 2x1." "ServiceClient, httpx" {
                    tags "IntegracionC3"
                }
                adaptadorClientes = component "Adaptador de clientes" "Verifica que el cliente del pedido exista." "ServiceClient, httpx" {
                    tags "IntegracionC3"
                }
                clienteSecretos = component "Cliente de secretos" "Obtiene los secretos de las integraciones de orders." "SecretProvider" {
                    tags "IntegracionC3"
                }
                repoPedidos = component "Repositorio de pedidos" "Pedidos, detalle con precio y descuento copiados, eventos y claves de idempotencia." "SQL" {
                    tags "PersistenciaC3"
                }
                traductorErrores = component "Traductor de errores" "Responde los errores con el formato común y el request_id." "Manejadores de excepciones" {
                    tags "ErrorC3"
                }
            }

            clients = container "clients" "Gestiona perfiles y datos de contacto de los clientes." "Python, FastAPI" {
                tags "Privado"
            }

            payments = container "payments" "Gestiona los estados de pago y la coordinación de cobros con el proveedor." "Python, FastAPI" {
                tags "Privado"

                apiPagos = component "API de pagos" "POST /payments, consultas, /payments/webhook y /payments/reconcile." "FastAPI" {
                    tags "EntradaC3"
                }
                verificadorFirma = component "Verificador de firma" "Calcula HMAC-SHA256 sobre el cuerpo recibido y lo compara con X-Signature." "hmac" {
                    tags "ControlC3"
                }
                controlDuplicados = component "Control de idempotencia y duplicados" "Idempotency-Key por cliente al iniciar un pago y event_id único por aviso del proveedor." "Restricciones UNIQUE" {
                    tags "ControlC3"
                }
                servicioPagos = component "Servicio de pagos" "Crea o reutiliza el pago, toma el monto desde orders, valida el aviso y concilia." "main.py" {
                    tags "AplicacionC3"
                }
                adaptadorProveedor = component "Adaptador del proveedor" "Solicita el cobro al proveedor de pagos." "Adaptador simulado" {
                    tags "IntegracionC3"
                }
                adaptadorPedidos = component "Adaptador de pedidos" "Lee el pedido y su total, y lo marca pagado." "ServiceClient, httpx" {
                    tags "IntegracionC3"
                }
                clienteSecretos = component "Cliente de secretos" "Obtiene el secreto HMAC y el de la integración con orders." "SecretProvider" {
                    tags "IntegracionC3"
                }
                repoPagos = component "Repositorio de pagos" "Pagos, claves de idempotencia y avisos recibidos." "SQL" {
                    tags "PersistenciaC3"
                }
            }

            analytics = container "analytics" "Proyección de ventas pagadas, sin datos personales; entrega resúmenes y exportación masiva." "Python, gRPC" {
                tags "Privado" "Analitica"
            }

            graphqlGateway = container "GraphQL Gateway" "Expone una API de consulta y agrega información de los subsistemas autorizados." "Python, Strawberry GraphQL" {
                tags "Gateway"

                endpoint = component "Endpoint GraphQL" "Recibe POST /graphql desde el API Gateway; no acepta GET ni lotes de operaciones." "GraphQLRouter" {
                    tags "EntradaC3"
                }
                validador = component "Validador de consultas" "Comprueba el esquema, introspección apagada, profundidad máxima 6 y costo máximo 5000." "limits.py" {
                    tags "ControlC3"
                }
                politicas = component "Política de acceso a campos" "Permisos por campo según rol y dueño: IsStaff, IsAdmin, OwnerOrAdmin y CanPay." "Permission classes" {
                    tags "ControlC3"
                }
                resolvers = component "Resolvers de negocio" "Resuelven me, products, myOrders, order, salesSummary, createOrder y syncAnalytics." "schema.py" {
                    tags "AplicacionC3"
                }
                dataloaders = component "DataLoaders" "Agrupan las lecturas en un lote por tipo de dato para evitar consultas N+1." "Strawberry DataLoader" {
                    tags "AplicacionC3"
                }
                conectores = component "Conectores de subsistemas" "Llaman a inventory, orders, clients y payments con el secreto de cada integración." "ServiceClient, httpx" {
                    tags "IntegracionC3"
                }
                clienteAnalytics = component "Cliente gRPC de analítica" "Pide resúmenes y sincronizaciones de ventas con plazos de 5 y 30 segundos." "grpc.aio" {
                    tags "IntegracionC3"
                }
                compositor = component "Compositor de respuestas" "Arma data y errores parciales por campo; enmascara los errores inesperados." "MaskErrors" {
                    tags "ErrorC3"
                }
            }

            dbInventory = container "Datos de inventario" "Persistencia del subsistema inventory." "SQLite" {
                tags "BaseDatos"
            }
            dbOrders = container "Datos de pedidos" "Persistencia del subsistema orders." "SQLite" {
                tags "BaseDatos"
            }
            dbClients = container "Datos de clientes" "Persistencia del subsistema clients." "SQLite" {
                tags "BaseDatos"
            }
            dbPayments = container "Datos de pagos" "Persistencia del subsistema payments." "SQLite" {
                tags "BaseDatos"
            }
            dbIdentity = container "Datos de identidad" "Usuarios, hashes de contraseña y sesiones." "SQLite" {
                tags "BaseDatos"
            }
            dbAnalytics = container "Datos de ventas" "Hechos de venta para reportes." "SQLite" {
                tags "BaseDatos"
            }
        }

        visitante -> sistema "Consulta el menú y la promoción del día"
        cliente -> sistema "Arma pedidos, los paga y revisa su historial"
        cocina -> sistema "Avanza pedidos y revisa existencias"
        administrador -> sistema "Administra carta, stock, promociones y ventas"
        sistema -> proveedorPago "Solicita el procesamiento de pagos"
        proveedorPago -> sistema "Notifica el resultado de los pagos"

        visitante -> sistema.frontend "Consulta el menú como visitante" "Navegador web" "C2"
        cliente -> sistema.frontend "Arma y paga sus pedidos" "Navegador web" "C2"
        cocina -> sistema.frontend "Gestiona la preparación de pedidos" "Navegador web" "C2"
        administrador -> sistema.frontend "Gestiona operaciones autorizadas" "Navegador web" "C2"
        sistema.frontend -> sistema.apiGateway "Envía solicitudes de la interfaz" "HTTPS/JSON" "C2"
        proveedorPago -> sistema.apiGateway "Envía avisos de pago firmados" "HTTPS/JSON + HMAC" "C2"
        sistema.apiGateway -> sistema.authService "Solicita validación de identidad o sesión" "HTTPS/JSON" "C2"
        sistema.apiGateway -> sistema.secretManager "Obtiene secretos autorizados" "Canal autenticado" "C2"
        sistema.authService -> sistema.secretManager "Obtiene sus secretos autorizados" "Canal autenticado" "C2"
        sistema.apiGateway -> sistema.inventory "Enruta consultas del menú, stock y promociones" "HTTPS/JSON" "C2"
        sistema.apiGateway -> sistema.orders "Enruta operaciones de pedidos" "HTTPS/JSON" "C2"
        sistema.apiGateway -> sistema.clients "Enruta operaciones de clientes" "HTTPS/JSON" "C2"
        sistema.apiGateway -> sistema.payments "Enruta operaciones de pago y avisos del proveedor" "HTTPS/JSON" "C2"
        sistema.apiGateway -> sistema.graphqlGateway "Enruta consultas GraphQL" "HTTPS/GraphQL" "C2"
        sistema.inventory -> sistema.secretManager "Obtiene credenciales autorizadas para integraciones" "Canal autenticado" "C2"
        sistema.orders -> sistema.secretManager "Obtiene credenciales autorizadas para integraciones" "Canal autenticado" "C2"
        sistema.clients -> sistema.secretManager "Obtiene credenciales autorizadas para integraciones" "Canal autenticado" "C2"
        sistema.payments -> sistema.secretManager "Obtiene credenciales y el secreto del webhook" "Canal autenticado" "C2"
        sistema.graphqlGateway -> sistema.secretManager "Obtiene credenciales autorizadas para integraciones" "Canal autenticado" "C2"
        sistema.analytics -> sistema.secretManager "Obtiene credenciales autorizadas para integraciones" "Canal autenticado" "C2"
        sistema.orders -> sistema.inventory "Reserva, libera y confirma stock" "HTTPS/JSON" "C2"
        sistema.orders -> sistema.clients "Verifica el cliente del pedido" "HTTPS/JSON" "C2"
        sistema.payments -> sistema.orders "Consulta el pedido y lo marca pagado" "HTTPS/JSON" "C2"
        sistema.payments -> proveedorPago "Solicita la operación de cobro" "HTTPS/JSON" "C2"
        sistema.analytics -> sistema.orders "Exporta las ventas pagadas" "HTTPS/JSON" "C2"
        sistema.authService -> sistema.clients "Crea el perfil al registrarse" "HTTPS/JSON" "C2"
        sistema.graphqlGateway -> sistema.inventory "Agrega información de productos y stock" "HTTPS/JSON" "C2"
        sistema.graphqlGateway -> sistema.orders "Agrega información autorizada de pedidos" "HTTPS/JSON" "C2"
        sistema.graphqlGateway -> sistema.clients "Consulta perfiles autorizados" "HTTPS/JSON" "C2"
        sistema.graphqlGateway -> sistema.payments "Agrega información de pagos" "HTTPS/JSON" "C2"
        sistema.graphqlGateway -> sistema.analytics "Pide resúmenes y sincronización de ventas" "gRPC" "C2"
        sistema.inventory -> sistema.dbInventory "Lee y escribe datos de inventario" "SQL" "C2"
        sistema.orders -> sistema.dbOrders "Lee y escribe pedidos" "SQL" "C2"
        sistema.clients -> sistema.dbClients "Lee y escribe perfiles de clientes" "SQL" "C2"
        sistema.payments -> sistema.dbPayments "Lee y escribe estados de pagos" "SQL" "C2"
        sistema.authService -> sistema.dbIdentity "Consulta y actualiza identidades y sesiones" "SQL" "C2"
        sistema.analytics -> sistema.dbAnalytics "Lee y escribe hechos de venta" "SQL" "C2"

        sistema.frontend -> sistema.apiGateway.adaptadorHttp "Invoca funciones del backend" "HTTPS/JSON"
        proveedorPago -> sistema.apiGateway.adaptadorHttp "Envía webhooks firmados" "HTTPS/JSON + HMAC"
        sistema.apiGateway.adaptadorHttp -> sistema.apiGateway.limitador "Controla tasa, tamaño y tipo del cuerpo"
        sistema.apiGateway.adaptadorHttp -> sistema.apiGateway.tablaRutas "Busca la ruta y el verbo"
        sistema.apiGateway.adaptadorHttp -> sistema.apiGateway.filtroAcceso "Solicita comprobación de acceso"
        sistema.apiGateway.filtroAcceso -> sistema.authService "Introspecta la sesión cuando la ruta lo exige" "HTTPS/JSON"
        sistema.apiGateway.filtroAcceso -> sistema.apiGateway.despachador "Permite una ruta pública o una solicitud autorizada"
        sistema.apiGateway.filtroAcceso -> sistema.apiGateway.clienteSecretos "Usa el secreto de la integración con Auth"
        sistema.apiGateway.filtroAcceso -> sistema.apiGateway.traductorErrores "Rechaza con 401, 403 o 429"
        sistema.apiGateway.despachador -> sistema.apiGateway.clienteSecretos "Obtiene el secreto de cada integración"
        sistema.apiGateway.despachador -> sistema.inventory "Despacha consultas del menú, stock y promociones" "HTTPS/JSON"
        sistema.apiGateway.despachador -> sistema.orders "Despacha operaciones de pedidos" "HTTPS/JSON"
        sistema.apiGateway.despachador -> sistema.clients "Despacha operaciones de clientes" "HTTPS/JSON"
        sistema.apiGateway.despachador -> sistema.payments "Despacha pagos y webhooks" "HTTPS/JSON"
        sistema.apiGateway.despachador -> sistema.graphqlGateway "Despacha consultas GraphQL" "HTTPS/GraphQL"
        sistema.apiGateway.despachador -> sistema.apiGateway.traductorErrores "Reporta fallos del destino (502, 503, 504)"
        sistema.apiGateway.clienteSecretos -> sistema.secretManager "Lee secretos con el token del gateway" "HTTPS"

        sistema.apiGateway -> sistema.graphqlGateway.endpoint "Remite operaciones GraphQL con la identidad verificada" "HTTPS/GraphQL"
        sistema.graphqlGateway.endpoint -> sistema.graphqlGateway.validador "Verifica esquema, profundidad y costo"
        sistema.graphqlGateway.validador -> sistema.graphqlGateway.resolvers "Entrega la consulta válida"
        sistema.graphqlGateway.resolvers -> sistema.graphqlGateway.politicas "Comprueba permisos por campo"
        sistema.graphqlGateway.resolvers -> sistema.graphqlGateway.dataloaders "Pide datos en lote"
        sistema.graphqlGateway.resolvers -> sistema.graphqlGateway.conectores "Crea pedidos y lee listas"
        sistema.graphqlGateway.resolvers -> sistema.graphqlGateway.clienteAnalytics "Pide ventas"
        sistema.graphqlGateway.resolvers -> sistema.graphqlGateway.compositor "Envía datos y errores para componer la respuesta"
        sistema.graphqlGateway.dataloaders -> sistema.graphqlGateway.conectores "Agrupa llamadas por tipo"
        sistema.graphqlGateway.conectores -> sistema.inventory "Consulta productos y disponibilidad" "HTTPS/JSON"
        sistema.graphqlGateway.conectores -> sistema.orders "Consulta pedidos autorizados" "HTTPS/JSON"
        sistema.graphqlGateway.conectores -> sistema.clients "Consulta perfiles autorizados" "HTTPS/JSON"
        sistema.graphqlGateway.conectores -> sistema.payments "Consulta pagos" "HTTPS/JSON"
        sistema.graphqlGateway.conectores -> sistema.secretManager "Obtiene el secreto de cada integración" "HTTPS"
        sistema.graphqlGateway.clienteAnalytics -> sistema.analytics "Llama SalesSummary y Sync" "gRPC"

        sistema.apiGateway -> sistema.authService.apiIdentidad "Inicia, valida y cierra sesiones" "HTTPS/JSON"
        sistema.authService.apiIdentidad -> sistema.authService.verificador "Verifica usuario y clave"
        sistema.authService.apiIdentidad -> sistema.authService.gestorSesiones "Crea, valida y revoca sesiones"
        sistema.authService.apiIdentidad -> sistema.authService.registro "Registra clientes"
        sistema.authService.apiIdentidad -> sistema.authService.clienteSecretos "Verifica el secreto del llamador"
        sistema.authService.verificador -> sistema.authService.repoIdentidad "Lee el hash y los intentos fallidos"
        sistema.authService.gestorSesiones -> sistema.authService.repoIdentidad "Guarda y consulta el hash del token"
        sistema.authService.registro -> sistema.authService.repoIdentidad "Crea, activa o elimina el usuario pendiente"
        sistema.authService.registro -> sistema.authService.conectorClientes "Pide crear el perfil"
        sistema.authService.conectorClientes -> sistema.authService.clienteSecretos "Usa el secreto de la integración con clients"
        sistema.authService.conectorClientes -> sistema.clients "Crea el perfil del cliente" "HTTPS/JSON"
        sistema.authService.repoIdentidad -> sistema.dbIdentity "Lee y escribe identidades y sesiones" "SQL"
        sistema.authService.clienteSecretos -> sistema.secretManager "Obtiene secretos de forma controlada" "HTTPS"

        sistema.apiGateway -> sistema.orders.apiPedidos "Enruta pedidos de clientes, cocina y administración" "HTTPS/JSON"
        sistema.graphqlGateway -> sistema.orders.apiPedidos "Consulta y crea pedidos permitidos" "HTTPS/JSON"
        sistema.payments -> sistema.orders.apiPedidos "Lee el pedido y lo marca pagado" "HTTPS/JSON"
        sistema.analytics -> sistema.orders.apiPedidos "Exporta ventas con cursor" "HTTPS/JSON"
        sistema.orders.apiPedidos -> sistema.orders.politicaAcceso "Comprueba identidad, rol y dueño del recurso"
        sistema.orders.apiPedidos -> sistema.orders.idempotencia "Detecta reintentos con la misma clave"
        sistema.orders.apiPedidos -> sistema.orders.servicioPedidos "Ejecuta la operación admisible"
        sistema.orders.apiPedidos -> sistema.orders.traductorErrores "Responde errores con formato común"
        sistema.orders.idempotencia -> sistema.orders.repoPedidos "Busca operación previa por clave"
        sistema.orders.servicioPedidos -> sistema.orders.adaptadorInventario "Reserva o libera stock"
        sistema.orders.servicioPedidos -> sistema.orders.adaptadorClientes "Verifica el cliente"
        sistema.orders.servicioPedidos -> sistema.orders.repoPedidos "Persiste pedidos, estados y eventos"
        sistema.orders.adaptadorInventario -> sistema.orders.clienteSecretos "Usa el secreto de la integración con inventory"
        sistema.orders.adaptadorClientes -> sistema.orders.clienteSecretos "Usa el secreto de la integración con clients"
        sistema.orders.adaptadorInventario -> sistema.inventory "Invoca el contrato de reservas" "HTTPS/JSON"
        sistema.orders.adaptadorClientes -> sistema.clients "Invoca el contrato de clientes" "HTTPS/JSON"
        sistema.orders.clienteSecretos -> sistema.secretManager "Obtiene secretos de sus integraciones" "HTTPS"
        sistema.orders.repoPedidos -> sistema.dbOrders "Lee y escribe pedidos y claves" "SQL"

        sistema.apiGateway -> sistema.payments.apiPagos "Enruta pagos y webhooks" "HTTPS/JSON"
        sistema.graphqlGateway -> sistema.payments.apiPagos "Consulta pagos de pedidos" "HTTPS/JSON"
        sistema.payments.apiPagos -> sistema.payments.verificadorFirma "Verifica avisos del proveedor"
        sistema.payments.apiPagos -> sistema.payments.controlDuplicados "Detecta reintentos y avisos repetidos"
        sistema.payments.apiPagos -> sistema.payments.servicioPagos "Ejecuta la operación"
        sistema.payments.verificadorFirma -> sistema.payments.clienteSecretos "Lee el secreto HMAC"
        sistema.payments.controlDuplicados -> sistema.payments.repoPagos "Consulta claves y event_id"
        sistema.payments.servicioPagos -> sistema.payments.adaptadorProveedor "Solicita el cobro"
        sistema.payments.servicioPagos -> sistema.payments.adaptadorPedidos "Lee el total y marca pagado"
        sistema.payments.servicioPagos -> sistema.payments.repoPagos "Guarda pagos y avisos"
        sistema.payments.adaptadorProveedor -> proveedorPago "Solicita la operación de pago" "HTTPS/JSON"
        sistema.payments.adaptadorPedidos -> sistema.orders "Consulta y actualiza el pedido" "HTTPS/JSON"
        sistema.payments.adaptadorPedidos -> sistema.payments.clienteSecretos "Usa el secreto de la integración con orders"
        sistema.payments.clienteSecretos -> sistema.secretManager "Obtiene secretos de forma controlada" "HTTPS"
        sistema.payments.repoPagos -> sistema.dbPayments "Lee y escribe pagos" "SQL"

        sistema.dbInventory -> sistema.inventory "Devuelve resultados de consulta" "SQL" "Respuesta"
        sistema.inventory -> sistema.apiGateway "Responde consultas del menú" "HTTPS/JSON" "Respuesta"
        sistema.apiGateway -> sistema.frontend "Devuelve respuestas y errores controlados" "HTTPS/JSON" "Respuesta"
        sistema.frontend -> visitante "Presenta resultados de consulta" "Interfaz web" "Respuesta"
        sistema.frontend -> cliente "Presenta resultados y errores de las operaciones" "Interfaz web" "Respuesta"
        sistema.authService -> sistema.apiGateway "Responde la validación de sesión" "HTTPS/JSON" "Respuesta"
        sistema.clients -> sistema.orders "Confirma el cliente" "HTTPS/JSON" "Respuesta"
        sistema.inventory -> sistema.orders "Devuelve reserva, precios y descuento" "HTTPS/JSON" "Respuesta"
        sistema.dbOrders -> sistema.orders "Devuelve pedidos y claves registradas" "SQL" "Respuesta"
        sistema.orders -> sistema.apiGateway "Responde operaciones y consultas de pedidos" "HTTPS/JSON" "Respuesta"
        sistema.orders -> sistema.payments "Devuelve el pedido y su total" "HTTPS/JSON" "Respuesta"
        sistema.payments -> sistema.apiGateway "Responde operaciones de pago" "HTTPS/JSON" "Respuesta"
        sistema.apiGateway -> proveedorPago "Confirma la recepción del aviso" "HTTPS/JSON" "Respuesta"
        sistema.graphqlGateway -> sistema.apiGateway "Devuelve resultado agregado o errores parciales" "HTTPS/GraphQL" "Respuesta"
        sistema.inventory -> sistema.graphqlGateway "Devuelve productos y disponibilidad" "HTTPS/JSON" "Respuesta"
        sistema.orders -> sistema.graphqlGateway "Devuelve datos autorizados de pedidos" "HTTPS/JSON" "Respuesta"
        sistema.clients -> sistema.graphqlGateway "Devuelve información autorizada del cliente" "HTTPS/JSON" "Respuesta"
        sistema.graphqlGateway.validador -> sistema.graphqlGateway.endpoint "Reporta rechazo de consulta inválida" "" "Respuesta"
        sistema.graphqlGateway.endpoint -> sistema.apiGateway "Responde error GraphQL de validación" "HTTPS/GraphQL" "Respuesta"
        sistema.orders.repoPedidos -> sistema.orders.idempotencia "Devuelve el pedido ya registrado" "" "Respuesta"
        sistema.orders.idempotencia -> sistema.orders.apiPedidos "Devuelve el resultado existente sin procesar de nuevo" "" "Respuesta"
        sistema.orders.apiPedidos -> sistema.apiGateway "Devuelve respuesta controlada de pedidos" "HTTPS/JSON" "Respuesta"

        docker = deploymentEnvironment "Docker_Compose" {
            deploymentNode "Dispositivo del usuario" "Equipo con navegador web que ejecuta el frontend responsivo." "Equipo cliente" {
                tags "ZonaCliente"
                deploymentNode "Navegador web" "Ejecuta index.html, style.css y script.js; no es un servidor backend." "Navegador" {
                    containerInstance sistema.frontend
                }
            }
            deploymentNode "Internet" "Servicios externos a la plataforma." "Red pública" {
                tags "ZonaExterna"
                softwareSystemInstance proveedorPago
            }
            deploymentNode "Equipo con Docker Compose" "Host que ejecuta docker compose up según docker-compose.yml (modelo de la configuración entregada)." "Docker Engine" {
                tags "ZonaEntorno"
                deploymentNode "Red public" "Red bridge; solo el gateway publica el puerto 127.0.0.1:8000." "Red Docker" {
                    tags "ZonaPublica"
                    deploymentNode "Contenedor api-gateway" "Único contenedor con puerto publicado; también está conectado a la red private." "python:3.12-slim, uvicorn" {
                        containerInstance sistema.apiGateway
                    }
                }
                deploymentNode "Red private" "Red interna (internal: true): sin salida a internet ni puertos publicados." "Red Docker" {
                    tags "ZonaPrivada"
                    deploymentNode "Contenedor auth" "Token de Vault propio montado de solo lectura." "python:3.12-slim, uvicorn" {
                        containerInstance sistema.authService
                        deploymentNode "Volumen data_auth" "Archivo SQLite del servicio." "Volumen Docker" {
                            tags "ZonaDatos"
                            containerInstance sistema.dbIdentity
                        }
                    }
                    deploymentNode "Contenedor inventory" "Token de Vault propio montado de solo lectura." "python:3.12-slim, uvicorn" {
                        containerInstance sistema.inventory
                        deploymentNode "Volumen data_inventory" "Archivo SQLite del servicio." "Volumen Docker" {
                            tags "ZonaDatos"
                            containerInstance sistema.dbInventory
                        }
                    }
                    deploymentNode "Contenedor orders" "Token de Vault propio montado de solo lectura." "python:3.12-slim, uvicorn" {
                        containerInstance sistema.orders
                        deploymentNode "Volumen data_orders" "Archivo SQLite del servicio." "Volumen Docker" {
                            tags "ZonaDatos"
                            containerInstance sistema.dbOrders
                        }
                    }
                    deploymentNode "Contenedor clients" "Token de Vault propio montado de solo lectura." "python:3.12-slim, uvicorn" {
                        containerInstance sistema.clients
                        deploymentNode "Volumen data_clients" "Archivo SQLite del servicio." "Volumen Docker" {
                            tags "ZonaDatos"
                            containerInstance sistema.dbClients
                        }
                    }
                    deploymentNode "Contenedor payments" "Token de Vault propio montado de solo lectura." "python:3.12-slim, uvicorn" {
                        containerInstance sistema.payments
                        deploymentNode "Volumen data_payments" "Archivo SQLite del servicio." "Volumen Docker" {
                            tags "ZonaDatos"
                            containerInstance sistema.dbPayments
                        }
                    }
                    deploymentNode "Contenedor analytics" "Servidor gRPC en el puerto 50051 de la red private." "python:3.12-slim, grpcio" {
                        containerInstance sistema.analytics
                        deploymentNode "Volumen data_analytics" "Archivo SQLite del servicio." "Volumen Docker" {
                            tags "ZonaDatos"
                            containerInstance sistema.dbAnalytics
                        }
                    }
                    deploymentNode "Contenedor graphql-gateway" "Sin base de datos propia." "python:3.12-slim, uvicorn" {
                        containerInstance sistema.graphqlGateway
                    }
                    deploymentNode "Contenedor vault" "Vault en modo desarrollo; no es visible desde el navegador." "hashicorp/vault:1.17" {
                        tags "ZonaSecretos"
                        containerInstance sistema.secretManager
                    }
                    infrastructureNode "vault-bootstrap" "Tarea de arranque: crea políticas, un token por servicio y los secretos de cada integración; luego termina." "python:3.12-slim"
                }
            }
        }

        local = deploymentEnvironment "Desarrollo_Local" {
            deploymentNode "Equipo de desarrollo" "Estación local para pruebas: python -m scripts.run_local. La separación pública/privada la imponen los secretos por integración: un servicio llamado directo responde 403." "Estación de trabajo" {
                tags "ZonaLocal"
                deploymentNode "Navegador local" "Abre index.html del frontend." "Navegador" {
                    containerInstance sistema.frontend
                }
                deploymentNode "Proceso de entrada" "API Gateway en 127.0.0.1:8000 (variable GATEWAY_PORT)." "Python, uvicorn" {
                    containerInstance sistema.apiGateway
                }
                deploymentNode "Procesos privados" "Servicios internos en puertos locales entre 20000 y 30000, dentro del mismo proceso." "Python, uvicorn y grpcio" {
                    containerInstance sistema.authService
                    containerInstance sistema.graphqlGateway
                    containerInstance sistema.inventory
                    containerInstance sistema.orders
                    containerInstance sistema.clients
                    containerInstance sistema.payments
                    containerInstance sistema.analytics
                }
                deploymentNode "Vault de desarrollo" "Vault en memoria que aplica políticas y tokens por servicio; token raíz y claves generados en cada arranque." "tools/dev_vault.py" {
                    tags "ZonaSecretos"
                    containerInstance sistema.secretManager
                }
                deploymentNode "Carpeta temporal mariachi-*" "Un archivo SQLite por servicio con datos ficticios." "Sistema de archivos" {
                    tags "ZonaDatos"
                    containerInstance sistema.dbInventory
                    containerInstance sistema.dbOrders
                    containerInstance sistema.dbClients
                    containerInstance sistema.dbPayments
                    containerInstance sistema.dbIdentity
                    containerInstance sistema.dbAnalytics
                }
            }
        }
    }

    views {
        systemContext sistema "C1_Contexto" "Contexto de negocio: actores y dependencias externas." {
            title "C1 - Contexto de la plataforma El Mariachi"
            include *
            exclude "relationship.tag==Respuesta"
            autoLayout lr
        }

        container sistema "C2_Contenedores" "Aplicaciones y almacenes de datos de la plataforma El Mariachi." {
            title "C2 - Contenedores de la plataforma El Mariachi"
            include *
            exclude "relationship.tag==Respuesta"
            autoLayout lr
        }

        container sistema "C2_Catalogo" "Recorrido estructural de la consulta del menú." {
            title "C2 - Vista de catálogo"
            include visitante cliente sistema.frontend sistema.apiGateway sistema.authService sistema.inventory sistema.dbInventory sistema.secretManager
            exclude "relationship.tag==Respuesta"
            autoLayout lr
        }

        container sistema "C2_Pedidos" "Recorrido estructural del registro y pago de pedidos." {
            title "C2 - Vista de pedidos y pagos"
            include cliente cocina sistema.frontend sistema.apiGateway sistema.authService sistema.orders sistema.inventory sistema.clients sistema.payments sistema.dbOrders sistema.dbInventory sistema.dbPayments sistema.secretManager proveedorPago
            exclude "relationship.tag==Respuesta"
            autoLayout lr
        }

        container sistema "C2_Agregacion" "Recorrido estructural de la agregación GraphQL y la analítica de ventas." {
            title "C2 - Vista de agregación y ventas"
            include cliente administrador sistema.frontend sistema.apiGateway sistema.graphqlGateway sistema.inventory sistema.orders sistema.clients sistema.payments sistema.analytics sistema.dbAnalytics
            exclude "relationship.tag==Respuesta"
            autoLayout lr
        }

        component sistema.apiGateway "C3_API_Gateway" "Componentes internos del punto de entrada HTTP." {
            title "C3 - API Gateway"
            include *
            exclude "relationship.tag==C2"
            exclude "relationship.tag==Respuesta"
            autoLayout lr
        }

        component sistema.graphqlGateway "C3_GraphQL" "Validación, autorización y agregación de datos." {
            title "C3 - GraphQL Gateway"
            include *
            exclude "relationship.tag==C2"
            exclude "relationship.tag==Respuesta"
            autoLayout lr
        }

        component sistema.authService "C3_Auth_Service" "Identidad, sesiones, credenciales y secretos." {
            title "C3 - Auth Service"
            include *
            exclude "relationship.tag==C2"
            exclude "relationship.tag==Respuesta"
            autoLayout lr
        }

        component sistema.orders "C3_Orders" "Autorización, idempotencia, lógica y persistencia de pedidos." {
            title "C3 - orders"
            include *
            exclude "relationship.tag==C2"
            exclude "relationship.tag==Respuesta"
            autoLayout lr
        }

        component sistema.payments "C3_Payments" "Firma del webhook, duplicados, cobro y sincronización con orders." {
            title "C3 - payments"
            include *
            exclude "relationship.tag==C2"
            exclude "relationship.tag==Respuesta"
            autoLayout lr
        }

        dynamic sistema "D_F01_Exito" "Lectura del menú desde el navegador hasta inventory y regreso. Prueba: test_catalogo_publico_para_visitantes_solo_campos_publicos." {
            title "F01 - Consulta del menú: éxito"
            1: visitante -> sistema.frontend "Abre la pantalla Menú"
            2: sistema.frontend -> sistema.apiGateway "GET /products sin sesión" "HTTPS/JSON"
            3: sistema.apiGateway -> sistema.inventory "Enruta la consulta pública" "HTTPS/JSON"
            4: sistema.inventory -> sistema.dbInventory "Busca los platillos activos" "SQL"
            5: sistema.dbInventory -> sistema.inventory "Devuelve los 12 platillos" "SQL"
            6: sistema.inventory -> sistema.apiGateway "Responde solo campos públicos" "HTTPS/JSON"
            7: sistema.apiGateway -> sistema.frontend "Devuelve 200 con el menú y su X-Request-Id" "HTTPS/JSON"
            8: sistema.frontend -> visitante "Presenta los platillos o 'No se encontraron platillos'"
            autoLayout lr
        }

        dynamic sistema "D_F01_Recuperacion" "inventory no disponible: error controlado y nuevo intento tras restaurarlo (comprobado con el sistema local: 502 y luego 200)." {
            title "F01 - Fallo controlado y recuperación"
            1: visitante -> sistema.frontend "Abre el menú"
            2: sistema.frontend -> sistema.apiGateway "GET /products" "HTTPS/JSON"
            3: sistema.apiGateway -> sistema.inventory "Consulta el menú con un reintento automático; no responde" "HTTPS/JSON"
            4: sistema.apiGateway -> sistema.frontend "502 'Servicio inventory no disponible' (504 si vence el plazo de 3 s)" "HTTPS/JSON"
            5: sistema.frontend -> visitante "Muestra el error sin presentar datos falsos"
            6: visitante -> sistema.frontend "Reintenta tras restaurar inventory"
            7: sistema.frontend -> sistema.apiGateway "Reintenta GET /products" "HTTPS/JSON"
            8: sistema.apiGateway -> sistema.inventory "Consulta el menú recuperado" "HTTPS/JSON"
            9: sistema.inventory -> sistema.dbInventory "Busca los platillos activos" "SQL"
            10: sistema.dbInventory -> sistema.inventory "Devuelve los platillos" "SQL"
            11: sistema.inventory -> sistema.apiGateway "Responde el menú" "HTTPS/JSON"
            12: sistema.apiGateway -> sistema.frontend "Devuelve 200 con el menú" "HTTPS/JSON"
            13: sistema.frontend -> visitante "Muestra los platillos recuperados"
            autoLayout lr
        }

        dynamic sistema "D_F02_Exito" "Registro de un pedido con validación de identidad, cliente, reserva de stock, 2x1 y persistencia. Pruebas: test_orden_reserva_stock_y_calcula_total_en_servidor y test_p01_promocion_del_dia_se_aplica_en_el_servidor." {
            title "F02 - Registro de pedido: éxito"
            1: cliente -> sistema.frontend "Confirma el carrito: 2 Tacos al Pastor y 1 Quesadilla Mixta"
            2: sistema.frontend -> sistema.apiGateway "POST /orders con cookie de sesión e Idempotency-Key" "HTTPS/JSON"
            3: sistema.apiGateway -> sistema.authService "Introspecta la sesión" "HTTPS/JSON"
            4: sistema.authService -> sistema.apiGateway "Sesión válida: usuario, rol customer y client_id" "HTTPS/JSON"
            5: sistema.apiGateway -> sistema.orders "Enruta con la identidad verificada" "HTTPS/JSON"
            6: sistema.orders -> sistema.clients "Verifica el cliente del pedido" "HTTPS/JSON"
            7: sistema.clients -> sistema.orders "Cliente existe" "HTTPS/JSON"
            8: sistema.orders -> sistema.inventory "Reserva stock y pide precios y promoción" "HTTPS/JSON"
            9: sistema.inventory -> sistema.orders "Reserva hecha: subtotal 8200, descuento 2x1 de 2500" "HTTPS/JSON"
            10: sistema.orders -> sistema.dbOrders "Guarda el pedido pendiente_pago y la clave" "SQL"
            11: sistema.dbOrders -> sistema.orders "Confirma la escritura" "SQL"
            12: sistema.orders -> sistema.apiGateway "201 con id, total 5700 y estado" "HTTPS/JSON"
            13: sistema.apiGateway -> sistema.frontend "Responde la operación" "HTTPS/JSON"
            14: sistema.frontend -> cliente "Muestra la confirmación del pedido"
            autoLayout lr
        }

        dynamic sistema "D_F02_Pago" "Pago del pedido: inicio con clave de idempotencia y confirmación por aviso firmado del proveedor. Pruebas: test_pago_exitoso_marca_la_orden_pagada y test_webhook_duplicado_no_paga_dos_veces." {
            title "F02 - Pago del pedido"
            1: cliente -> sistema.frontend "Paga el pedido"
            2: sistema.frontend -> sistema.apiGateway "POST /payments con Idempotency-Key" "HTTPS/JSON"
            3: sistema.apiGateway -> sistema.authService "Introspecta la sesión" "HTTPS/JSON"
            4: sistema.authService -> sistema.apiGateway "Sesión válida" "HTTPS/JSON"
            5: sistema.apiGateway -> sistema.payments "Enruta el pago" "HTTPS/JSON"
            6: sistema.payments -> sistema.orders "Lee el pedido y su total" "HTTPS/JSON"
            7: sistema.orders -> sistema.payments "Pedido propio y pendiente; total 5700" "HTTPS/JSON"
            8: sistema.payments -> proveedorPago "Solicita el cobro" "HTTPS/JSON"
            9: sistema.payments -> sistema.apiGateway "201 pago pendiente" "HTTPS/JSON"
            10: sistema.apiGateway -> sistema.frontend "Responde la operación" "HTTPS/JSON"
            11: proveedorPago -> sistema.apiGateway "Envía el aviso firmado con HMAC" "HTTPS/JSON + HMAC"
            12: sistema.apiGateway -> sistema.payments "Enruta el webhook" "HTTPS/JSON"
            13: sistema.payments -> sistema.orders "Marca el pedido pagado (monto verificado)" "HTTPS/JSON"
            14: sistema.payments -> sistema.apiGateway "Aviso procesado; un duplicado no cobra de nuevo" "HTTPS/JSON"
            15: sistema.apiGateway -> proveedorPago "Confirma la recepción del aviso" "HTTPS/JSON"
            autoLayout lr
        }

        dynamic sistema "D_F02_Reintento" "Segunda ejecución con la misma clave: devuelve el pedido existente sin reservar de nuevo. Prueba: test_idempotencia_al_crear_orden." {
            title "F02 - Reintento de pedido: sin duplicación"
            1: cliente -> sistema.frontend "Reintenta el mismo pedido tras una respuesta incierta"
            2: sistema.frontend -> sistema.apiGateway "POST /orders con la misma Idempotency-Key" "HTTPS/JSON"
            3: sistema.apiGateway -> sistema.authService "Introspecta la sesión" "HTTPS/JSON"
            4: sistema.authService -> sistema.apiGateway "Sesión válida" "HTTPS/JSON"
            5: sistema.apiGateway -> sistema.orders "Remite la solicitud repetida" "HTTPS/JSON"
            6: sistema.orders -> sistema.dbOrders "Busca la clave del cliente" "SQL"
            7: sistema.dbOrders -> sistema.orders "Devuelve el pedido ya registrado" "SQL"
            8: sistema.orders -> sistema.apiGateway "200 con el mismo pedido; no crea otro ni reserva stock" "HTTPS/JSON"
            9: sistema.apiGateway -> sistema.frontend "Devuelve el identificador previo" "HTTPS/JSON"
            10: sistema.frontend -> cliente "Muestra el pedido existente"
            autoLayout lr
        }

        dynamic sistema.orders "D_F02_Idempotencia_C3" "Detalle de una solicitud repetida dentro del servicio orders." {
            title "F02 - Idempotencia: componentes internos"
            1: sistema.apiGateway -> sistema.orders.apiPedidos "Entrega el POST repetido y la clave" "HTTPS/JSON"
            2: sistema.orders.apiPedidos -> sistema.orders.politicaAcceso "Verifica identidad y rol customer"
            3: sistema.orders.apiPedidos -> sistema.orders.idempotencia "Busca la clave del cliente"
            4: sistema.orders.idempotencia -> sistema.orders.repoPedidos "Consulta claves usadas"
            5: sistema.orders.repoPedidos -> sistema.dbOrders "Lee la tabla idempotency" "SQL"
            6: sistema.orders.repoPedidos -> sistema.orders.idempotencia "Entrega el pedido existente"
            7: sistema.orders.idempotencia -> sistema.orders.apiPedidos "Retorna el resultado sin ejecutar el servicio de pedidos"
            8: sistema.orders.apiPedidos -> sistema.apiGateway "200 con el mismo pedido, sin duplicar" "HTTPS/JSON"
            autoLayout lr
        }

        dynamic sistema "D_F03_Propio" "Lectura autorizada de un pedido propio. Prueba: test_propiedad_de_ordenes_entre_clientes." {
            title "F03 - Consulta protegida: pedido propio"
            1: cliente -> sistema.frontend "Abre un pedido propio"
            2: sistema.frontend -> sistema.apiGateway "GET /orders/{id}" "HTTPS/JSON"
            3: sistema.apiGateway -> sistema.authService "Comprueba la sesión" "HTTPS/JSON"
            4: sistema.authService -> sistema.apiGateway "Sesión válida con client_id" "HTTPS/JSON"
            5: sistema.apiGateway -> sistema.orders "Solicita el pedido con la identidad verificada" "HTTPS/JSON"
            6: sistema.orders -> sistema.dbOrders "Consulta el pedido" "SQL"
            7: sistema.dbOrders -> sistema.orders "Devuelve el pedido; client_id coincide" "SQL"
            8: sistema.orders -> sistema.apiGateway "200 con los datos del pedido" "HTTPS/JSON"
            9: sistema.apiGateway -> sistema.frontend "Devuelve el pedido" "HTTPS/JSON"
            10: sistema.frontend -> cliente "Muestra número, estado y total"
            autoLayout lr
        }

        dynamic sistema "D_F03_Ajeno" "Prueba negativa de autorización por dueño del recurso. Prueba: test_propiedad_de_ordenes_entre_clientes." {
            title "F03 - Consulta protegida: pedido ajeno"
            1: cliente -> sistema.frontend "Intenta abrir el pedido de otro cliente"
            2: sistema.frontend -> sistema.apiGateway "GET /orders/{idAjeno}" "HTTPS/JSON"
            3: sistema.apiGateway -> sistema.authService "Comprueba la sesión" "HTTPS/JSON"
            4: sistema.authService -> sistema.apiGateway "Sesión válida (no implica acceso al pedido)" "HTTPS/JSON"
            5: sistema.apiGateway -> sistema.orders "Consulta el recurso con la identidad verificada" "HTTPS/JSON"
            6: sistema.orders -> sistema.dbOrders "Consulta el pedido" "SQL"
            7: sistema.dbOrders -> sistema.orders "El client_id no coincide" "SQL"
            8: sistema.orders -> sistema.apiGateway "404 'Orden no encontrada': no revela que existe" "HTTPS/JSON"
            9: sistema.apiGateway -> sistema.frontend "Entrega el error con su request_id" "HTTPS/JSON"
            10: sistema.frontend -> cliente "Muestra el rechazo sin datos ajenos"
            autoLayout lr
        }

        dynamic sistema "D_F03_Expirada" "El gateway rechaza antes de llamar al servicio protegido. Pruebas: test_sesion_expirada_401 y test_gateway_corta_antes_de_llamar_al_servicio." {
            title "F03 - Sesión expirada: rechazo temprano"
            1: cliente -> sistema.frontend "Consulta un pedido con la sesión vencida (15 minutos)"
            2: sistema.frontend -> sistema.apiGateway "GET /orders/{id} con cookie vencida" "HTTPS/JSON"
            3: sistema.apiGateway -> sistema.authService "Introspecta la sesión" "HTTPS/JSON"
            4: sistema.authService -> sistema.apiGateway "Sesión expirada o revocada" "HTTPS/JSON"
            5: sistema.apiGateway -> sistema.frontend "401 'Sesion requerida'; orders no recibe la solicitud" "HTTPS/JSON"
            6: sistema.frontend -> cliente "Pide iniciar sesión sin mostrar el pedido"
            autoLayout lr
        }

        dynamic sistema "D_F04_GraphQL_Exito" "La pantalla de confirmación obtiene pedido, cliente y productos en una sola consulta. Pruebas: test_p04_confirmacion_con_una_sola_consulta_graphql y test_batching_evita_n_mas_1." {
            title "F04 - GraphQL: agregación exitosa"
            1: cliente -> sistema.frontend "Abre la confirmación de su pedido"
            2: sistema.frontend -> sistema.apiGateway "POST /graphql con order(id)" "HTTPS/JSON"
            3: sistema.apiGateway -> sistema.authService "Introspecta la sesión" "HTTPS/JSON"
            4: sistema.authService -> sistema.apiGateway "Sesión válida" "HTTPS/JSON"
            5: sistema.apiGateway -> sistema.graphqlGateway "Entrega la consulta y la identidad verificada" "HTTPS/GraphQL"
            6: sistema.graphqlGateway -> sistema.orders "Consulta el pedido autorizado" "HTTPS/JSON"
            7: sistema.orders -> sistema.graphqlGateway "Devuelve el pedido" "HTTPS/JSON"
            8: sistema.graphqlGateway -> sistema.clients "Pide los clientes en un lote" "HTTPS/JSON"
            8: sistema.graphqlGateway -> sistema.inventory "Pide los productos en un lote" "HTTPS/JSON"
            9: sistema.clients -> sistema.graphqlGateway "Devuelve nombre y teléfono" "HTTPS/JSON"
            9: sistema.inventory -> sistema.graphqlGateway "Devuelve los productos" "HTTPS/JSON"
            10: sistema.graphqlGateway -> sistema.apiGateway "Compone la respuesta agregada" "HTTPS/GraphQL"
            11: sistema.apiGateway -> sistema.frontend "Entrega el resultado autorizado" "HTTPS/JSON"
            12: sistema.frontend -> cliente "Muestra número, fecha, cliente, ítems y total"
            autoLayout lr
        }

        dynamic sistema "D_F04_GraphQL_Parcial" "Una dependencia cae y la respuesta parcial queda identificada, no se presenta como completa. Prueba: test_errores_parciales_si_clientes_no_responde." {
            title "F04 - GraphQL: dependencia fallida"
            1: cliente -> sistema.frontend "Consulta sus pedidos"
            2: sistema.frontend -> sistema.apiGateway "POST /graphql con myOrders" "HTTPS/JSON"
            3: sistema.apiGateway -> sistema.authService "Introspecta la sesión" "HTTPS/JSON"
            4: sistema.authService -> sistema.apiGateway "Sesión válida" "HTTPS/JSON"
            5: sistema.apiGateway -> sistema.graphqlGateway "Remite la consulta permitida" "HTTPS/GraphQL"
            6: sistema.graphqlGateway -> sistema.orders "Consulta los pedidos" "HTTPS/JSON"
            7: sistema.orders -> sistema.graphqlGateway "Devuelve los pedidos" "HTTPS/JSON"
            8: sistema.graphqlGateway -> sistema.clients "Pide los clientes (clients no responde)" "HTTPS/JSON"
            9: sistema.graphqlGateway -> sistema.apiGateway "Pedidos completos, client: null y error en la ruta myOrders.nodes.0.client" "HTTPS/GraphQL"
            10: sistema.apiGateway -> sistema.frontend "Transmite datos y errores" "HTTPS/JSON"
            11: sistema.frontend -> cliente "Informa que faltan los datos del cliente"
            autoLayout lr
        }

        dynamic sistema.graphqlGateway "D_F04_GraphQL_Limite_C3" "Rechazo antes de ejecutar resolvers o consultar servicios privados. Prueba: test_limite_de_costo_rechaza_consultas_abusivas." {
            title "F04 - GraphQL: consulta excede el límite"
            1: sistema.apiGateway -> sistema.graphqlGateway.endpoint "Envía una consulta de costo 7206" "HTTPS/GraphQL"
            2: sistema.graphqlGateway.endpoint -> sistema.graphqlGateway.validador "Calcula profundidad y costo"
            3: sistema.graphqlGateway.validador -> sistema.graphqlGateway.endpoint "Rechaza: excede el máximo 5000"
            4: sistema.graphqlGateway.endpoint -> sistema.apiGateway "Devuelve el error sin llamar a resolvers" "HTTPS/GraphQL"
            autoLayout lr
        }

        deployment sistema docker "DEP_Docker" "Ubicación de aplicaciones, datos y secretos según docker-compose.yml." {
            title "Despliegue - Docker Compose (configuración entregada)"
            include *
            exclude "relationship.tag==Respuesta"
            autoLayout lr
        }

        deployment sistema local "DEP_Local" "Todos los servicios en un equipo con python -m scripts.run_local." {
            title "Despliegue - Desarrollo local"
            include *
            exclude "relationship.tag==Respuesta"
            autoLayout lr
        }

        styles {
            element "Deployment Node" {
                background #E9EFF5
                color #213F56
                stroke #8FA5B7
            }
            element "Infrastructure Node" {
                shape roundedbox
                background #EDF0F3
                color #334454
            }
            element "ZonaCliente" {
                background #F1F5F9
                color #173B5D
            }
            element "ZonaExterna" {
                background #F7F3EC
                color #544633
            }
            element "ZonaEntorno" {
                background #F4F6F8
                color #213F56
            }
            element "ZonaPublica" {
                background #DCEAF7
                color #173B5D
            }
            element "ZonaPrivada" {
                background #E5EEE8
                color #20513D
            }
            element "ZonaDatos" {
                background #ECEAF2
                color #463D64
            }
            element "ZonaSecretos" {
                background #EEE5E1
                color #68483C
            }
            element "ZonaLocal" {
                background #F0F3F6
                color #243F56
            }
            element "Person" {
                shape person
                background #56718A
                color #FFFFFF
            }
            element "Software System" {
                shape roundedbox
                background #0C527A
                color #FFFFFF
            }
            element "SistemaEvaluado" {
                background #173B5D
                color #FFFFFF
            }
            element "Container" {
                shape roundedbox
                background #E3ECF5
                color #173B5D
            }
            element "Frontend" {
                shape webbrowser
                background #CDE5F7
                color #153E5B
            }
            element "Gateway" {
                background #2B6289
                color #FFFFFF
            }
            element "Seguridad" {
                background #3F6171
                color #FFFFFF
            }
            element "Privado" {
                background #D5E8EF
                color #173B5D
            }
            element "BaseDatos" {
                shape cylinder
                background #E5EAF0
                color #243F56
            }
            element "SistemaExterno" {
                background #F1EDE7
                color #544633
                stroke #A89D8A
            }
            element "Analitica" {
                background #E7E0F2
                color #453166
            }
            element "Component" {
                shape roundedbox
                background #EDF3F7
                color #173B5D
            }
            element "EntradaC3" {
                background #D3E9F7
                color #153F62
            }
            element "ControlC3" {
                background #DBE4EC
                color #213F56
            }
            element "AplicacionC3" {
                background #D7E9DE
                color #20533E
            }
            element "IntegracionC3" {
                background #E9E2F2
                color #4A3666
            }
            element "PersistenciaC3" {
                background #E9EBEE
                color #334454
            }
            element "ErrorC3" {
                background #F2E6DB
                color #70462C
            }
            relationship "Relationship" {
                color #60758A
                thickness 2
            }
            relationship "Respuesta" {
                style dashed
            }
        }
    }
}
