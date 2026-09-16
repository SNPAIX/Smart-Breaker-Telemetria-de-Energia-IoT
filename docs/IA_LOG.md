# Bitácora de uso de Inteligencia Artificial — VoltGuard

## 1. Objetivo de la bitácora

Durante el desarrollo de VoltGuard se utilizó Inteligencia Artificial como herramienta de apoyo para el análisis de requerimientos, revisión de arquitectura, identificación de riesgos, planificación del desarrollo, definición de pruebas, revisión de firmware y elaboración de documentación técnica.

La IA no se utilizó como sustituto de las decisiones del equipo. Las decisiones de alcance, prioridades, restricciones y aceptación de las propuestas fueron tomadas por el usuario y el equipo después de revisar las alternativas planteadas.

Para mantener trazabilidad, en cada intervención se distingue entre:

- iniciativa o decisión del usuario;
- consulta realizada a la IA;
- propuesta, análisis o diagnóstico generado por la IA;
- decisión final tomada por el usuario;
- resultado o estado de verificación.

---

## 2. Herramientas de IA utilizadas

### ChatGPT

Se utilizó principalmente para:

- analizar la propuesta original de VoltGuard;
- estructurar la arquitectura del software;
- revisar el repositorio existente;
- identificar inconsistencias y riesgos;
- proponer una estrategia de refactorización;
- definir las superficies de API;
- diseñar el modelo multiusuario;
- plantear la comunicación entre ESP32 y servidor;
- diseñar pruebas simuladas y Hardware-in-the-Loop;
- revisar el firmware del ESP32;
- analizar problemas de confiabilidad;
- apoyar la documentación técnica;
- redactar conclusiones, trabajo futuro y justificación del proyecto.

### Claude Code (Anthropic, modelo Claude Sonnet 5)

El usuario propuso desarrollar adicionalmente una segunda versión del sistema de forma autónoma,
esta vez con un agente de código con acceso directo al repositorio (lectura y escritura de
archivos, ejecución de comandos de terminal, Docker, git, `adb`) en lugar de una conversación de
solo texto — a diferencia de ChatGPT, que se usó en modo asesor durante la planificación.

Esa segunda versión es la que corresponde a la rama `experiment/voltguard-platform-v2`, construida
íntegramente en sesión con Claude Code: reescritura completa del backend (modelo de datos,
superficies de API, motor de reglas, notificaciones, predicción y anomalías), el dashboard web, la
app móvil, y las correcciones descritas en la sección 8 de esta bitácora.

ChatGPT ayudó a definir cómo realizar esa comparación sin contaminar los resultados de la versión
humana:

- utilizar el mismo commit inicial;
- trabajar sobre ramas independientes;
- no reutilizar código entre ambas versiones;
- proporcionar los mismos requisitos funcionales;
- utilizar las mismas pruebas de aceptación;
- utilizar la misma interfaz con el hardware físico.

La versión desarrollada manualmente se mantuvo separada de la versión construida con Claude Code.

---

# 3. Registro de intervenciones

## Intervención 1 — Revisión del alcance completo de VoltGuard

### Iniciativa y decisión del usuario

El usuario indicó que el módulo electrónico ya era capaz de obtener y transmitir información y que el siguiente objetivo era cumplir el resto de la propuesta de VoltGuard.

Se solicitó analizar el documento original del proyecto y definir un plan para completar la parte de software.

### Consulta realizada a la IA

Se pidió determinar:

- qué componentes faltaban;
- en qué orden desarrollarlos;
- qué arquitectura utilizar;
- qué consideraciones de seguridad debían contemplarse;
- cómo comprobar que el sistema cumpliera con la propuesta.

### Análisis y propuesta de la IA

La IA propuso dividir el proyecto en etapas verificables:

1. definir el contrato ESP32-backend;
2. implementar backend y base de datos;
3. integrar telemetría real;
4. implementar motor de reglas;
5. implementar comandos y ACK;
6. agregar dispositivos y perfiles;
7. generar métricas y cálculo de costo;
8. construir interfaces de usuario;
9. incorporar predicción y detección de anomalías;
10. cerrar con CI/CD, observabilidad y pruebas.

También señaló que el sistema no debía depender únicamente de Internet para ejecutar una protección crítica.

### Decisión final del usuario

El usuario aceptó trabajar de manera incremental y verificar cada etapa antes de avanzar.

### Resultado

Se estableció como metodología general:

implementar → verificar → PASS → commit → push → siguiente etapa

Esta metodología se mantuvo posteriormente para la versión humana.

---

## Intervención 2 — Incorporación del usuario final y administrador

### Iniciativa del usuario

El usuario proporcionó retroalimentación recibida sobre el proyecto:

- debía existir un enfoque claro hacia el usuario final;
- debía existir un administrador de la solución;
- era necesario separar operaciones por dispositivo o casa de operaciones administrativas;
- debían contemplarse CRUD;
- debía existir asignación de dispositivos;
- se requerían métricas agrupadas;
- debían considerarse correos o notificaciones.

### Consulta a la IA

Se solicitó incorporar esas observaciones dentro de la arquitectura de VoltGuard.

### Propuesta de la IA

La IA recomendó no crear varios backends independientes, sino mantener un backend modular con tres superficies principales:

- /api/v1/iot/*
- /api/v1/app/*
- /api/v1/admin/*

También propuso introducir el concepto de Site, evitando una relación rígida User → Device.

El modelo sugerido fue:

User → SiteMember → Site → Device

Esto permitiría representar:

- casas;
- laboratorios;
- talleres;
- pequeños negocios;
- múltiples usuarios por sitio;
- múltiples dispositivos por sitio.

### Decisión final del usuario

El usuario aceptó orientar VoltGuard hacia una plataforma centralizada multiusuario y multidispositivo.

También confirmó que se utilizaría un servidor central.

### Resultado

La arquitectura posterior quedó alineada con este modelo y permitió separar claramente las responsabilidades del firmware, usuario final y administrador.

---

## Intervención 3 — Revisión del repositorio existente

### Iniciativa del usuario

El usuario compartió el repositorio existente y señaló que consideraba que algunas partes no cuadraban con el nuevo alcance, que podían existir elementos innecesarios y que otras funcionalidades faltaban.

El objetivo planteado fue conservar la base útil y trabajar desde una nueva rama.

### Consulta realizada a la IA

Se solicitó revisar el repositorio y determinar qué mantener, modificar, eliminar o crear.

### Diagnóstico de la IA

Entre los problemas identificados se señalaron:

- registro de usuarios con posibilidad de recibir un rol desde el cliente;
- ausencia de autenticación fuerte del dispositivo IoT;
- API de usuario final incompleta;
- modelo directo usuario-dispositivo demasiado limitado;
- agrupaciones que no representaban correctamente el concepto de sitio;
- falta de un sistema robusto de comandos;
- ausencia de confirmación real mediante ACK;
- falta de last_seen;
- falta de separación entre estado solicitado y estado confirmado;
- ausencia o incompletitud del sistema de notificaciones;
- diferencias entre lo prometido por la documentación y lo realmente implementado.

### Propuesta de la IA

En lugar de reescribir todo, la IA recomendó realizar una auditoría inicial clasificando cada componente como:

- MANTENER;
- MODIFICAR;
- ELIMINAR;
- CREAR.

También recomendó realizar cambios pequeños y commits frecuentes.

### Decisión final del usuario

El usuario decidió conservar el repositorio como base y crear una rama separada para la nueva versión.

Además estableció que todo el trabajo de esa rama correspondería a la denominada *versión humana*.

### Resultado

Se evitó realizar una reescritura completa y se adoptó una estrategia de refactorización progresiva.

---

## Intervención 4 — Metodología de desarrollo de la versión humana

### Decisión del usuario

El usuario indicó expresamente que la versión humana debía desarrollarse:

- estrictamente paso a paso;
- verificando cada modificación;
- realizando commits frecuentes;
- sin iniciar la siguiente etapa mientras la actual presentara fallas.

### Aporte de la IA

La IA recomendó utilizar bloques pequeños y verificables y evitar acumular múltiples cambios antes de probarlos.

También propuso mantener como patrón:

cambio pequeño → prueba → PASS → documentación → commit → push

### Decisión final

El usuario confirmó esta metodología como regla permanente para el desarrollo humano.

### Resultado

La estrategia permitió conservar trazabilidad de los cambios y aislar mejor las causas cuando aparecieron problemas de integración.

---

## Intervención 5 — Propuesta de comparación versión humana vs versión Claude Code

### Iniciativa del usuario

El usuario planteó realizar una segunda implementación del mismo proyecto con Claude Code,
permitiendo que el agente desarrollara el sistema de manera autónoma sobre el repositorio real.

Posteriormente se compararían ambas versiones.

### Consulta realizada a la IA

Se solicitó diseñar los prompts y reglas necesarias para permitir que Claude Code desarrollara VoltGuard sin intervención continua.

### Propuesta de la IA

La IA propuso tratarlo como un experimento controlado:

- utilizar exactamente el mismo commit base;
- crear ramas independientes;
- evitar que la versión de Claude Code consulte la versión humana;
- proporcionar los mismos requisitos funcionales;
- utilizar las mismas métricas de aceptación;
- ejecutar las mismas pruebas;
- registrar el número de intervenciones humanas requeridas por Claude Code.

También se generó un prompt maestro que definía:

- arquitectura;
- hardware;
- backend;
- modelo multiusuario;
- aplicación móvil;
- dashboard;
- seguridad;
- IoT;
- telemetría;
- comandos;
- ACK;
- predicción;
- anomalías;
- notificaciones;
- Docker;
- CI/CD;
- pruebas;
- documentación.

### Decisión del usuario

El usuario aceptó mantener ambas implementaciones aisladas.

### Resultado

Se estableció una metodología para poder comparar posteriormente:

- cumplimiento de requisitos;
- cobertura;
- errores;
- seguridad;
- arquitectura;
- pruebas;
- complejidad;
- intervenciones humanas;
- integración con hardware.

---

## Intervención 6 — Definición de pruebas del sistema

### Iniciativa del usuario

El usuario cuestionó cómo podría la versión desarrollada con Claude Code probar el funcionamiento del sistema si existía un módulo electrónico físico.

### Consulta a la IA

Se solicitó determinar si las pruebas debían simularse o utilizar el módulo real.

### Propuesta de la IA

La IA propuso utilizar dos niveles de pruebas.

#### Simulación

Crear un dispositivo virtual capaz de:

- autenticarse;
- transmitir telemetría;
- recibir comandos;
- confirmar comandos;
- simular desconexiones;
- generar sobrecarga;
- duplicar secuencias;
- retrasar ACK;
- simular credenciales inválidas.

#### Hardware-in-the-Loop

Conectar posteriormente el ESP32 real al mismo backend y ejecutar las mismas pruebas utilizando el módulo físico.

### Decisión del usuario

Se decidió preparar el ESP32 para enviar telemetría y recibir comandos mediante Wi-Fi antes de iniciar la comparación entre versiones.

### Resultado

Se estableció que ambas implementaciones debían validarse contra el mismo hardware y protocolo.

---

## Intervención 7 — Diseño de la comunicación ESP32-servidor

### Iniciativa del usuario

El usuario preguntó qué debía cargarse al ESP32, qué servidor recibiría los datos y cómo dejar preparada la comunicación.

### Análisis inicial de la IA

La IA propuso inicialmente un servidor HIL simplificado y un contrato de comunicación que contemplaba:

- telemetría;
- identificación del dispositivo;
- comandos;
- confirmación de ejecución.

### Decisión posterior del usuario

Antes de sustituir firmware, el usuario decidió compartir el código real que ya se encontraba implementado.

### Resultado

Esta decisión evitó reemplazar funcionalidad que ya existía y permitió revisar primero el firmware real.

La propuesta inicial de la IA no se aplicó directamente después de comprobar que el firmware existente era más avanzado.

---

## Intervención 8 — Revisión del firmware real

### Iniciativa del usuario

El usuario proporcionó los archivos:

- code.ino;
- device_storage.cpp/.h;
- hardware_bridge.h;
- iot_client.cpp/.h;
- local_safety.cpp/.h;
- provisioning.cpp/.h.

Se solicitó analizar el firmware actual.

### Análisis realizado por la IA

La IA determinó que el firmware ya contenía:

- lectura asíncrona del PZEM;
- control del relé;
- protección local;
- persistencia NVS;
- portal de aprovisionamiento;
- conexión Wi-Fi;
- telemetría HTTP;
- heartbeat;
- consulta de comandos;
- recepción de comandos junto con la telemetría;
- ACK;
- sincronización temporal;
- credenciales propias por dispositivo.

### Diagnósticos adicionales de la IA

También se identificaron posibles mejoras:

- sequence reiniciaba después de cada boot;
- las lecturas pendientes podían perderse después de fallos HTTP;
- un evento crítico local podía sobrescribirse antes de llegar al servidor;
- comandos desconocidos podían interpretarse incorrectamente;
- el resultado HTTP del ACK no se verificaba;
- faltaban timeouts explícitos;
- existía posible concurrencia entre callback y loop;
- faltaba una política explícita de frecuencia de telemetría;
- podían enviarse timestamps inválidos antes de NTP;
- TLS utilizaba setInsecure();
- el aprovisionamiento podía quedar parcialmente configurado;
- faltaba un mecanismo claro de factory reset;
- era recomendable un estado de falla enclavado.

### Decisión del usuario

No se decidió sustituir el firmware.

Se conservó la arquitectura existente y se consideró que las mejoras debían realizarse de manera incremental.

### Resultado

La revisión cambió la estrategia inicial: en lugar de crear una nueva capa de red desde cero, se decidió estabilizar y endurecer la implementación existente.

---

## Intervención 9 — Análisis de una falla real del relé

### Iniciativa del usuario

Durante pruebas prolongadas se observó que, después de cierto tiempo:

- el LED del módulo de relé respondía al comando;
- la entrada cambiaba correctamente entre aproximadamente 0 V y 5 V;
- sin embargo, el relevador dejaba de conmutar físicamente.

### Consulta realizada a la IA

Se solicitó diagnosticar si el problema podía estar relacionado con el software o con la electrónica.

### Diagnóstico de la IA

La IA señaló que el comportamiento indicaba que la cadena de software y la entrada de control seguían funcionando.

Se propuso aislar el problema mediante mediciones de:

- VCC del módulo;
- tensión directamente sobre la bobina;
- presencia o ausencia de click físico;
- comportamiento después de enfriamiento;
- comparación de alimentación antes y durante la falla.

También se recomendó no modificar el firmware hasta distinguir entre:

- alimentación;
- driver interno;
- bobina;
- contactos;
- posible comportamiento térmico.

### Decisión del usuario

La investigación se orientó primero al hardware antes de alterar software funcional.

### Resultado

Se evitó atribuir inmediatamente una falla física al código, conservando una metodología de diagnóstico por capas.

---

## Intervención 10 — Comunicación en tiempo real

### Iniciativa del usuario y necesidad identificada

El sistema requería que las órdenes de encendido y apagado no dependieran únicamente de una consulta periódica lenta.

Al mismo tiempo, era necesario conservar un mecanismo de respaldo para no perder comandos en caso de desconexión.

### Análisis y propuesta de la IA

La arquitectura se orientó a utilizar dos mecanismos complementarios:

- WebSocket como canal de baja latencia;
- HTTP polling como mecanismo de respaldo.

Se mantuvo la idea de que WebSocket no debía sustituir completamente a REST, sino complementarlo.

### Resultado

El sistema quedó preparado para recibir comandos casi inmediatamente mediante WebSocket, conservando la consulta HTTP de comandos pendientes como respaldo.

Durante las pruebas reales también se detectó que la reconexión del cliente WebSocket podía bloquear el flujo principal del microcontrolador.

La solución aplicada fue mover el cliente WebSocket a una tarea independiente de FreeRTOS para evitar que problemas de reconexión afectaran la lectura del sensor y el resto del firmware.

---

## Intervención 11 — Seguridad eléctrica en dos niveles

### Iniciativa del usuario

El proyecto tenía como objetivo no solamente medir consumo, sino actuar ante condiciones eléctricas peligrosas.

### Consulta a la IA

Se analizó si el corte debía depender del backend o si debía existir también protección local.

### Propuesta de la IA

La IA recomendó utilizar dos niveles:

#### Nivel 1 — Protección local

El ESP32 evalúa directamente la corriente y puede desactivar el relé sin depender de:

- Wi-Fi;
- Internet;
- servidor;
- base de datos.

#### Nivel 2 — Protección central

El backend evalúa:

- sobrecorriente;
- sobrevoltaje;
- subvoltaje.

Además:

- registra eventos;
- bloquea dispositivos;
- genera órdenes;
- mantiene trazabilidad;
- genera notificaciones.

### Decisión final

El usuario aceptó conservar la protección local como mecanismo independiente de la red.

### Resultado

VoltGuard quedó diseñado para que una pérdida de conectividad afecte las funciones remotas, pero no elimine la protección eléctrica básica.

---

## Intervención 12 — Estado deseado y estado confirmado

### Problema identificado

Una orden generada por el servidor no garantiza que el dispositivo físico realmente haya cambiado de estado.

### Consulta y análisis de la IA

La IA recomendó distinguir:

- desired_state;
- actual_state.

También propuso utilizar confirmaciones ACK desde el ESP32.

### Decisión aplicada

Se incorporó el concepto de comando pendiente y confirmación posterior.

### Resultado

El sistema puede diferenciar entre:

el usuario pidió apagar

y:

el dispositivo confirmó que quedó apagado.

Esto mejoró la trazabilidad del control remoto.

---

## Intervención 13 — Modelo de comandos

### Necesidad identificada

El sistema necesitaba almacenar y dar seguimiento a órdenes enviadas a los dispositivos.

### Propuesta de la IA

Se propuso utilizar estados equivalentes a:

- PENDING;
- DELIVERED;
- ACKNOWLEDGED;
- FAILED;
- EXPIRED.

Además, registrar:

- dispositivo;
- acción;
- origen;
- creación;
- entrega;
- confirmación.

### Uso de la propuesta

La recomendación fue utilizada como base conceptual para construir el mecanismo de comandos y confirmaciones del backend.

### Resultado

Se consiguió una cola sencilla de comandos sin necesidad de introducir un broker externo de mensajería.

---

## Intervención 14 — Modelo de usuarios, sitios y membresías

### Iniciativa del usuario

El proyecto debía contemplar tanto usuario final como administración de múltiples dispositivos.

### Consulta a la IA

Se evaluó cómo evitar que el sistema quedara limitado a una relación simple usuario-dispositivo.

### Propuesta de la IA

Se recomendó utilizar:

User → SiteMember → Site → Device

con roles dentro de los sitios.

### Decisión aplicada

Se utilizaron conceptos como:

- usuario;
- sitio;
- miembro;
- owner;
- member;
- dispositivo.

### Resultado

La plataforma puede representar:

- un usuario con varios sitios;
- varios usuarios dentro de un mismo sitio;
- varios dispositivos en cada sitio;
- permisos diferentes según membresía.

---

## Intervención 15 — Funciones administrativas

### Iniciativa del usuario

A partir de la retroalimentación externa se decidió que debía existir un administrador de la solución.

### Consulta a la IA

Se pidió definir qué responsabilidades debía tener esa superficie.

### Propuesta de la IA

Se recomendó incluir:

- CRUD de usuarios;
- CRUD de sitios;
- CRUD de dispositivos;
- perfiles de seguridad;
- asignación de dispositivos;
- membresías;
- tarifas;
- métricas globales;
- eventos;
- anomalías.

### Resultado

Se estableció una superficie administrativa separada de la experiencia del usuario final.

---

## Intervención 16 — Soporte temporal de administradores

### Problema identificado durante el uso

Era necesario que un administrador pudiera ingresar temporalmente a un sitio de otra persona para revisar problemas sin convertirse en propietario.

### Análisis realizado

Se determinó que reutilizar la misma relación de membresía era más coherente que crear permisos especiales fuera del modelo existente.

### Decisión aplicada

El administrador puede agregarse temporalmente como member, nunca como owner.

### Resultado

Se agregó un flujo explícito de soporte temporal manteniendo visible quién es el propietario real del sitio.

---

## Intervención 17 — Eliminación segura de usuarios

### Problema identificado

Eliminar un usuario podía dejar sitios activos sin propietario.

### Análisis

Se consideró que ejecutar directamente la eliminación producía un riesgo de inconsistencia operativa.

### Solución propuesta y aplicada

Antes de borrar se calcula el impacto de la operación:

- sitios que quedarían sin dueño;
- dispositivos asociados;
- posibilidad de eliminar también sitios huérfanos.

### Resultado

La acción destructiva se volvió informada y explícita en lugar de ejecutarse sin conocer sus consecuencias.

---

## Intervención 18 — Aplicación móvil

### Iniciativa del usuario

El usuario indicó que VoltGuard debía contar con una aplicación móvil desde donde monitorear y controlar los dispositivos IoT.

### Consulta realizada a la IA

Se analizó la función que debía cumplir la aplicación dentro de la arquitectura.

### Propuesta de la IA

Se recomendó que la aplicación:

- nunca se conectara directamente al ESP32;
- consumiera la misma API del backend;
- mostrara sitios y dispositivos;
- mostrara telemetría;
- permitiera ON/OFF;
- mostrara estados pendientes y confirmados;
- mostrara eventos;
- mostrara notificaciones;
- mostrara histórico;
- mostrara predicción y costos.

### Decisión aplicada

La aplicación móvil se construyó sobre el mismo contrato utilizado por el sistema web.

### Resultado

El usuario final obtuvo una interfaz móvil centralizada para controlar y supervisar VoltGuard.

---

## Intervención 19 — Dashboard web

### Necesidad del proyecto

Además de la aplicación móvil, era necesario disponer de una interfaz web para usuarios y administración.

### Propuesta y análisis de IA

Se recomendó reutilizar las mismas APIs del backend y mantener la lógica de autorización en servidor.

También se recomendó generar los tipos del frontend a partir de OpenAPI para reducir inconsistencias entre backend y clientes.

### Resultado

El dashboard permitió:

- gestión de sitios;
- gestión de dispositivos;
- gestión administrativa;
- visualización de métricas;
- control remoto;
- histórico;
- predicciones;
- eventos;
- notificaciones.

---

## Intervención 20 — Notificaciones

### Iniciativa del usuario

Dentro de las observaciones iniciales se indicó que el sistema debía considerar envío de emails o notificaciones.

### Consulta a la IA

Se analizó cómo evitar que la generación de una notificación bloqueara la recepción de telemetría.

### Propuesta de la IA

Se recomendó separar:

evento → registro persistente → procesamiento de notificación

en lugar de ejecutar servicios externos directamente dentro del request de telemetría.

### Resultado

Se incorporó una capa persistente de notificaciones y comunicación en tiempo real hacia los clientes conectados.

---

## Intervención 21 — Predicción de consumo

### Requisito del proyecto

La propuesta original exigía estimar consumo y costo mensual.

### Consulta a la IA

Se solicitó definir qué tipo de modelo utilizar.

### Propuesta de la IA

Se recomendó comenzar con modelos simples y explicables antes de usar alternativas más complejas.

Se plantearon opciones como:

- baseline;
- regresión;
- tendencia lineal;
- Exponential Smoothing.

También se recomendó evaluar con:

- MAE;
- RMSE;
- MAPE.

### Decisión aplicada

Se priorizó una tendencia simple y explicable.

### Resultado

El sistema obtuvo capacidad de proyectar consumo y costo sin introducir complejidad innecesaria.

---

## Intervención 22 — Detección de anomalías

### Necesidad del proyecto

Además de detectar condiciones eléctricas críticas, se buscaba identificar comportamientos de consumo inusuales.

### Consulta a la IA

Se evaluaron alternativas de detección.

### Propuesta de la IA

Se recomendó separar anomalías de seguridad eléctrica.

Se plantearon:

- z-score;
- Isolation Forest.

La IA también señaló que detectar una anomalía no debía provocar automáticamente un corte de energía salvo que además se violara una regla de seguridad.

### Decisión aplicada

Se mantuvieron ambos conceptos independientes:

- reglas críticas;
- anomalías de consumo.

### Resultado

El sistema puede informar comportamiento anormal sin convertir cualquier desviación estadística en una acción física de corte.

---

## Intervención 23 — Calidad y pruebas automatizadas

### Iniciativa del proyecto

La propuesta requería:

- Ruff;
- Mypy;
- Pytest;
- cobertura igual o superior al 80 %;
- CI/CD.

### Aporte de la IA

Se recomendó utilizar las pruebas como condición obligatoria antes de cada avance importante y conservar el límite de cobertura en lugar de reducirlo para hacer pasar el pipeline.

### Resultado

La versión documentada llegó a una batería de 110 pruebas con aproximadamente 94 % de cobertura.

Las pruebas abarcaron:

- autenticación;
- reglas de seguridad;
- consumo;
- costos;
- predicción;
- anomalías;
- WebSocket;
- notificaciones;
- CRUD administrativos.

---

## Intervención 24 — Despliegue

### Necesidad del proyecto

La plataforma debía poder ejecutarse en un servidor real.

### Consulta a la IA

Se analizaron opciones para evitar una infraestructura innecesariamente compleja.

### Recomendación de la IA

Mantener una solución basada en:

- Docker Compose;
- PostgreSQL;
- FastAPI;
- proxy inverso;
- TLS.

Evitar inicialmente:

- Kubernetes;
- Kafka;
- arquitecturas de microservicios innecesarias.

### Decisión aplicada

La infraestructura se mantuvo relativamente sencilla y reproducible.

### Resultado

La plataforma puede desplegarse sobre un servidor Linux sin depender obligatoriamente de un proveedor cloud concreto.

---

## Intervención 25 — Documentación técnica del sistema

### Iniciativa del usuario

Una vez integrado el sistema, se solicitó apoyo para elaborar:

- conclusiones;
- trabajo futuro;
- justificación;
- impacto del proyecto;
- explicación de la arquitectura;
- material para presentación.

### Aporte de la IA

La IA ayudó a estructurar las conclusiones alrededor de los resultados reales del proyecto:

- separación hardware/software;
- backend como punto central;
- protección local independiente;
- modelo multiusuario;
- aplicaciones web y móvil;
- confirmación del estado real mediante ACK;
- tolerancia a fallos mediante REST + WebSocket;
- análisis de consumo;
- pruebas automatizadas;
- posibilidad de crecimiento futuro.

También se propusieron líneas de trabajo futuro relacionadas con:

- OTA;
- validación TLS en firmware;
- almacenamiento persistente de eventos críticos;
- mayor robustez del protocolo;
- rate limiting;
- notificaciones adicionales;
- soporte iOS;
- pruebas de larga duración;
- pruebas de carga;
- validación HIL.

### Decisión del usuario

El usuario solicitó que el reporte enfatizara no solamente qué tecnologías se utilizaron, sino por qué su integración era útil y qué impacto aportaba VoltGuard.

### Resultado

La documentación final presentó VoltGuard como una plataforma IoT completa y no únicamente como un circuito de medición.

---

## Intervención 26 — Rediseño visual de tarjetas de sitios y dispositivos

### Iniciativa del usuario

Se pidió cambiar la estética de las tarjetas a un estilo claro con efecto de desenfoque (no
oscuro), con un brillo de esquina cuyo color dependiera del estado del dispositivo, aplicado de
forma consistente en todas las vistas del dashboard y de la app móvil.

### Resultado y corrección aplicada

El primer intento se hizo en tema oscuro y fue rechazado explícitamente antes de continuar. Las
rondas siguientes de corrección no fueron de diseño sino de causa raíz real: varias reglas CSS
genéricas (por ejemplo selectores de lista aplicados a cualquier `<a>`/`<li>`) le ganaban en
especificidad a las clases de la tarjeta por orden de aparición en la hoja de estilos. Se corrigió
subiendo la especificidad de los selectores correctos, verificado inspeccionando directamente el
DOM renderizado antes y después del cambio.

---

## Intervención 27 — Visibilidad de soporte de administración en la interfaz

### Iniciativa del usuario

Se pidió que un administrador pudiera vincularse temporalmente a un sitio de otro usuario para dar
soporte, que quedara visible quién es el dueño real de cada sitio, y que la propia persona
administradora pudiera ver y salir de ese vínculo temporal con un solo botón — tanto desde el
panel de administración como desde la vista normal de "Mis sitios".

### Resultado

Columna "Soporte" en el panel de sitios del administrador con una insignia cuando ya está
vinculado, botón "Vincularme temporalmente para dar soporte" (el rol siempre queda como `member`,
nunca `owner`), y en "Mis sitios" un chip informativo ("Dueño" / "Soporte temporal" / "Invitado de
{email}") con un botón de autodesvinculación.

### Corrección aplicada

Para el indicador visual se evaluó una librería de "chips"; se descartó porque en realidad era un
componente de entrada de etiquetas dependiente de un paquete abandonado, no un indicador visual.
Se pidió explícitamente no sobrediseñar la solución y reutilizar el estilo de etiqueta ya existente
en vez de sumar una dependencia nueva para algo tan puntual.

---

## Intervención 28 — Flujo de borrado seguro de usuario en la interfaz

### Iniciativa del usuario

Se pidió decidir y mostrar en la interfaz qué pasa con los sitios y dispositivos de un usuario al
borrarlo, en vez de ejecutar el borrado sin más contexto.

### Resultado

Antes de confirmar, la interfaz muestra una vista previa de los sitios que quedarían sin dueño, con
una casilla para borrarlos también (solo disponible cuando el usuario es dueño único de ese sitio)
y un aviso de que la operación no es reversible y que el dispositivo tendría que vincularse
después a otro sitio. El comportamiento exacto fue especificado por el usuario en la respuesta a
la pregunta de diseño planteada, y se implementó tal cual se describió.

---

## Intervención 29 — Modales de confirmación y notificaciones globales

### Iniciativa del usuario

Se pidió reemplazar las confirmaciones de borrado embebidas en la tabla (se veían superpuestas con
otros elementos) por modales reales, y los mensajes de error/éxito embebidos por notificaciones
globales.

### Resultado

Modal real con Radix UI Dialog en el panel web (la app móvil no se migró porque no tenía el mismo
problema de superposición) y notificaciones tipo toast (`react-hot-toast`) en panel web y app
móvil.

### Corrección aplicada

Al integrar las notificaciones se encontró un bug preexistente no relacionado con el pedido
original: el interceptor de peticiones redirigía a la pantalla de login ante cualquier respuesta
401, incluida la del propio login fallido — eso recargaba la página antes de que cualquier mensaje
de error pudiera mostrarse en pantalla. Se corrigió excluyendo la petición de login de esa
redirección.

---

## Intervención 30 — Control rápido de encendido/apagado con estado en vivo

### Iniciativa del usuario

Se pidió un botón de encendido/apagado directo en la tarjeta del dispositivo, reutilizando la
mutación ya existente en vez de crear una nueva.

### Corrección aplicada

Tras la primera versión, se reportó que el estado mostrado en la tarjeta quedaba lento o
desacoplado del estado real del dispositivo después de tocar el botón. Se agregó sondeo periódico
del estado y un estado transicional visible ("Cambiando...") que solo se limpia cuando el estado
real confirmado por el dispositivo coincide con lo pedido, en vez de asumir éxito apenas se hace
clic.

---

## Intervención 31 — Exposición temporal del backend para pruebas móviles

### Iniciativa del usuario

Se pidió poder probar la app móvil contra el backend local desde un celular fuera de la red local,
sin exponer el puerto de forma permanente y sin tener que recompilar el APK cada vez que cambiara
la URL del túnel.

### Resultado

Túnel de Cloudflare (Quick Tunnel, sin necesidad de cuenta) más una URL de backend configurable en
tiempo de ejecución guardada en `localStorage`, con un panel oculto en la app (se activa tocando
cinco veces el ícono en la pantalla de login) marcado explícitamente como "solo para demo".

### Corrección aplicada

En el camino aparecieron dos problemas reales no anticipados en el pedido original: un error 502
del túnel resultó ser Docker Desktop detenido, no un problema de configuración del túnel en sí; y
una conclusión inicial de "no hay JDK ni Android SDK instalado en esta máquina" fue corregida
directamente por el usuario ("ya se habían hecho instalaciones del APK en esta sesión, debe estar
en el disco R") — la búsqueda inicial solo había cubierto el disco C:.

---

## Intervención 32 — Documentación de la arquitectura final y su organización modular

### Iniciativa del usuario

Se pidió que el README incluyera un diagrama de la arquitectura completa, mostrando cada parte del
sistema, qué función cumple y cómo se comunica con las demás.

### Resultado

Diagrama Mermaid (`flowchart`) agregado al README con un subgrafo por componente:

- **`ino/` (firmware):** sensor PZEM-004T → microcontrolador ESP32-C3 → relé. El corte crítico por
  sobrecarga se evalúa y ejecuta ahí mismo, sin depender de la red ni del servidor.
- **`backend-server/` (servidor):** API FastAPI, base de datos PostgreSQL y el motor de reglas de
  seguridad/predicción/anomalías, como único punto que conoce el estado completo del sistema.
- **Clientes de usuario:** `front/` (panel web) y `mobile/` (app Android), ambos hablándole
  únicamente al servidor por REST y WebSocket, nunca directo al dispositivo.
- **`IA-Assistant/` (asistente de voz):** módulo aparte y opcional que reutiliza la misma API y los
  mismos permisos que ya usan panel web y app móvil.

Esto documenta explícitamente la decisión de arquitectura que atraviesa todo el proyecto: cada
carpeta del monorepo es un módulo independiente con su propio conjunto de dependencias
(`backend-server/`, `front/`, `mobile/`, `ino/`, `IA-Assistant/`, `infra/`), y el único contrato
compartido entre todos ellos es la API HTTP/WebSocket que expone el servidor — lo que permite que
cualquier cliente cambie por completo, o que el asistente de voz se agregue o se quite, sin tocar
el resto del sistema.

### Corrección aplicada

El usuario editó después el diagrama directamente para separar el asistente de voz en su propio
recuadro, pero reutilizó el mismo identificador de subgrafo (`clients`) para dos bloques distintos
— Mermaid exige identificadores únicos, así que el segundo bloque no renderizaba bien. Se corrigió
dándole un identificador propio (`assistant`) al bloque del asistente, sin tocar el resto del
diagrama.

---

## Intervención 33 — Diagnóstico y corrección de telemetría con timestamp inválido

### Iniciativa del usuario

Se pidió revisar el backend porque la gráfica de consumo dejó de verse bien de un momento a otro.

### Resultado

Se determinó que, al reiniciarse, el ESP32 manda telemetría real antes de terminar de sincronizar
su reloj por NTP, con el timestamp en época cero (1970-01-01); esos puntos intercalados en medio de
la serie real rompían el eje de tiempo de la gráfica. Se corrigieron 72 registros históricos ya
afectados directamente en la base de datos, y se agregó una validación en el servidor: un timestamp
de dispositivo implausible se reemplaza por la hora de recepción del propio servidor al guardar la
lectura.

### Corrección aplicada

La instrucción explícita del usuario fue "quien debe graficar es server, si los datos llegan mal
pone la hora de recibido, no nos fiamos de la ESP" — confirmando el criterio de no confiar nunca en
el reloj del dispositivo, en vez de, por ejemplo, intentar resolverlo desde el firmware.

---

## Intervención 34 — Mayor resolución en la gráfica de consumo

### Iniciativa del usuario

Se pidió agregar más resolución a la vista "Hoy" de la gráfica de consumo, que se veía "muy
espaciada" al agrupar únicamente por hora.

### Resultado

Nueva granularidad por minuto en el backend, expuesta en el mismo endpoint de consumo, con una
pestaña nueva "Hoy (min)" en panel web y app móvil, y pruebas automatizadas nuevas para cubrirla.

### Corrección aplicada

Al probarlo, la vista por hora mostraba datos pero la de minuto no mostraba nada. La causa no
estaba en el código nuevo sino en que el servidor de desarrollo corre sin recarga automática, así
que seguía sirviendo la versión anterior del backend; se corrigió reiniciando el proceso para
cargar el código nuevo, verificado directamente contra la base de datos antes de dar el cambio por
resuelto.

---

## Intervención 35 — Revisión de seguridad end-to-end del historial de git

### Iniciativa del usuario

Se pidió revisar todo el historial de git en busca de secretos filtrados y, de haberlos, quitarlos
sin dañar nada.

### Resultado

No se encontró ningún secreto real filtrado — nunca se subió un `.env` real, ni claves de API, ni
credenciales de producción. Sí se encontró una contraseña de Postgres hardcodeada como texto plano
en el compose de desarrollo y en el valor por defecto de la configuración, aunque nunca fue una
credencial explotable (solo protegía un Postgres de `localhost` en modo dessarrollo, nunca expuesto). Se corrigió
siguiendo el mismo patrón ya usado en el proyecto para la clave de firma de sesión: variable de
entorno con un valor de respaldo marcado explícitamente como inseguro para desarrollo.

### Decisión final del usuario

El usuario decidió rotar el password y resolverlo hacia adelante con un
commit normal y documentado.

---

# 4. Reflexión sobre el uso de IA

La Inteligencia Artificial fue utilizada principalmente como herramienta de revisión, análisis y apoyo en la toma de decisiones.

Durante el proyecto se presentaron situaciones donde la primera propuesta de la IA no se aplicó directamente.

Un ejemplo fue la comunicación entre ESP32 y servidor. Inicialmente se propuso construir un nuevo firmware de comunicación, pero después de que el usuario proporcionó el firmware real se comprobó que gran parte de esa funcionalidad ya estaba implementada. La estrategia se modificó entonces hacia la revisión y endurecimiento del código existente.

Este comportamiento fue importante porque evitó utilizar las propuestas de IA de manera automática.

Las recomendaciones se contrastaron con:

- el código existente;
- la arquitectura del proyecto;
- mediciones sobre hardware real;
- pruebas funcionales;
- necesidades planteadas por el usuario.

La IA también permitió detectar riesgos que podían no ser visibles durante una prueba funcional básica, como:

- pérdida de telemetría;
- repetición de comandos;
- diferencias entre estado solicitado y estado real;
- problemas de idempotencia;
- dependencia excesiva de la conectividad;
- posibles bloqueos derivados de reconexiones;
- inconsistencias entre usuarios, sitios y dispositivos.

La decisión final sobre qué cambios adoptar permaneció en todo momento en manos del usuario y del equipo.

---

# 5. Principales aportes de la IA

Los aportes más importantes durante el desarrollo de software fueron:

1. estructurar el alcance completo del proyecto;
2. proponer la separación de API IoT, usuario y administrador;
3. introducir el modelo User → SiteMember → Site → Device;
4. identificar inconsistencias del repositorio original;
5. proponer una estrategia de refactorización incremental;
6. diseñar la metodología de comparación humano vs Claude Code;
7. definir pruebas simuladas y Hardware-in-the-Loop;
8. revisar la comunicación entre firmware y backend;
9. identificar posibles fallos de robustez en el firmware;
10. apoyar el diagnóstico por capas de problemas reales;
11. proponer una estrategia de comunicación REST + WebSocket;
12. apoyar la separación entre estado deseado y estado confirmado;
13. apoyar la definición del modelo de comandos;
14. apoyar la construcción de métricas, predicción y anomalías;
15. apoyar la definición de funciones administrativas;
16. apoyar la documentación, conclusiones y trabajo futuro;
17. construir de punta a punta, con Claude Code, el soporte temporal de administración, los
    modales de confirmación, las notificaciones globales y el control en vivo de encendido/apagado
    sobre la rama `experiment/voltguard-platform-v2`;
18. diagnosticar y corregir, con datos reales de producción, la telemetría con timestamp inválido
    tras un reinicio del dispositivo;
19. documentar la arquitectura final y su organización modular mediante un diagrama de
    componentes;
20. auditar el historial de git en busca de secretos filtrados y aplicar la corrección
    correspondiente.

---

# 6. Decisiones que correspondieron al usuario/equipo

Para evitar atribuir decisiones propias a la IA, se deja explícito que fueron decisiones del usuario o del equipo:

- utilizar el módulo electrónico previamente desarrollado;
- utilizar un servidor central para VoltGuard;
- incorporar una aplicación móvil;
- separar usuario final y administrador;
- partir del repositorio existente en lugar de comenzar desde cero;
- mantener una versión humana independiente;
- exigir desarrollo paso a paso con verificaciones y commits frecuentes;
- crear adicionalmente una versión autónoma con Claude Code;
- comparar ambas versiones posteriormente;
- conservar el firmware existente después de revisar su implementación real;
- validar el sistema utilizando hardware físico;
- utilizar el proyecto como solución integral de monitoreo, control y protección eléctrica;
- aceptar o rechazar las recomendaciones propuestas por la IA después de contrastarlas con el sistema real;
- definir el criterio exacto para el borrado seguro de usuarios y sitios huérfanos;
- decidir, ante un secreto de desarrollo hardcodeado encontrado en el historial, corregirlo hacia
  adelante en vez de reescribir el historial de git compartido.

---

# 7. Conclusión de la bitácora

El uso de IA en VoltGuard funcionó principalmente como un mecanismo de apoyo técnico, revisión y exploración de alternativas.

Las propuestas generadas permitieron analizar opciones con rapidez, detectar riesgos y organizar el desarrollo, pero fueron contrastadas continuamente contra el sistema real.

La participación del usuario fue determinante para aportar las restricciones reales del hardware, decidir el alcance, seleccionar qué recomendaciones aplicar, realizar las pruebas físicas y validar los resultados.

El proceso tuvo dos fases con roles distintos para la IA. Con ChatGPT, en modo asesor de solo
texto, se definió el alcance, la arquitectura y la estrategia de refactorización. Con Claude Code,
como agente con acceso directo al repositorio, se construyó la implementación real sobre la rama
`experiment/voltguard-platform-v2` — el modelo de datos, las tres superficies de API, el dashboard
web, la app móvil, el soporte de administración, y la corrección de problemas encontrados sobre
datos reales de producción (telemetría con timestamp inválido, un secreto de desarrollo
hardcodeado). En ambos casos, cada propuesta se contrastó contra el sistema real antes de
aceptarse, y varias correcciones surgieron directamente de la persona a cargo del proyecto en el
momento de revisar el resultado, no de la IA por iniciativa propia.

Por lo tanto, el resultado final no corresponde a una solución generada automáticamente por IA, sino a un proceso de desarrollo asistido donde las herramientas de Inteligencia Artificial aportaron análisis, diagnósticos y propuestas, mientras que las decisiones técnicas finales y la validación permanecieron bajo responsabilidad del usuario y del equipo.