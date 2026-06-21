# FeriaKL — API (backend Python)

API REST en **FastAPI** para FeriaKL. Corre local con **SQLite** (sin instalar nada extra) y se despliega en **Google Cloud Run + Cloud SQL (PostgreSQL)**.

## Estructura

```
backend/
├─ app/
│  ├─ main.py          # arma la app, CORS, crea tablas y seed al iniciar
│  ├─ config.py        # configuración por variables de entorno
│  ├─ database.py      # conexión SQLAlchemy (SQLite o Postgres)
│  ├─ models.py        # tablas: users, products, sales, sale_items, customers, payments, mermas
│  ├─ schemas.py       # esquemas Pydantic (entrada/salida JSON)
│  ├─ auth.py          # hash de contraseñas + JWT + roles
│  ├─ seed.py          # admin inicial + productos de ejemplo
│  └─ routers/         # auth, products, sales, customers (fiado), mermas, reports
├─ requirements.txt
├─ Dockerfile          # para Cloud Run
└─ .env.example
```

## Correr en local

Requisitos: **Python 3.12+** (instálalo desde https://www.python.org/downloads/ — marca "Add to PATH").

```bash
cd backend
python -m venv .venv
# Windows PowerShell:
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env        # (PowerShell)  o  cp .env.example .env
uvicorn app.main:app --reload
```

- API: http://127.0.0.1:8000
- **Documentación interactiva (Swagger): http://127.0.0.1:8000/docs** ← prueba todo desde aquí
- Login inicial: `admin@feriakl.cl` / `feria1234` (cámbialo).

### Cómo autenticarte para probar
1. En `/docs`, endpoint `POST /auth/login` → ingresa el correo en *username* y la clave.
2. Copia el `access_token`. Clic en **Authorize** (arriba a la derecha) y pégalo.
3. Ya puedes llamar al resto de endpoints (productos, ventas, fiado, etc.).

## Endpoints principales

| Método | Ruta | Para qué |
|---|---|---|
| POST | `/auth/login` | Iniciar sesión (devuelve token) |
| GET/POST | `/auth/users` | Listar / crear usuarios (admin) |
| GET/POST/PATCH | `/products` | Inventario |
| POST/GET | `/sales` | Registrar venta (descuenta stock) / historial |
| GET/POST | `/customers` | Clientes con fiado (deuda calculada) |
| POST | `/customers/{id}/payments` | Registrar abono |
| GET/POST | `/mermas` | Registrar / listar pérdidas |
| GET | `/reports/summary` | KPIs del día |
| GET | `/reports/sales-by-day` | Ventas por día |
| GET | `/reports/top-products` | Más vendidos |

## Desplegar en Google Cloud (GCP)

Requisitos: cuenta GCP con facturación, [gcloud CLI](https://cloud.google.com/sdk/docs/install) instalado.

```bash
# Variables
export PROJECT=feriakl            # tu ID de proyecto
export REGION=southamerica-west1  # Santiago

gcloud config set project $PROJECT
gcloud services enable run.googleapis.com sqladmin.googleapis.com artifactregistry.googleapis.com

# 1) Base de datos: Cloud SQL Postgres (instancia más pequeña)
gcloud sql instances create feriakl-db --database-version=POSTGRES_16 \
  --tier=db-f1-micro --region=$REGION
gcloud sql databases create feriakl --instance=feriakl-db
gcloud sql users create feriakl --instance=feriakl-db --password=TU_CLAVE_DB

# 2) Guarda el SECRET_KEY como secreto
echo -n "$(openssl rand -hex 32)" | gcloud secrets create feriakl-secret --data-file=-

# 3) Despliega (backend + frontend en una sola imagen).
#    OJO: el contexto es la RAÍZ del repo (no backend/), porque la imagen
#    incluye el frontend. Se usa el Dockerfile de la raíz.
gcloud run deploy feriakl \
  --source . \
  --region $REGION \
  --allow-unauthenticated \
  --add-cloudsql-instances $PROJECT:$REGION:feriakl-db \
  --set-secrets SECRET_KEY=feriakl-secret:latest \
  --set-env-vars "DATABASE_URL=postgresql+psycopg2://feriakl:TU_CLAVE_DB@/feriakl?host=/cloudsql/$PROJECT:$REGION:feriakl-db"
```

Cloud Run te entrega una URL `https://feriakl-....run.app` que sirve **la app y el API juntos**, ya con **HTTPS y certificado válido automático** (la cámara funcionará sin avisos).

## Certificados / HTTPS en producción

No se suben certificados manualmente:

- **URL `*.run.app`**: Cloud Run la entrega con TLS y **certificado administrado por Google** (confiable, auto-renovado). Cero configuración.
- **Dominio propio** (ej. `app.feriakl.cl`): al mapearlo, Google **provisiona y renueva** un certificado administrado gratis:
  ```bash
  gcloud beta run domain-mappings create --service feriakl --domain app.feriakl.cl --region $REGION
  # Luego agrega en tu DNS los registros que el comando indique. El certificado
  # queda activo (estado "Certificate provisioned") en unos minutos a ~1 hora.
  ```

> El certificado autofirmado de `backend/certs/` es **solo para probar la cámara en el celular en red local**. No se usa ni se sube a producción (está en `.gitignore` y `.gcloudignore`).

> **Costos:** Cloud Run escala a cero (pagas casi nada con tráfico bajo). Cloud SQL `db-f1-micro` tiene un costo base mensual (~USD 8–10); si quieres evitarlo al inicio, puedes mantener SQLite en una sola instancia, pero pierdes el multi-dispositivo. Lo conversamos.
