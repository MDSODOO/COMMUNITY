# Medicine Depot - Gestión de Lotes

**Módulo**: `md_lots_management`
**Versión**: 19.0.1.0.0
**Estado**: 🚀 Producción
**Última actualización**: 2026-06-03

---

## 📖 Descripción

Módulo que migra personalizaciones de **Odoo Studio** en el modelo `stock.production.lot` a **código puro**, mejorando:

- ✅ **Preservación de datos**: Migración limpia sin pérdida de historial
- ✅ **Mejora de UI**: Vistas refactorizadas, limpias de artefactos de Studio
- ✅ **Mantenibilidad**: Código nativo, versionable y auditable
- ✅ **Rendimiento**: Optimización de queries y cálculos

---

## 🎯 Características Principales

### Campos Personalizados

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `cantidad_la_mano` | Float (Computed) | Cantidad total **A la Mano** (disponible en inventario) |
| `fecha_entrada` | Datetime | Fecha de ingreso del lote al sistema |
| `fecha_vencimiento_estimado` | Date | Estimación complementaria de vencimiento |
| `estado_lote` | Selection | Estado: Activo, Pausado, Agotado, Descontinuado |
| `notas_calidad` | Text | Observaciones de calidad durante inspección |
| `usuario_creacion` | Many2one (res.users) | Usuario que creó el lote |
| `codigo_proveedor_externo` | Char | Identificador del proveedor |
| `referencia_compra` | Char | Número de OC o factura asociada |

### Vistas

#### 1. **Vista de Lista** (`production_lot_views.xml`)
- Columnas optimizadas: Número, Producto, **A la Mano**, Vencimiento, Estado
- Campos opcionales (hidden/show): Referencias, Ubicación, Códigos
- Búsqueda mejorada con filtros
- Agrupación por Producto, Estado, Fecha

#### 2. **Vista de Formulario** (`production_lot_forms.xml`)
- **Pestaña 1 - Información General**: Datos básicos, cantidad, estado
- **Pestaña 2 - Referencias Externas**: Códigos del proveedor y OC
- **Pestaña 3 - Auditoría**: Usuario creador, fechas de modificación
- **Pestaña 4 - Movimientos**: Tabla de ubicaciones y cantidades

#### 3. **Vista Kanban**
- Agrupación por `estado_lote`
- Visualización de cantidad **A la Mano** y vencimiento
- Acceso rápido a movimientos

---

## 🚀 Instalación y Uso

### Instalación

1. **Desde Odoo.sh**:
   ```bash
   # El módulo se instalará automáticamente si está en addons_path
   # En Odoo: Apps → Buscar "Medicine Depot - Gestión de Lotes" → Instalar
   ```

2. **Verificar instalación**:
   - Ir a: **Inventario → Seguimiento → Lotes**
   - Deberías ver la nueva interfaz refactorizada

### Uso

#### Ver lista de lotes
```
Inventario → Seguimiento → Lotes
```

#### Buscar lotes activos
```
Filtro: "Activos"
O búsqueda manual por: Número, Producto, Código Proveedor
```

#### Abrir un lote
- Click en cualquier fila
- Verás todas las pestañas con información completa

---

## 🔄 Migración desde Studio

Este módulo **reemplaza las personalizaciones de Studio** del modelo `stock.production.lot`:

### Antes (Studio)
```
- Campos x_studio_* en BD
- Vistas con atributos studio_modifiers, studio_id
- Dependencia en Studio para cambios
- Riesgo de pérdida de datos
```

### Después (Código Puro)
```
✅ Campos nativos con validaciones
✅ Vistas limpias y legibles
✅ Versionable en Git
✅ Preservación de datos históricos
```

### Preservación de Datos
Los datos existentes en campos Studio se **migran automáticamente**:
- Columnas PostgreSQL se mapean 1:1
- No hay truncamiento de valores
- Historial completo se preserva

---

## 📊 Ejemplos de Uso

### Ejemplo 1: Consultar cantidad A la Mano

```python
# En código Odoo
lot = env['stock.lot'].search([('name', '=', 'LOT-2026-001')])
print(f"Lote {lot.name}: {lot.cantidad_la_mano} unidades A la Mano")
```

### Ejemplo 2: Filtrar lotes por estado

```python
# Lotes activos
lotes_activos = env['stock.lot'].search([
    ('estado_lote', '=', 'activo')
])
```

### Ejemplo 3: Obtener lotes vencidos

```python
from odoo import fields
hoy = fields.Date.today()

lotes_vencidos = env['stock.lot'].search([
    ('expiration_date', '<', hoy)
])
```

---

## 🔐 Permisos y Acceso

### Grupos de Usuario

| Grupo | Permisos | Descripción |
|-------|----------|-------------|
| **Usuario Básico** | Lectura | Ver lotes, campos de auditoría |
| **Inventario** | Lectura + Escritura | Crear y editar lotes |
| **Gerente de Inventario** | Completo | Crear, editar, eliminar lotes |

---

## ⚙️ Configuración

### Variables Computadas

El campo `cantidad_la_mano` se **calcula automáticamente** a partir de:
```
cantidad_la_mano = SUM(quant.quantity) para cada ubicación del lote
```

Esto ocurre en tiempo real cuando hay movimientos de inventario.

### Validaciones

1. **Fechas de vencimiento**:
   ```
   fecha_vencimiento_estimado ≤ expiration_date
   ```

2. **Estado del lote**:
   ```
   Solo valores: Activo | Pausado | Agotado | Descontinuado
   ```

---

## 🐛 Troubleshooting

### Problema: El campo "A la Mano" muestra 0

**Solución**: Verifica que haya movimientos de inventario para el lote:
1. Abre el lote
2. Pestaña "Movimientos de Inventario"
3. Debería haber al menos una línea con ubicación y cantidad

### Problema: Vistas no cargan después de instalar

**Solución**:
1. Ve a **Ajustes → Técnico → Vistas**
2. Busca las vistas del módulo (`view_production_lot_*`)
3. Haz clic en "Recargar"

### Problema: Campos Studio antiguos se ven vacíos

**Solución**: Los campos antiguos (`x_studio_*`) se migran automáticamente. Si aún ves vacíos:
1. Ejecuta: **Ajustes → Técnico → Base de datos → Actualizar módulos**
2. Reinicia la sesión

---

## 📝 Notas Técnicas

### Herencia de Modelo
```python
class ProductionLot(models.Model):
    _inherit = 'stock.production.lot'
    # Agrega nuevos campos sin sobreescribir existentes
```

### Funciones Computadas (Stored)
```python
@api.depends('quant_ids')
def _compute_cantidad_la_mano(self):
    # Calcula y persiste en BD para rendimiento
```

### Restricción de Integridad
```python
@api.constrains('fecha_vencimiento_estimado', 'expiration_date')
def _check_expiration_dates(self):
    # Valida en nivel de modelo (seguridad)
```

---

## 📞 Soporte

Para problemas o sugerencias:
- **Email**: daniel.cervera.2029@gmail.com
- **Documentación**: Ver `STUDIO_MIGRATION_PLAN.md`
- **Tests**: `tests/test_lots_migration.py`

---

## 📜 Licencia

LGPL-3 (compatible con Odoo)

---

**Manteni do por**: Claude Code
**Proyecto**: Medicine Depot
**Fecha**: 2026-06-03
