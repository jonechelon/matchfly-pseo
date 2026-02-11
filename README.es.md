# MatchFly https://matchfly.org

**Monitor de Confiabilidad Aérea e Indemnizaciones**

<div align="center">

**Language / Idioma / Idioma:**

[![English](https://img.shields.io/badge/English-🇬🇧-blue?style=flat-square)](./README.md)
[![Português](https://img.shields.io/badge/Português-🇧🇷-green?style=flat-square)](./README.pt-BR.md)
[![Español](https://img.shields.io/badge/Español-🇪🇸-red?style=flat-square)](#español)

</div>

---

## 🇪🇸 Español

MatchFly agrega datos de vuelos (retrasos y cancelaciones) desde el Aeropuerto de Guarulhos (GRU), genera páginas estáticas optimizadas para SEO e informa a los pasajeros sobre derechos de indemnización (ANAC 400 / EC 261), con integración a socios de verificación de indemnización.

---

## Acerca de

MatchFly es una plataforma automatizada que:

- Consolida datos de vuelos (scrapers, CSV, datos ANAC)
- Genera un sitio estático con una página por vuelo problemático y por destino
- Ofrece una interfaz clara para consulta de estado y enlaces para verificación de indemnización

El sitio se publica en **GitHub Pages** desde la carpeta `docs/` en la rama `main`.

---

## UI: Split-Flap (Aeropuerto Retro)

La interfaz utiliza un concepto visual **Split-Flap** (paneles tipo aeropuerto retro): tarjetas por ciudad con vuelos retrasados/cancelados, navegación por pestañas (Ciudades, Cancelados, Retrasados) y página personalizada 404. El diseño es responsivo (Tailwind CSS) y accesible.

---

## Tech Stack

| Capa           | Tecnología                    |
|----------------|-------------------------------|
| Backend        | Python 3.12                   |
| Templates      | Jinja2                        |
| Estilos        | Tailwind CSS (CDN)            |
| Datos          | JSON (`data/flights-db.json`) |
| Publicación    | GitHub Pages (carpeta `/docs`) |

---

## Cómo ejecutar

**Prerrequisito:** tener datos en `data/flights-db.json` (generado por `voos_proximos_finalbuild.py` o por importación histórica).

Generar el sitio localmente (salida en `docs/`):

```bash
pip install -r requirements.txt
python src/generator.py
```

Abrir en el navegador: `docs/index.html` o servir la carpeta `docs/` con un servidor local (ej.: `python -m http.server --directory docs 8000`).

Para actualizar los datos antes de generar:

```bash
python voos_proximos_finalbuild.py
python src/generator.py
```

Pipeline completo (scraper + generador): `./scripts/run_pipeline.sh` (ejecutar desde la raíz del repositorio).

---

## Estructura del proyecto

| Carpeta / archivo   | Descripción |
|---------------------|-------------|
| `src/`              | Código principal: generador de páginas (`generator.py`), enriquecimiento, scrapers y plantillas Jinja2. |
| `docs/`             | **Salida del generador** y carpeta publicada en GitHub Pages (HTML, sitemap, robots, CNAME, 404). |
| `data/`             | Base de datos de vuelos en JSON y archivos de apoyo (ej.: rutas ANAC). |
| `_internal_docs/`   | Documentación técnica interna (arquitectura, deploy, guías). |
| `scripts/`          | Scripts de automatización y mantenimiento (ej.: `run_pipeline.sh`). |
| `voos_proximos_finalbuild.py` | Punto de entrada de sincronización de datos (usado por CI y localmente). |

---

## Documentación interna

- **Arquitectura y flujo:** `_internal_docs/ARCHITECTURE.md`
- **Deploy (GitHub Pages, CNAME, workflow):** `_internal_docs/DEPLOY.md`
- Otros guías y referencias: carpeta `_internal_docs/`

---

## Licencia y uso

Consulte el repositorio y la documentación interna para detalles de uso, contribución y licencia.
