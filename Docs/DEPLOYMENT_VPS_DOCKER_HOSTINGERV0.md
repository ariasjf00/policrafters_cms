# Deployment paso a paso en VPS Hostinger (KVM 2 Ubuntu) con Docker

Este documento describe un flujo completo para desplegar este proyecto Django/Wagtail en un VPS de Hostinger usando Docker, reutilizando una instancia PostgreSQL que ya existe en el servidor.

## 1) Integrar GitHub con tu VPS

### 1.1 Preparar acceso SSH al VPS

En tu maquina local:

```bash
ssh root@IP_DE_TU_VPS
```

Recomendado crear un usuario de despliegue:

```bash
adduser deploy
usermod -aG sudo deploy
usermod -aG docker deploy
```

### 1.2 Instalar git y utilidades

```bash
sudo apt update
sudo apt install -y git curl ca-certificates gnupg lsb-release
```

Si Git ya viene instalado en tu VPS (tu caso), puedes omitir este paso y solo validar:

```bash
git --version
```

### 1.3 Crear llave SSH en el VPS para GitHub

Con el usuario deploy:

```bash
ssh-keygen -t ed25519 -C "deploy-policrafters" -f ~/.ssh/id_ed25519 -N ""
cat ~/.ssh/id_ed25519.pub
```

Si ya tienes una llave SSH funcionando en ese VPS para otro repo (por ejemplo policrafters_web), puedes reutilizarla si la misma identidad tiene acceso al repo de este CMS.

Verifica llaves existentes:

```bash
ls -la ~/.ssh
```

Prueba autenticacion con GitHub:

```bash
ssh -T git@github.com
```

Si responde "successfully authenticated", la llave es valida.

### 1.4 Registrar llave en GitHub

En GitHub tienes dos opciones:

1. Repository Deploy Key (recomendada para un solo repo)
2. SSH Key de una cuenta tecnica (si vas a manejar varios repos)

Recomendacion practica:

1. Puedes usar la misma llave para varios repos solo si esa llave pertenece a un usuario de GitHub con permisos en todos ellos.
2. Si usas Deploy Keys por repo, normalmente necesitas una llave distinta por repositorio.
3. Para mayor orden/seguridad en servidores de produccion, suele convenir una llave por app.

Ruta sugerida:

1. Repo -> Settings -> Deploy keys -> Add deploy key
2. Pegar la salida de ~/.ssh/id_ed25519.pub
3. Marcar Read access (o Write access si el flujo lo requiere)

### 1.5 Clonar el proyecto en el VPS

```bash
sudo mkdir -p /var/www
sudo chown -R $USER:$USER /var/www
cd /var/www
git clone git@github.com:ariasjf00/policrafters_cms.git
cd policrafters-cms
git checkout main
```

Nota: para mantener consistencia con tu estructura actual, usa /var/www junto a /var/www/policrafters_web.

## 2) Instalar Docker y Docker Compose plugin

```bash
sudo apt update
sudo apt install -y docker.io docker-compose-v2
sudo systemctl enable --now docker
docker --version
docker compose version
```

Si estas en usuario deploy y no quieres usar sudo en cada comando:

```bash
sudo usermod -aG docker $USER
newgrp docker
```

## 3) Preparar PostgreSQL existente (sin dockerizar)

Como ya tienes PostgreSQL corriendo con otras apps, no levantes un contenedor de postgres para este proyecto.

### 3.1 Crear base y usuario dedicados

En el servidor, con el usuario postgres:

```bash
sudo -u postgres psql
```

Dentro de psql:

```sql
CREATE DATABASE policrafters_cms_prod;
CREATE USER policrafters_app WITH ENCRYPTED PASSWORD 'PASSWORD_MUY_SEGURA';
GRANT ALL PRIVILEGES ON DATABASE policrafters_cms_prod TO policrafters_app;
\q
```

Nota: al compartir PostgreSQL con otras apps, usa una base y usuario exclusivos para aislar permisos.

### 3.2 Verificar conectividad local

Si PostgreSQL esta en el mismo VPS, normalmente el host sera localhost y puerto 5432.

## 4) Archivos Docker recomendados

Tu repo ya tiene un Dockerfile funcional multi-stage. Para produccion en VPS te conviene manejar arranque con compose + variables de entorno.

### 4.1 Dockerfile (actual)

Archivo actual: Dockerfile en la raiz del repo.

Puntos importantes del Dockerfile actual:

1. Usa python:3.12-slim-bookworm en builder y runtime.
2. Instala dependencias de compilacion en builder y runtime libs minimas.
3. Ejecuta collectstatic en build.
4. Arranca con migrate + gunicorn en CMD.

Puedes mantenerlo asi para un primer deploy. Mas adelante puedes mover migrate a un paso separado.

### 4.2 Crear docker-compose.prod.yml

Crear archivo docker-compose.prod.yml en la raiz:

```yaml
services:
  web:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: policrafters_web
    restart: unless-stopped
    env_file:
      - .env.production
    environment:
      DJANGO_SETTINGS_MODULE: policrafters_cms.settings.production
      PORT: 8000
    command: >
      sh -c "python manage.py migrate --noinput && gunicorn policrafters_cms.wsgi:application --bind 0.0.0.0:8000 --workers 3 --timeout 120"
    ports:
      - "127.0.0.1:8000:8000"
    volumes:
      - static_data:/app/static
      - media_data:/app/media

volumes:
  static_data:
  media_data:
```

Este compose:

1. No levanta PostgreSQL (usa el existente).
2. Expone app solo en localhost para que Nginx haga reverse proxy.
3. Persiste static y media en volumnes Docker.

### 4.3 Crear .env.production

Crear .env.production en la raiz (no subirlo a git):

```env
DJANGO_SETTINGS_MODULE=policrafters_cms.settings.production

DB_ENGINE=django.db.backends.postgresql
DB_NAME=policrafters_cms_prod
DB_USER=policrafters_app
DB_PASSWORD=CAMBIA_ESTE_PASSWORD
DB_HOST=127.0.0.1
DB_PORT=5432

# OJO: en el codigo actual, production.py no define SECRET_KEY/ALLOWED_HOSTS por defecto.
# Si no tienes settings/local.py en produccion, debes inyectarlos desde configuracion local del proyecto.
SECRET_KEY=CAMBIA_ESTA_LLAVE_SECRETA
ALLOWED_HOSTS=tu-dominio.com,www.tu-dominio.com,IP_DEL_VPS
CSRF_TRUSTED_ORIGINS=https://tu-dominio.com,https://www.tu-dominio.com
WAGTAILADMIN_BASE_URL=https://tu-dominio.com
```

Generar SECRET_KEY rapido:

```bash
python - <<'PY'
from django.core.management.utils import get_random_secret_key
print(get_random_secret_key())
PY
```

Importante: agrega .env.production a .gitignore.

## 5) Preparar Nginx como reverse proxy

Instalar Nginx:

```bash
sudo apt install -y nginx
```

Crear archivo /etc/nginx/sites-available/policrafters:

```nginx
server {
    listen 80;
    server_name tu-dominio.com www.tu-dominio.com;

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

Activar sitio:

```bash
sudo ln -s /etc/nginx/sites-available/policrafters /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

## 6) Primer deploy

En el repo dentro del VPS:

```bash
cd /var/www/policrafters-cms
docker compose -f docker-compose.prod.yml build --no-cache
docker compose -f docker-compose.prod.yml up -d
docker compose -f docker-compose.prod.yml logs -f web
```

Checks utiles:

```bash
docker ps
curl -I http://127.0.0.1:8000
```

## 7) HTTPS con Let's Encrypt

```bash
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d tu-dominio.com -d www.tu-dominio.com
sudo systemctl status certbot.timer
```

## 8) Flujo de actualizacion (deploy continuo manual)

Cada vez que publiques cambios:

```bash
cd /var/www/policrafters-cms
git pull origin main
docker compose -f docker-compose.prod.yml build
docker compose -f docker-compose.prod.yml up -d
docker image prune -f
```

## 9) Integracion GitHub Actions opcional (auto-deploy)

Puedes automatizar deploy al hacer push a main con SSH.

### 9.1 Secrets en GitHub

En GitHub repo -> Settings -> Secrets and variables -> Actions:

1. VPS_HOST
2. VPS_USER
3. VPS_SSH_KEY
4. VPS_APP_DIR (ejemplo recomendado en tu caso: /var/www/policrafters-cms)

### 9.2 Workflow ejemplo

Crear .github/workflows/deploy.yml:

```yaml
name: Deploy VPS

on:
  push:
    branches: ["main"]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - name: Deploy over SSH
        uses: appleboy/ssh-action@v1.2.0
        with:
          host: ${{ secrets.VPS_HOST }}
          username: ${{ secrets.VPS_USER }}
          key: ${{ secrets.VPS_SSH_KEY }}
          script: |
            cd ${{ secrets.VPS_APP_DIR }}
            git pull origin main
            docker compose -f docker-compose.prod.yml build
            docker compose -f docker-compose.prod.yml up -d
            docker image prune -f
```

## 10) Checklist de produccion para este proyecto

1. Definir SECRET_KEY para produccion.
2. Definir ALLOWED_HOSTS reales (no usar *).
3. Definir CSRF_TRUSTED_ORIGINS con https.
4. Configurar WAGTAILADMIN_BASE_URL con dominio real.
5. Confirmar que DB_NAME/DB_USER/DB_PASSWORD apuntan a la base dedicada.
6. Verificar backups de PostgreSQL antes del go-live.
7. Verificar que media y static persisten (volumes).

## 11) Troubleshooting rapido

### Error: DisallowedHost

Revisar ALLOWED_HOSTS en .env.production.

### Error CSRF verification failed

Revisar CSRF_TRUSTED_ORIGINS con esquema https://.

### Error conexion PostgreSQL

1. Validar credenciales DB_*
2. Verificar que PostgreSQL acepte conexiones locales

## 12) Ajustes si ya tienes policrafters_web desplegado

Si ya tienes el frontend Astro en /var/www/policrafters_web, para este CMS aplica:

1. Desplegar el CMS en otra carpeta: /var/www/policrafters-cms.
2. Mantener compose separado por proyecto (cada app con su docker-compose propio).
3. En Nginx, usar server_name y/o location separados para frontend y CMS/API.
4. Si ambos usan GitHub SSH, puedes reutilizar la misma llave solo si esa identidad tiene acceso a ambos repos.
5. Si quieres menor riesgo operacional, crea otra llave para el CMS (aislamiento por app).

Ejemplo rapido de pull usando la llave ya configurada:

```bash
cd /var/www/policrafters-cms
git remote -v
git pull origin main
```
3. Probar login manual:

```bash
psql -h 127.0.0.1 -U policrafters_app -d policrafters_cms_prod
```

### Error de estaticos

Revisar logs del contenedor y confirmar que collectstatic se ejecuto durante build.
