# FeriaKL — API (backend Python + Firestore)

API REST en **FastAPI** que además sirve la PWA. Base de datos **Firestore** (nativa de GCP, free tier). Se despliega en **Cloud Run** (free tier), que sirve backend y frontend desde el mismo origen y con HTTPS/certificado administrado automático.

## Estructura

```
backend/app/
├─ main.py        # app, cabeceras de seguridad (CSP, HSTS, Permissions-Policy), CORS, seed
├─ config.py      # configuración por variables de entorno
├─ db.py          # cliente Firestore + colecciones (users, products, sales, mermas)
├─ auth.py        # bcrypt + JWT + roles + rate-limit de login
├─ schemas.py     # validación Pydantic (longitudes, formatos)
├─ seed.py        # admin inicial + productos de limpieza de ejemplo
└─ routers/       # auth, products, sales, mermas, reports
```

## Seguridad incluida

- **Login por persona** con JWT y contraseñas **bcrypt**; política mínima de 8 caracteres.
- **Rate-limit** de login (anti fuerza bruta) por IP+correo.
- **Cabeceras**: `Content-Security-Policy`, `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`, `Permissions-Policy` (cámara solo same-origin), `HSTS` en producción.
- **Validación estricta** de entradas (Pydantic) y **escape XSS** en el frontend.
- **Secretos** (SECRET_KEY, contraseña admin) en **Secret Manager**, nunca en el código.
- En `ENVIRONMENT=production` la app **no arranca** con la clave de desarrollo.

## Correr en local

Requiere credenciales de GCP y una base Firestore (el emulador necesita Java 21+):

```bash
gcloud auth application-default login          # credenciales locales (ADC)
cd backend
python -m venv .venv && .venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env                          # edita GCP_PROJECT, SECRET_KEY, SEED_ADMIN_PASSWORD
uvicorn app.main:app --reload
```

- App + API: http://127.0.0.1:8000 · Docs: http://127.0.0.1:8000/docs

## Desplegar a GCP (Cloud Run + Firestore, free tier)

Con `gcloud` autenticado, desde la **raíz del repo**:

```bash
PROJECT=tu-proyecto REGION=southamerica-west1 bash deploy.sh
```

El script (`../deploy.sh`):
1. Habilita las APIs necesarias.
2. Crea la base **Firestore (Native)**.
3. Genera y guarda **SECRET_KEY** y la **contraseña inicial del admin** en Secret Manager (te la muestra una vez).
4. Da permisos de Firestore/secretos a la cuenta de servicio de Cloud Run.
5. Despliega (build del `Dockerfile` de la raíz, que empaqueta backend + frontend).
6. Imprime la **URL pública** (`https://feriakl-….run.app`).

### Certificados / HTTPS
Automáticos: Cloud Run entrega TLS con certificado administrado por Google. Para dominio propio:
`gcloud beta run domain-mappings create --service feriakl --domain app.tudominio.cl --region $REGION`.

### Costos
Cloud Run escala a cero y Firestore tiene cuota diaria gratis (1 GiB, 50K lecturas / 20K escrituras al día). Para un puesto, se mantiene en **USD 0**.
