# Despliegue reproducible de Policrafters CMS + Astro en VPS

> **Estado de esta guía:** reproduce la arquitectura que actualmente
> está funcionando.\
> **Pendiente:** automatización del rebuild/deploy de Astro al publicar
> contenido en Wagtail.

## 1. Arquitectura final

La instalación utiliza un único dominio público:

``` text
https://astro.novatierra.cloud
        |
        v
      Traefik
        |
        +-- /*               -> policrafters_astro:80
        +-- /api/*           -> policrafters_cms:8000
        +-- /admin/*         -> policrafters_cms:8000
        +-- /django-admin/*  -> policrafters_cms:8000
        +-- /documents/*     -> policrafters_cms:8000
        +-- /search/*        -> policrafters_cms:8000
        +-- /static/*        -> policrafters_cms_assets:80
        +-- /media/*         -> policrafters_cms_assets:80
```

Componentes:

-   **Astro**: frontend público estático.
-   **Django/Wagtail**: CMS, administración y APIs.
-   **PostgreSQL 16**: base de datos exclusiva del CMS.
-   **Nginx Alpine**: sirve `/static/` y `/media/` de Wagtail.
-   **Traefik**: reverse proxy y HTTPS.
-   **Docker Compose**: despliegue de CMS y frontend.

El administrador usa:

``` text
https://astro.novatierra.cloud/admin/
```

No se requiere un dominio público separado para el CMS.

------------------------------------------------------------------------

## 2. Principio de trabajo

Los cambios de código e infraestructura se hacen en el equipo local, se
versionan en GitHub y después se actualizan en el VPS.

Flujo recomendado:

``` text
Mac / desarrollo
      |
      | git push
      v
GitHub
      |
      | git pull
      v
VPS
```

Se versionan:

-   `Dockerfile`
-   `docker-compose.prod.yml`
-   `.dockerignore`
-   `.env.example`
-   configuración Django de producción
-   código Wagtail/Astro

No se versionan:

-   `.env.production`
-   `.env` de producción
-   `SECRET_KEY`
-   contraseñas
-   certificados
-   dumps
-   archivos `media` de producción

------------------------------------------------------------------------

## 3. Requisitos del VPS

Debe existir:

-   Ubuntu
-   Docker
-   Docker Compose
-   Git
-   Traefik funcionando y escuchando en puertos 80/443
-   red Docker externa `traefik_proxy`

Verificar:

``` bash
docker --version
docker compose version
docker network ls | grep traefik_proxy
docker ps
```

En esta arquitectura **no se instala Nginx directamente en Ubuntu**.
Traefik maneja 80/443 y el Nginx necesario para assets corre dentro de
Docker.

------------------------------------------------------------------------

## 4. Clonar el CMS

Ruta utilizada:

``` bash
cd /var/www
git clone URL_DEL_REPOSITORIO/policrafters-cms.git policrafters_cms
cd /var/www/policrafters_cms

git status
git branch --show-current
git remote -v
```

La rama de producción utilizada es:

``` text
main
```

------------------------------------------------------------------------

## 5. Configuración Django de producción

El proyecto utiliza:

``` text
DJANGO_SETTINGS_MODULE=policrafters_cms.settings.production
```

La configuración de producción debe incluir, entre otros:

``` python
DEBUG = False

SECRET_KEY = env("SECRET_KEY")

ALLOWED_HOSTS = [
    host.strip()
    for host in env("ALLOWED_HOSTS", default="").split(",")
    if host.strip()
]

CSRF_TRUSTED_ORIGINS = [
    origin.strip()
    for origin in env("CSRF_TRUSTED_ORIGINS", default="").split(",")
    if origin.strip()
]

CORS_ALLOWED_ORIGINS = [
    origin.strip()
    for origin in env("CORS_ALLOWED_ORIGINS", default="").split(",")
    if origin.strip()
]

CORS_ALLOW_CREDENTIALS = True

WAGTAILADMIN_BASE_URL = env(
    "WAGTAILADMIN_BASE_URL",
    default="https://astro.novatierra.cloud",
)

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

STORAGES["staticfiles"]["BACKEND"] = (
    "django.contrib.staticfiles.storage.ManifestStaticFilesStorage"
)

try:
    from .local import *
except ImportError:
    pass
```

Los paths de archivos:

``` python
STATIC_ROOT = BASE_DIR / "static"
STATIC_URL = "/static/"

MEDIA_ROOT = BASE_DIR / "media"
MEDIA_URL = "/media/"
```

------------------------------------------------------------------------

## 6. Rutas Django/Wagtail

La instalación funcional utiliza rutas equivalentes a:

``` python
urlpatterns = [
    path("django-admin/", admin.site.urls),
    path("admin/", include(wagtailadmin_urls)),
    path("documents/", include(wagtaildocs_urls)),

    path("api/home", home_page_api, name="home_page_api"),
    path("api/home/", home_page_api),

    path("api/catalogs", catalogs_index_api, name="catalogs_index_api"),
    path("api/catalogs/", catalogs_index_api),

    path("api/contact-page", contact_page_api, name="contact_page_api"),
    path("api/contact-page/", contact_page_api),

    path("api/contact-us", contact_page_api),
    path("api/contact-us/", contact_page_api),

    path("search/", search_views.search, name="search"),
]

urlpatterns += [
    path("", include(wagtail_urls)),
]
```

Actualmente están implementadas las APIs de:

-   Home
-   Catalogs
-   Contact Us

No deben considerarse obligatorias otras APIs que todavía no estén
desarrolladas.

------------------------------------------------------------------------

## 7. `.env.production` del CMS

Este archivo se crea **solamente en el VPS**:

``` bash
cd /var/www/policrafters_cms
nano .env.production
```

Contenido:

``` env
DJANGO_SETTINGS_MODULE=policrafters_cms.settings.production

DB_ENGINE=django.db.backends.postgresql
DB_NAME=policrafters_cms
DB_USER=policrafters_cms_user
DB_PASSWORD=CAMBIAR_POR_PASSWORD_SEGURA
DB_HOST=db
DB_PORT=5432

SECRET_KEY=CAMBIAR_POR_SECRET_KEY

ALLOWED_HOSTS=astro.novatierra.cloud
CSRF_TRUSTED_ORIGINS=https://astro.novatierra.cloud
CORS_ALLOWED_ORIGINS=https://astro.novatierra.cloud,https://www.astro.novatierra.cloud
WAGTAILADMIN_BASE_URL=https://astro.novatierra.cloud
```

Generar `SECRET_KEY`:

``` bash
python3 - <<'PY'
import secrets
print(secrets.token_urlsafe(64))
PY
```

Generar contraseña PostgreSQL:

``` bash
openssl rand -base64 32
```

Verificar que Git ignore los archivos de entorno:

``` gitignore
.env
.env.production
.env.*
!.env.example
```

------------------------------------------------------------------------

## 8. Docker Compose del CMS

`docker-compose.prod.yml`:

``` yaml
services:
  db:
    image: postgres:16
    container_name: policrafters_cms_db
    restart: unless-stopped

    environment:
      POSTGRES_DB: ${DB_NAME}
      POSTGRES_USER: ${DB_USER}
      POSTGRES_PASSWORD: ${DB_PASSWORD}

    volumes:
      - policrafters_cms_postgres_data:/var/lib/postgresql/data

    ports:
      - "127.0.0.1:5434:5432"

    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${DB_USER} -d ${DB_NAME}"]
      interval: 10s
      timeout: 5s
      retries: 5

    networks:
      - policrafters_cms_network

  web:
    build:
      context: .
      dockerfile: Dockerfile

    container_name: policrafters_cms
    restart: unless-stopped

    env_file:
      - .env.production

    environment:
      DJANGO_SETTINGS_MODULE: policrafters_cms.settings.production
      PORT: 8000

    command: >
      sh -c "python manage.py migrate --noinput &&
             python manage.py collectstatic --noinput &&
             gunicorn policrafters_cms.wsgi:application --bind 0.0.0.0:8000 --workers 3 --timeout 120"

    depends_on:
      db:
        condition: service_healthy

    ports:
      - "127.0.0.1:8000:8000"

    volumes:
      - static_data:/app/static
      - media_data:/app/media

    networks:
      - policrafters_cms_network
      - traefik_proxy

    labels:
      - "traefik.enable=true"
      - "traefik.docker.network=traefik_proxy"
      - "traefik.http.routers.policrafters-cms.rule=Host(`astro.novatierra.cloud`) && (PathPrefix(`/admin`) || PathPrefix(`/django-admin`) || PathPrefix(`/api`) || PathPrefix(`/documents`) || PathPrefix(`/search`))"
      - "traefik.http.routers.policrafters-cms.entrypoints=websecure"
      - "traefik.http.routers.policrafters-cms.tls=true"
      - "traefik.http.routers.policrafters-cms.tls.certresolver=mytlschallenge"
      - "traefik.http.services.policrafters-cms.loadbalancer.server.port=8000"

  assets:
    image: nginx:alpine
    container_name: policrafters_cms_assets
    restart: unless-stopped

    volumes:
      - static_data:/usr/share/nginx/html/static:ro
      - media_data:/usr/share/nginx/html/media:ro

    networks:
      - traefik_proxy

    labels:
      - "traefik.enable=true"
      - "traefik.docker.network=traefik_proxy"
      - "traefik.http.routers.policrafters-cms-assets.rule=Host(`astro.novatierra.cloud`) && (PathPrefix(`/static`) || PathPrefix(`/media`))"
      - "traefik.http.routers.policrafters-cms-assets.entrypoints=websecure"
      - "traefik.http.routers.policrafters-cms-assets.tls=true"
      - "traefik.http.routers.policrafters-cms-assets.tls.certresolver=mytlschallenge"
      - "traefik.http.services.policrafters-cms-assets.loadbalancer.server.port=80"

volumes:
  policrafters_cms_postgres_data:
  static_data:
  media_data:

networks:
  policrafters_cms_network:
    driver: bridge

  traefik_proxy:
    external: true
```

### Importante

Nunca ejecutar en producción:

``` bash
docker compose down -v
```

`-v` puede eliminar los volúmenes persistentes, incluida la base de
datos.

------------------------------------------------------------------------

## 9. Validar y levantar el CMS

Validar Compose:

``` bash
cd /var/www/policrafters_cms

docker compose \
  -f docker-compose.prod.yml \
  --env-file .env.production \
  config
```

La salida puede contener secretos. No copiarla en tickets, commits o
documentación pública.

Construir:

``` bash
docker compose \
  -f docker-compose.prod.yml \
  --env-file .env.production \
  build
```

Levantar:

``` bash
docker compose \
  -f docker-compose.prod.yml \
  --env-file .env.production \
  up -d
```

Verificar:

``` bash
docker compose \
  -f docker-compose.prod.yml \
  --env-file .env.production \
  ps
```

Deben aparecer:

``` text
policrafters_cms
policrafters_cms_db
policrafters_cms_assets
```

------------------------------------------------------------------------

## 10. Verificar PostgreSQL

Logs:

``` bash
docker logs policrafters_cms_db
```

Conectarse:

``` bash
docker exec -it policrafters_cms_db \
  psql -U policrafters_cms_user -d policrafters_cms
```

Dentro de PostgreSQL:

``` sql
\dt
\q
```

Django se conecta internamente a:

``` text
db:5432
```

El puerto:

``` text
127.0.0.1:5434
```

es solamente para administración desde el host/túnel SSH.

------------------------------------------------------------------------

## 11. Migraciones y superusuario

El comando de arranque ya ejecuta:

``` bash
python manage.py migrate --noinput
python manage.py collectstatic --noinput
```

Comprobar migraciones:

``` bash
docker exec -it policrafters_cms python manage.py showmigrations
```

Crear superusuario:

``` bash
docker exec -it policrafters_cms python manage.py createsuperuser
```

Ver logs:

``` bash
docker logs -f policrafters_cms
```

------------------------------------------------------------------------

## 12. Verificaciones del CMS antes del frontend

Desde el VPS:

``` bash
curl -I http://127.0.0.1:8000/admin/
```

Desde Internet:

``` bash
curl -I https://astro.novatierra.cloud/admin/
curl -I https://astro.novatierra.cloud/static/wagtailadmin/css/core.css
curl -I https://astro.novatierra.cloud/api/home/
```

Resultados esperados:

-   `/admin/` redirige al login de Wagtail.
-   `/static/...` responde `200`.
-   `/api/home/` responde JSON.
-   `/media/...` debe poder servir imágenes subidas desde Wagtail.

Ejemplo de URL válida de media:

``` text
https://astro.novatierra.cloud/media/original_images/logo_black.png
```

------------------------------------------------------------------------

## 13. Frontend Astro

Ruta utilizada en el VPS:

``` text
/var/www/policrafters_web
```

Clonar:

``` bash
cd /var/www
git clone URL_DEL_REPOSITORIO/policrafters-web.git policrafters_web
cd /var/www/policrafters_web
```

El frontend actual es **Astro estático**.

El Dockerfile actual sirve un `dist/` ya construido:

``` dockerfile
FROM nginx:alpine

COPY dist/ /usr/share/nginx/html/

EXPOSE 80
```

Por tanto, el build de Astro se realiza antes del build Docker.

------------------------------------------------------------------------

## 14. Docker Compose del frontend

``` yaml
services:
  astro:
    build: .
    container_name: policrafters_astro
    restart: unless-stopped

    networks:
      - traefik_proxy

    labels:
      - traefik.enable=true
      - traefik.docker.network=traefik_proxy
      - traefik.http.routers.policrafters.rule=Host(`astro.novatierra.cloud`)
      - traefik.http.routers.policrafters.entrypoints=websecure
      - traefik.http.routers.policrafters.tls=true
      - traefik.http.routers.policrafters.tls.certresolver=mytlschallenge
      - traefik.http.services.policrafters.loadbalancer.server.port=80

networks:
  traefik_proxy:
    external: true
```

El router general de Astro recibe `/*`, mientras que los routers más
específicos del CMS reciben `/api`, `/admin`, `/static`, etc.

------------------------------------------------------------------------

## 15. Variables de entorno del frontend

Actualmente se usa un `.env` en el VPS.

### Para consumir Wagtail

``` env
PUBLIC_USE_API=true
PUBLIC_API_URL=https://astro.novatierra.cloud/api/home/
PUBLIC_CATALOGS_API_URL=https://astro.novatierra.cloud/api/catalogs/
PUBLIC_CONTACT_PAGE_API_URL=https://astro.novatierra.cloud/api/contact-us/
```

### Para trabajar con mocks

``` env
PUBLIC_USE_API=false
PUBLIC_API_URL=https://astro.novatierra.cloud/api/home/
PUBLIC_CATALOGS_API_URL=https://astro.novatierra.cloud/api/catalogs/
PUBLIC_CONTACT_PAGE_API_URL=https://astro.novatierra.cloud/api/contact-us/
```

`PUBLIC_USE_API=false` debe impedir que Home consulte el CMS incluso si
`PUBLIC_API_URL` existe.

En `index.astro` se corrigió la lógica para transmitir explícitamente
esta decisión al navegador:

``` astro
<body
    data-api-url={apiUrl}
    data-use-api={useApi ? "true" : "false"}
>
```

Y el JavaScript usa:

``` javascript
const body = document.body;
const apiUrl = body?.dataset?.apiUrl || '';
const shouldUseCms =
    body?.dataset?.useApi === 'true' && Boolean(apiUrl);
```

Así:

``` text
PUBLIC_USE_API=false -> mocks EN/ES
PUBLIC_USE_API=true  -> Wagtail API
```

------------------------------------------------------------------------

## 16. Build y despliegue manual de Astro

Actualizar código:

``` bash
cd /var/www/policrafters_web
git status
git pull origin main
```

Instalar dependencias si es necesario:

``` bash
npm ci
```

Construir:

``` bash
npm run build
```

Comprobar que existe:

``` bash
stat dist/index.html
```

Desplegar:

``` bash
docker compose up -d --build astro
```

Verificar:

``` bash
docker ps --filter name=policrafters_astro
```

Abrir:

``` text
https://astro.novatierra.cloud
```

------------------------------------------------------------------------

## 17. Comportamiento actual de Wagtail -\> Astro

Este punto es fundamental.

Astro actualmente genera HTML estático. Cuando:

``` env
PUBLIC_USE_API=true
```

Astro consulta las APIs de Wagtail **durante el build**.

El flujo actual es:

``` text
Wagtail
   |
   | API
   v
npm run build
   |
   v
dist/
   |
   v
docker compose up -d --build astro
   |
   v
Nginx
   |
   v
Sitio público
```

Por tanto, publicar una modificación en Wagtail actualiza inmediatamente
la API, pero **no modifica automáticamente el HTML estático que ya está
desplegado**.

Para reflejar un Publish actualmente hay que ejecutar:

``` bash
cd /var/www/policrafters_web
npm run build
docker compose up -d --build astro
```

Esto fue comprobado funcionando correctamente.

------------------------------------------------------------------------

## 18. Prueba recomendada de integración

1.  Entrar a:

``` text
https://astro.novatierra.cloud/admin/
```

2.  Modificar un texto de Home.
3.  Publicar.
4.  Verificar la API:

``` bash
curl https://astro.novatierra.cloud/api/home/
```

5.  Confirmar que el JSON ya contiene el cambio.
6.  En el VPS:

``` bash
cd /var/www/policrafters_web
npm run build
```

7.  Verificar el contenido generado en `dist/index.html`.
8.  Desplegar:

``` bash
docker compose up -d --build astro
```

9.  Recargar el sitio público.

Si aparece el contenido nuevo, la cadena completa está funcionando:

``` text
Wagtail -> API -> Astro build -> dist -> Nginx -> Traefik -> Internet
```

------------------------------------------------------------------------

## 19. Persistencia de media y static

El contenedor Wagtail y el contenedor `assets` comparten:

``` yaml
static_data
media_data
```

Wagtail escribe:

``` text
/app/static
/app/media
```

Nginx assets lee los mismos volúmenes en:

``` text
/usr/share/nginx/html/static
/usr/share/nginx/html/media
```

Esto permite que una imagen cargada desde Wagtail quede disponible
públicamente bajo:

``` text
/media/...
```

Los archivos de `media` no deben guardarse dentro de la imagen Docker.

------------------------------------------------------------------------

## 20. Actualizaciones posteriores del CMS

Flujo habitual:

``` bash
cd /var/www/policrafters_cms

git status
git pull origin main

docker compose \
  -f docker-compose.prod.yml \
  --env-file .env.production \
  up -d --build
```

Después:

``` bash
docker compose \
  -f docker-compose.prod.yml \
  --env-file .env.production \
  ps

docker logs --tail 100 policrafters_cms
```

Como el arranque ejecuta migraciones y `collectstatic`, ambos procesos
se aplican automáticamente.

------------------------------------------------------------------------

## 21. Comandos de diagnóstico

### Contenedores

``` bash
docker ps
```

### Logs CMS

``` bash
docker logs --tail 200 policrafters_cms
```

### Logs PostgreSQL

``` bash
docker logs --tail 200 policrafters_cms_db
```

### Redes

``` bash
docker network inspect traefik_proxy
```

### Variables visibles dentro del CMS

No imprimir secretos innecesariamente. Para verificar valores concretos:

``` bash
docker exec policrafters_cms printenv DJANGO_SETTINGS_MODULE
docker exec policrafters_cms printenv DB_HOST
docker exec policrafters_cms printenv DB_PORT
```

### API

``` bash
curl -s https://astro.novatierra.cloud/api/home/
```

### Assets

``` bash
curl -I https://astro.novatierra.cloud/static/wagtailadmin/css/core.css
curl -I https://astro.novatierra.cloud/media/RUTA_DE_IMAGEN
```

------------------------------------------------------------------------

## 22. Errores encontrados durante la primera instalación

### `ModuleNotFoundError: wagtail_localize`

La dependencia debe estar incluida en las dependencias Python del
proyecto antes de reconstruir la imagen.

### Errores `--bind`, `--workers` o `--timeout not found`

El comando Gunicorn debe formar una única instrucción shell válida. La
versión funcional es:

``` yaml
command: >
  sh -c "python manage.py migrate --noinput &&
         python manage.py collectstatic --noinput &&
         gunicorn policrafters_cms.wsgi:application --bind 0.0.0.0:8000 --workers 3 --timeout 120"
```

### Admin sin estilos

Django/Gunicorn no es el encargado final de servir los assets en esta
arquitectura.

La solución utilizada es:

``` text
/static/* -> policrafters_cms_assets
/media/*  -> policrafters_cms_assets
```

con volúmenes compartidos.

### URLs de media con HTTP en lugar de HTTPS

Como Traefik termina TLS y Django recibe tráfico interno HTTP, Django
debe conocer el protocolo original:

``` python
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
```

------------------------------------------------------------------------

## 23. Lo que NO debe hacerse

-   No instalar otro Nginx en el host para esta arquitectura.
-   No exponer PostgreSQL públicamente.
-   No poner secretos en GitHub.
-   No modificar permanentemente Compose solo en el VPS.
-   No ejecutar `docker compose down -v`.
-   No conectar Django a `127.0.0.1:5434`; dentro de Docker debe usar
    `db:5432`.
-   No esperar que un Publish de Wagtail regenere por sí solo un sitio
    Astro estático mientras la automatización no esté implementada.
-   No montar `/var/run/docker.sock` dentro del contenedor Django solo
    para permitir que Wagtail despliegue el frontend.

------------------------------------------------------------------------

## 24. Pendiente: automatización de Publish

La instalación descrita hasta aquí es la versión actualmente funcional.

El siguiente componente pendiente es:

``` text
Editor publica en Wagtail
          |
          v
evento page_published
          |
          v
trigger seguro en el VPS
          |
          v
rebuild Astro
          |
          v
deploy policrafters_astro
          |
          v
sitio actualizado automáticamente
```

La opción prevista es mantener Docker fuera del contenedor Django y
utilizar un mecanismo host-local controlado, por ejemplo:

``` text
Wagtail page_published
        |
        v
archivo/señal de trigger
        |
        v
systemd.path
        |
        v
systemd service
        |
        v
script fijo de deploy
```

El script ejecutaría conceptualmente:

``` bash
cd /var/www/policrafters_web
npm run build
docker compose up -d --build astro
```

Se deberá añadir:

-   bloqueo (`flock`) para evitar builds simultáneos;
-   debounce para múltiples publicaciones cercanas;
-   logs;
-   manejo de errores;
-   una estrategia segura de preview de borradores.

**Esta automatización no forma parte todavía de la instalación
reproducible documentada aquí.**

------------------------------------------------------------------------

## 25. Checklist para replicar en otro VPS

-   [ ] Docker y Docker Compose instalados.
-   [ ] Traefik activo en 80/443.
-   [ ] Red `traefik_proxy` creada.
-   [ ] DNS del dominio apuntando al VPS.
-   [ ] Repositorio CMS clonado en `/var/www/policrafters_cms`.
-   [ ] `.env.production` creado únicamente en el VPS.
-   [ ] PostgreSQL CMS levantado.
-   [ ] Migraciones aplicadas.
-   [ ] Superusuario creado.
-   [ ] `policrafters_cms` funcionando.
-   [ ] `policrafters_cms_assets` funcionando.
-   [ ] `/admin/` accesible por HTTPS.
-   [ ] `/static/` accesible.
-   [ ] `/media/` accesible.
-   [ ] `/api/home/` accesible.
-   [ ] Repositorio Astro clonado en `/var/www/policrafters_web`.
-   [ ] `.env` de frontend configurado.
-   [ ] `npm ci` ejecutado.
-   [ ] `npm run build` completado.
-   [ ] `policrafters_astro` desplegado.
-   [ ] Home público funcionando.
-   [ ] Imagen subida desde Wagtail visible por `/media/`.
-   [ ] Cambio publicado en Wagtail comprobado vía API.
-   [ ] Rebuild manual de Astro comprobado.
-   [ ] Automatización de Publish marcada como pendiente.

------------------------------------------------------------------------

## 26. Resultado esperado

Al terminar, el nuevo VPS debe presentar:

``` text
Internet
   |
   v
Traefik :443
   |
   +-- astro.novatierra.cloud/
   |      -> Astro / Nginx
   |
   +-- astro.novatierra.cloud/admin/
   |      -> Django / Wagtail
   |
   +-- astro.novatierra.cloud/api/
   |      -> Django APIs
   |
   +-- astro.novatierra.cloud/static/
   |      -> Nginx assets
   |
   +-- astro.novatierra.cloud/media/
          -> Nginx assets

Django
   |
   v
PostgreSQL 16
```

Con esto queda reproducida la instalación funcional actual. El único
paso de infraestructura funcional pendiente es automatizar el
rebuild/deploy de Astro después de un **Publish** en Wagtail.

## 27. Actualizacion del cms
1. Entrar al VPS y ubicarse en el CMS
cd /var/www/policrafters_cms

Antes de actualizar, verifica que no existan modificaciones hechas directamente en producción:

git status

Lo ideal es que aparezca algo equivalente a:

On branch main
Your branch is up to date with 'origin/main'.

nothing to commit, working tree clean

El manual establece precisamente que el flujo debe ser desarrollo local → GitHub → VPS, evitando cambios permanentes directamente en producción.

2. Confirmar que estás en main
git branch --show-current

Debe responder:

main

La rama definida en el manual para producción es main.

3. Descargar la nueva versión
git pull origin main

Aquí ya queda actualizado el código fuente en:

/var/www/policrafters_cms

Pero todavía no has actualizado el contenedor que está ejecutándose.

4. Reconstruir y actualizar los contenedores

Ejecuta exactamente:

docker compose \
  -f docker-compose.prod.yml \
  --env-file .env.production \
  up -d --build
Además, no necesitas ejecutar manualmente migrate ni collectstatic, porque el docker-compose.prod.yml ya arranca el CMS con:

python manage.py migrate --noinput &&
python manage.py collectstatic --noinput &&
gunicorn policrafters_cms.wsgi:application ...

Por eso las nuevas migraciones y los archivos estáticos se procesan automáticamente durante el arranque.

5. Verificar los contenedores

Después de la reconstrucción:

docker compose \
  -f docker-compose.prod.yml \
  --env-file .env.production \
  ps

Deberías tener funcionando:

policrafters_cms
policrafters_cms_db
policrafters_cms_assets

Esos son los tres servicios previstos por la instalación.

6. Revisar los logs del CMS
docker logs --tail 100 policrafters_cms

Aquí debes comprobar especialmente que no existan errores de:

migrate
collectstatic
gunicorn
ModuleNotFoundError
database connection

El manual recomienda precisamente revisar estos logs después de actualizar.

7. Verificar que Wagtail siga respondiendo

Puedes comprobarlo directamente:

curl -I https://astro.novatierra.cloud/admin/

Y la API:

curl -I https://astro.novatierra.cloud/api/home/

Los resultados esperados son que /admin/ redirija al login de Wagtail y /api/home/ responda correctamente.

Por tanto, para una actualización normal del código del CMS, tu rutina práctica se reduce a:

cd /var/www/policrafters_cms

git status
git branch --show-current
git pull origin main

docker compose \
  -f docker-compose.prod.yml \
  --env-file .env.production \
  up -d --build

docker compose \
  -f docker-compose.prod.yml \
  --env-file .env.production \
  ps

docker logs --tail 100 policrafters_cms

Hay algo importante: no debes ejecutar docker compose down -v. El manual advierte que -v puede eliminar los volúmenes persistentes, incluyendo la base de datos PostgreSQL.

Y tampoco tienes que tocar .env.production: ese archivo permanece en el VPS y no se trae de GitHub porque contiene los secretos de producción.

En resumen: para los cambios que estás haciendo ahora en policrafters_cms, una vez que estén en main de GitHub, el ciclo es git pull → docker compose up -d --build → verificar ps → revisar logs. La base de datos y los media existentes se conservan porque están en volúmenes persistentes.