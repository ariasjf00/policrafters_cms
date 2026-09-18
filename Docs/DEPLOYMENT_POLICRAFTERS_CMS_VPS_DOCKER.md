# Deployment de `policrafters_cms` en VPS Hostinger con Docker

Esta guía describe el despliegue de **`policrafters_cms`**, backend
Django/Wagtail de Policrafters, en el VPS de Hostinger.

La arquitectura definida es:

``` text
Internet
   │
   ├── policrafters_web
   │      Frontend
   │          │
   │          │ HTTP / API
   │          ▼
   └── policrafters_cms
          Django / Wagtail
               │
               ▼
        policrafters_cms_db
          PostgreSQL 16
```

`policrafters_web` es el frontend y **no tiene base de datos propia**.\
`policrafters_cms` tendrá su propio contenedor PostgreSQL, independiente
de `geqc26_db`, `gamy_db` y del PostgreSQL instalado directamente en
Ubuntu.

> Estado actual: el repositorio `policrafters_cms` ya fue clonado desde
> GitHub en el VPS. Por tanto, esta guía continúa desde ese punto.

------------------------------------------------------------------------

## 1. Principio de despliegue

Los archivos que definen la infraestructura deben crearse **en el
repositorio local de desarrollo**, probarse y subirse a GitHub.

Se deben versionar:

-   `Dockerfile`
-   `docker-compose.prod.yml`
-   `.dockerignore`
-   `.env.example`
-   configuración de producción de Django que no contenga secretos
-   scripts de despliegue, si se crean

No se debe versionar:

-   `.env.production`
-   contraseñas
-   `SECRET_KEY`
-   certificados
-   dumps de PostgreSQL
-   archivos `media` generados en producción

Esto evita modificar manualmente `docker-compose.prod.yml` en el VPS y
reduce conflictos posteriores al ejecutar `git pull`.

------------------------------------------------------------------------

## 2. Verificar el repositorio ya clonado en el VPS

``` bash
cd /var/www/policrafters_cms
git status
git branch --show-current
git remote -v
```

La rama de producción esperada es:

``` text
main
```

Si el directorio real tiene otro nombre, usar ese nombre de forma
consistente en todos los comandos de esta guía.

------------------------------------------------------------------------

## 3. Crear los archivos Docker LOCALMENTE

Los siguientes archivos deben crearse primero en el Mac/equipo de
desarrollo, dentro de la raíz del repositorio `policrafters_cms`.

Después se hará:

``` bash
git add Dockerfile docker-compose.prod.yml .dockerignore .env.example .gitignore
git commit -m "Add production Docker deployment"
git push origin main
```

Luego, en el VPS, solamente será necesario traerlos con `git pull`.

------------------------------------------------------------------------

## 4. Dockerfile

Si el proyecto ya tiene un `Dockerfile` funcional para Django/Wagtail,
se recomienda conservarlo y verificar que:

1.  use Python 3.12;
2.  instale las dependencias del proyecto;
3.  copie el código a `/app`;
4.  ejecute `collectstatic`;
5.  permita ejecutar Gunicorn;
6.  no contenga contraseñas ni secretos.

El arranque de producción se controlará principalmente desde
`docker-compose.prod.yml`.

------------------------------------------------------------------------

## 5. Crear `docker-compose.prod.yml`

Crear este archivo **localmente**, en la raíz del repositorio:

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

    # Solo para administración desde el VPS o mediante túnel SSH.
    # PostgreSQL NO queda publicado hacia Internet.
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
             gunicorn policrafters_cms.wsgi:application
             --bind 0.0.0.0:8000
             --workers 3
             --timeout 120"

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

volumes:
  policrafters_cms_postgres_data:
  static_data:
  media_data:

networks:
  policrafters_cms_network:
    driver: bridge
```

### Qué consigue este Compose

-   crea un PostgreSQL 16 exclusivo para `policrafters_cms`;
-   crea automáticamente la base y el usuario en el primer arranque;
-   persiste PostgreSQL en un volumen independiente;
-   no utiliza el PostgreSQL de Ubuntu;
-   no utiliza `geqc26_db`;
-   no utiliza `gamy_db`;
-   Django se conecta a PostgreSQL mediante la red interna Docker;
-   PostgreSQL queda disponible en `127.0.0.1:5434` del VPS para
    administración mediante túnel SSH;
-   Django queda disponible en `127.0.0.1:8000` para el reverse proxy.

> No usar `docker compose down -v` en producción. La opción `-v` elimina
> los volúmenes declarados por Compose y podría destruir la base de
> datos.

------------------------------------------------------------------------

## 6. Variables de entorno

### 6.1 Crear `.env.example` LOCALMENTE

Este archivo sí se versiona:

``` env
DJANGO_SETTINGS_MODULE=policrafters_cms.settings.production

DB_ENGINE=django.db.backends.postgresql
DB_NAME=policrafters_cms
DB_USER=policrafters_cms_user
DB_PASSWORD=CHANGE_ME
DB_HOST=db
DB_PORT=5432

SECRET_KEY=CHANGE_ME

ALLOWED_HOSTS=cms.tu-dominio.com
CSRF_TRUSTED_ORIGINS=https://cms.tu-dominio.com
WAGTAILADMIN_BASE_URL=https://cms.tu-dominio.com
```

El punto fundamental es:

``` env
DB_HOST=db
DB_PORT=5432
```

Dentro de Docker, Django **no debe conectarse a `127.0.0.1:5434`**. El
nombre `db` es el DNS interno del servicio PostgreSQL definido en
Compose.

### 6.2 Proteger `.env.production`

Verificar que `.gitignore` contenga:

``` gitignore
.env
.env.production
.env.*
!.env.example
```

Antes de hacer commit:

``` bash
git status
```

Confirmar que `.env.production` **no aparece** entre los archivos que
Git va a subir.

------------------------------------------------------------------------

## 7. Subir la configuración Docker a GitHub

En el equipo local:

``` bash
git status
git add Dockerfile docker-compose.prod.yml .dockerignore .env.example .gitignore
git commit -m "Configure production deployment for policrafters CMS"
git push origin main
```

De esta forma el VPS recibe exactamente la misma infraestructura que
está almacenada en GitHub.

------------------------------------------------------------------------

## 8. Actualizar el VPS

Como el repositorio ya está clonado:

``` bash
cd /var/www/policrafters_cms
git status
git pull origin main
```

Antes de hacer `git pull`, `git status` debe estar limpio.

Si aparecen modificaciones locales, **no ejecutar inmediatamente
`git pull`**. Primero revisar:

``` bash
git diff
```

La intención de mantener Compose en GitHub es precisamente evitar que el
VPS tenga una versión modificada manualmente.

------------------------------------------------------------------------

## 9. Crear `.env.production` únicamente en el VPS

``` bash
cd /var/www/policrafters_cms
nano .env.production
```

Ejemplo:

``` env
DJANGO_SETTINGS_MODULE=policrafters_cms.settings.production

DB_ENGINE=django.db.backends.postgresql
DB_NAME=policrafters_cms
DB_USER=policrafters_cms_user
DB_PASSWORD=COLOCAR_PASSWORD_SEGURA

DB_HOST=db
DB_PORT=5432

SECRET_KEY=COLOCAR_SECRET_KEY

ALLOWED_HOSTS=cms.tu-dominio.com
CSRF_TRUSTED_ORIGINS=https://cms.tu-dominio.com
WAGTAILADMIN_BASE_URL=https://cms.tu-dominio.com
```

Generar una `SECRET_KEY`:

``` bash
python3 - <<'PY'
import secrets
print(secrets.token_urlsafe(64))
PY
```

Generar una contraseña fuerte para PostgreSQL:

``` bash
openssl rand -base64 32
```

Guardar estos valores fuera del repositorio.

------------------------------------------------------------------------

## 10. Validar Compose antes del primer arranque

``` bash
cd /var/www/policrafters_cms
docker compose -f docker-compose.prod.yml --env-file .env.production config
```

Este comando permite detectar errores de YAML y variables faltantes
antes de crear contenedores.

**Atención:** la salida expandida puede contener valores sensibles
provenientes de `.env.production`; no copiarla a tickets, chats públicos
o commits.

------------------------------------------------------------------------

## 11. Primer despliegue

Construir las imágenes:

``` bash
docker compose -f docker-compose.prod.yml --env-file .env.production build
```

Levantar los servicios:

``` bash
docker compose -f docker-compose.prod.yml --env-file .env.production up -d
```

Comprobar:

``` bash
docker compose -f docker-compose.prod.yml --env-file .env.production ps
```

Esperamos ver al menos:

``` text
policrafters_cms
policrafters_cms_db
```

------------------------------------------------------------------------

## 12. Verificar PostgreSQL

Ver logs:

``` bash
docker logs policrafters_cms_db
```

Comprobar las bases:

``` bash
docker exec -it policrafters_cms_db \
  psql -U policrafters_cms_user -d policrafters_cms
```

Dentro de PostgreSQL:

``` sql
\l
\dt
\q
```

La base `policrafters_cms` se crea automáticamente en el primer arranque
del contenedor.

No es necesario ejecutar `CREATE DATABASE` en el PostgreSQL instalado
directamente en Ubuntu.

------------------------------------------------------------------------

## 13. Verificar Django/Wagtail

Logs:

``` bash
docker logs -f policrafters_cms
```

Probar desde el VPS:

``` bash
curl -I http://127.0.0.1:8000
```

Revisar migraciones:

``` bash
docker exec -it policrafters_cms python manage.py showmigrations
```

Crear superusuario Wagtail/Django si es el primer despliegue:

``` bash
docker exec -it policrafters_cms python manage.py createsuperuser
```

------------------------------------------------------------------------

## 14. Conectar `policrafters_cms` a pgAdmin desde el Mac

El Compose publica PostgreSQL únicamente en:

``` text
VPS: 127.0.0.1:5434
```

No está disponible públicamente.

Desde el Mac abrir un túnel SSH:

``` bash
ssh -L 5434:127.0.0.1:5434 root@IP_DEL_VPS
```

Mantener esa terminal abierta.

En pgAdmin crear un servidor con:

  Campo                  Valor
  ---------------------- ------------------------
  Name                   Policrafters CMS VPS
  Host name/address      127.0.0.1
  Port                   5434
  Maintenance database   policrafters_cms
  Username               policrafters_cms_user
  Password               valor de `DB_PASSWORD`

Si el Mac ya utiliza el puerto local `5434`, se puede usar otro puerto
local:

``` bash
ssh -L 55434:127.0.0.1:5434 root@IP_DEL_VPS
```

y configurar pgAdmin con puerto `55434`.

------------------------------------------------------------------------

## 15. Reverse proxy

El CMS debe tener un dominio o subdominio independiente del frontend,
por ejemplo:

``` text
www.policrafters.com       -> policrafters_web
cms.policrafters.com       -> policrafters_cms
```

El proxy del CMS debe enviar las solicitudes a:

``` text
127.0.0.1:8000
```

Ejemplo Nginx:

``` nginx
server {
    listen 80;
    server_name cms.tu-dominio.com;

    client_max_body_size 30M;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

> Si el VPS ya utiliza Traefik para los demás proyectos, conviene
> integrar `policrafters_cms` con esa infraestructura en vez de instalar
> un segundo reverse proxy sin revisar primero la configuración
> existente.

------------------------------------------------------------------------

## 16. HTTPS

Si finalmente se utiliza Nginx:

``` bash
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d cms.tu-dominio.com
sudo systemctl status certbot.timer
```

Si se utiliza Traefik, el certificado debe configurarse mediante las
labels/router correspondientes y no mediante Certbot/Nginx.

------------------------------------------------------------------------

## 17. Flujo normal de actualización

### Desarrollo local

``` bash
git checkout main
git pull origin main

# realizar cambios

git add .
git commit -m "Descripción del cambio"
git push origin main
```

### VPS

``` bash
cd /var/www/policrafters_cms

git status
git pull origin main

docker compose -f docker-compose.prod.yml --env-file .env.production build
docker compose -f docker-compose.prod.yml --env-file .env.production up -d

docker compose -f docker-compose.prod.yml --env-file .env.production ps
docker logs --tail 100 policrafters_cms
```

Opcional:

``` bash
docker image prune -f
```

No ejecutar:

``` bash
docker compose down -v
```

------------------------------------------------------------------------

## 18. Si `git pull` informa cambios locales

Primero:

``` bash
git status
git diff
```

No sobrescribirlos sin revisar.

Si `docker-compose.prod.yml` fue creado y mantenido en GitHub,
normalmente no debería existir una versión diferente en producción.

Para archivos de configuración específicos del VPS utilizar
`.env.production`, que está ignorado por Git.

Esto separa correctamente:

``` text
GitHub
├── Dockerfile
├── docker-compose.prod.yml
├── .dockerignore
├── .env.example
└── código Django/Wagtail

VPS solamente
└── .env.production
```

------------------------------------------------------------------------

## 19. Backup de PostgreSQL

Crear un dump:

``` bash
docker exec policrafters_cms_db \
  pg_dump -U policrafters_cms_user -d policrafters_cms \
  > policrafters_cms_$(date +%Y%m%d_%H%M%S).sql
```

Comprobar:

``` bash
ls -lh policrafters_cms_*.sql
```

Los backups importantes deben copiarse también fuera del VPS.

------------------------------------------------------------------------

## 20. Comandos de diagnóstico

Estado:

``` bash
docker compose -f docker-compose.prod.yml --env-file .env.production ps
```

Logs Django:

``` bash
docker logs --tail 200 policrafters_cms
```

Logs PostgreSQL:

``` bash
docker logs --tail 200 policrafters_cms_db
```

Red:

``` bash
docker network ls
docker inspect policrafters_cms
docker inspect policrafters_cms_db
```

Puertos:

``` bash
ss -lntp | grep -E '5432|5433|5434|8000'
```

Probar PostgreSQL desde el contenedor Django:

``` bash
docker exec -it policrafters_cms python manage.py dbshell
```

------------------------------------------------------------------------

## 21. Checklist antes de producción

-   [ ] `Dockerfile` versionado en GitHub.
-   [ ] `docker-compose.prod.yml` versionado en GitHub.
-   [ ] `.env.example` versionado.
-   [ ] `.env.production` excluido de Git.
-   [ ] `SECRET_KEY` exclusiva de producción.
-   [ ] `DEBUG=False` efectivo en producción.
-   [ ] `ALLOWED_HOSTS` definido.
-   [ ] `CSRF_TRUSTED_ORIGINS` definido con HTTPS.
-   [ ] PostgreSQL corre en `policrafters_cms_db`.
-   [ ] Base `policrafters_cms` creada.
-   [ ] Usuario `policrafters_cms_user` creado.
-   [ ] Volumen PostgreSQL persistente.
-   [ ] Migraciones aplicadas.
-   [ ] Static y media persistentes.
-   [ ] Superusuario creado.
-   [ ] Reverse proxy configurado.
-   [ ] HTTPS funcionando.
-   [ ] Backup probado.
-   [ ] pgAdmin conectado mediante túnel SSH.

------------------------------------------------------------------------

## 22. Arquitectura final del VPS

``` text
VPS
│
├── PostgreSQL Ubuntu :5432
│
│
├── Docker
│   ├── geqc26_db
│   │     PostgreSQL :5432 interno / :5433 host
│   │
│   ├── gamy_db
│   │     PostgreSQL :5432 interno
│   │
│   ├── policrafters_web
│   │     Frontend Policrafters
│   │
│   ├── policrafters_cms
│   │     Django / Wagtail :8000
│   │
│   └── policrafters_cms_db
│         PostgreSQL 16 :5432 interno
│         127.0.0.1:5434 en host
│
└── Reverse proxy
      ├── dominio frontend -> policrafters_web
      └── dominio CMS/API -> policrafters_cms
```

Esta separación permite actualizar o reconstruir `policrafters_cms` sin
depender de las bases de datos de GEQC, GAMY o del PostgreSQL instalado
directamente en Ubuntu.
