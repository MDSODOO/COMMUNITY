# Plan de Ajuste de Diseño: Correo Electrónico y Componentes UI

## Referencias de Diseño del Proyecto

| Referencia | Archivo | Patrón Clave |
|---|---|---|
| **Tokens de marca** | `_tokens.scss` | `--md-primary: #16A6D9`, `--md-action: #97D700`, botón pill con gradiente |
| **Backend bento** | `backend_bento.scss` | Vidrio (`backdrop-filter`), botones pill, tarjetas con hover lift (-2px) |
| **Kanban productos** | `product_kanban_card.scss` | Borde izquierdo 4px `--md-primary`, badges pill con semáforo verde/rojo |
| **Portal bento** | `portal_bento.scss` | Liquid Glass, tarjetas con gradiente radial, hover -5px + scale |
| **Command palette** | `launcher.scss` | Spotlight glass, tiles con gradiente radial, chip "A la mano" |

---

## Capa 1: Módulo de Correo (`md_mail_client`)

### 1.1. Bandeja de mensajes (lista)

| Elemento | Estado Actual | Propuesta |
|---|---|---|
| Fondo fila | Blanco sólido | Fondo `--md-paper` con hover `rgba(22,166,217,0.05)` (igual que listas backend) |
| Fila seleccionada | Borde o clase | Borde izquierdo 3px `--md-primary` (mismo patrón que kanban productos) |
| Avatar remitente | Círculo con inicial + color hash | Círculo 32px, borde 2px `--md-primary`, sombra suave `--md-shadow-1` |
| Chip estado | Sin estilo consistente | Pill radio `--md-radius-pill`, `font-size: --md-text-sm`, color semántico (verde=enviado, rojo=exception, gris=borrador) |
| Separador fecha | Sin agrupación | Agrupar mensajes por día, con label tipo "Hoy", "Ayer", "DD/MM/AAAA" |

**Referencia visual:** `md_lots_management/product_kanban_card.scss` (borde izquierdo + badges)

### 1.2. Botones de acción (Redactar, Responder, Reenviar)

| Elemento | Estado Actual | Propuesta |
|---|---|---|
| Redactar | Botón genérico | `mixin md-btn-primary` de `_tokens.scss` — fondo gradiente `--md-primary`→`--md-action`, pill `border-radius: 999px`, hover lift con sombra |
| Responder *primary* | Botón genérico | Fondo `--md-primary`, pill, hover más oscuro |
| Responder/Reenviar *secondary* | Botón genérico | Outline pill: borde `--md-primary`, texto `--md-primary`, hover sólido |

**Referencia visual:** `backend_bento.scss` → `.btn.btn-primary` (pill + gradiente)

### 1.3. Panel de lectura

| Elemento | Estado Actual | Propuesta |
|---|---|---|
| Fondo panel | Blanco sólido | `background: rgba(255,255,255,0.97)` con `backdrop-filter: blur(10px)` (vidrio backend) |
| Avatar remitente | Genérico | Mismo círculo 40px que lista, con nombre + correo en texto jerarquizado (`--md-color-text-primary` / `--md-color-text-secondary`) |
| Separadores | Sin estilo | Bordes sutiles `--md-border` |

**Referencia visual:** `backend_bento.scss` → `.o_control_panel` (vidrio)

### 1.4. Dark mode

Cada elemento anterior debe tener su override bajo `html.o_md_dark_mode`, siguiendo el patrón de `backend_dark.scss` (fondos oscuros, opacidad ajustada).

---

## Capa 2: Kanban de Productos (Inventario)

Ya implementado en `md_lots_management/product_kanban_card.scss` y `md_pharma_regulatory/product_kanban_pos_style.scss`.

### Mejoras propuestas *(post-auditoría)*

| Elemento | Propuesta |
|---|---|
| Badge "A la mano" | Fondo semáforo: verde (`qty_available > 10`), amarillo (`1-10`), rojo (`=0`) usando `--md-success`, `--md-warning`, `--md-danger` |
| Card hover | Elevación `translateY(-2px)` + sombra `0 12px 28px rgba(22,166,217,0.14)` (misma receta backend `o_kanban_record`) |
| Imagen producto | `object-fit: contain` con fondo blanco, radio `--md-radius-sm`, borde sutil `--md-border` |

---

## Capa 3: Portal Web / Farmacovigilancia

### 3.1. Formulario público de farmacovigilancia

| Elemento | Propuesta |
|---|---|
| Tarjeta del formulario | Liquid Glass (`mixin md-liquid-glass` de `_tokens.scss`) — mismo patrón que portal bento |
| Botón enviar | `btn-primary` pill con gradiente (misma receta) |
| Inputs | 42px altura, `border-radius: 0.65rem`, focus ring 3px `--md-primary` al 15% (igual que `backend_bento.scss`) |
| Stepper pasos | Círculos numerados con borde `--md-primary`, activos con relleno `--md-primary`, completados con check verde |

**Referencia visual:** `portal_bento.scss` → Liquid Glass cards + `afiliacion.scss` wizard steps

### 3.2. Reporte en backend

| Elemento | Propuesta |
|---|---|
| Sheet form | Bento card (`background: white`, `border`, `--md-shadow-1`, `margin` ) como estándar en `backend_bento.scss` |
| Statusbar | Vidrio con blur, estado activo en `--md-primary` |
| Chatter | Fondo vidrio `rgba(255,255,255,0.62)`, avatar remitente círculo 28px con borde `--md-primary` |

---

## Capa 4: Command Palette Icons

| Acción | Icono Anterior | Icono Nuevo | Significado |
|---|---|---|---|
| Copiloto de inventario (IA local) | `fa-comments-o` | `fa-search-plus` | Buscar/consultar inventario |
| Identificar producto desde foto | `fa-camera` | `fa-eyedropper` | Identificación farmacéutica |
| Farmacovigilancia — Nuevo reporte | *(no existía)* | `fa-heartbeat` | Monitoreo de seguridad de medicamentos |

Implementado en:
- `local_ai_connector/static/src/js/launcher_quick_actions.js` (3 acciones)
- `medicine_depot_portal/static/src/js/launcher_quick_actions.js` (1 acción nueva)

---

## Principios de Diseño Consistentes (Checklist)

- [ ] **Botones:** Pill shape (`border-radius: 999px`), gradiente primario (blue→green) para primary, outline para secondary
- [ ] **Tarjetas:** Borde izquierdo 4px `--md-primary`, hover `translateY(-2px)`, sombra azul
- [ ] **Vidrio:** `backdrop-filter: blur(10px) saturate(1.2)` con fallback `rgba(255,255,255,0.97)` — exactamente como backend_bento.scss
- [ ] **Badges/Chips:** Pill shape, `font-size: --md-text-sm` (0.75rem), `font-weight: 700`, padding 0.15rem 0.5rem
- [ ] **Tipografía:** Poppins (headings), Inter (body), `--md-weight-heading: 700`, `--md-weight-label: 600`
- [ ] **Dark mode:** Override por clase `html.o_md_dark_mode` siguiendo backend_dark.scss
- [ ] **Terminología:** Siempre "A la mano" (nunca "Disponible" / "Stock")
- [ ] **Espaciado:** Rejilla 4px (`--md-space-1` a `--md-space-6`)

---

## Prioridad de Implementación

| Prioridad | Componente | Esfuerzo |
|---|---|---|
| 🔴 P0 | Botones `md_mail_client` (Redactar, Responder) → `_tokens.scss` mixins | 1h |
| 🟡 P1 | Bandeja mensajes `md_mail_client` (borde selección, avatar, chips) | 2h |
| 🟡 P1 | Badge semáforo kanban productos | 1h |
| 🟢 P2 | Vidrio panel lectura `md_mail_client` | 1h |
| 🟢 P2 | Formulario farmacovigilancia Liquid Glass | 2h |
| 🟢 P2 | Dark mode overrides para md_mail_client | 1h |
| ✅ Hecho | Icons command palette (3 cambios + 1 nuevo) | Completado |

---

*Basado en la auditoría de correo del 2026-07-29. Las referencias visuales están en los SCSS del proyecto ya desplegados en producción.*
