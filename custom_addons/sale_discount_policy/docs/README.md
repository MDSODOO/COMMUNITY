# Documentación: sale_discount_policy Module

## 📖 Estructura de Documentación

Este directorio contiene toda la documentación necesaria para implementar, mantener y entender el sistema de automatización de descuentos para Farmacias Económicas.

### 1. **SETUP.md** ⭐ START HERE
   - Instrucciones paso a paso de instalación
   - Configuración post-instalación
   - Verificación del sistema
   - Troubleshooting
   - **Lee esto primero** si estás instalando el módulo

### 2. **DESIGN.md** — Para Desarrolladores
   - Decisiones arquitectónicas
   - Explicación del modelo de datos
   - Flujo de cálculo (Sales + POS)
   - Lógica del motor de descuentos
   - **Lee esto** si necesitas entender la arquitectura técnica

### 3. **RESTRICTED_BRANDS.md** — Para Especialistas de Datos
   - Resumen de las 21 marcas restringidas
   - Distribución de 203 artículos
   - Cómo etiquetar productos
   - **Leer cuando necesites gestionar las restricciones**

### 4. **LISTA_COMPLETA_ARTICULOS.md** — Referencia Completa
   - Desglose de los 203 artículos por marca
   - Códigos EAN específicos
   - Instrucciones de verificación
   - **Consulta cuando necesites información detallada**

### 5. **ARTICULOS_SIN_DESCUENTO.csv** — Archivo de Importación
   - Datos en formato CSV (ean, marca, nombre)
   - 203 filas de productos restringidos
   - **Úsalo en el wizard de importación**

---

## 🚀 Flujo Rápido de Instalación

1. **Instala el módulo:**
   ```bash
   odoo -d <database> -i sale_discount_policy
   ```

2. **Configura según SETUP.md:**
   - Asigna almacenes autorizados
   - Etiqueta clientes Farmacias Económicas
   - Importa los 203 artículos restrictivos

3. **Verifica en SETUP.md — Sección "Verification"**

---

## 📊 Datos Clave

| Métrica | Valor |
|---------|-------|
| Marcas restringidas | 21 |
| Artículos específicos | 203 |
| Descuento aplicado | 2.0% |
| Sucursales autorizadas | Cancún, Playa del Carmen |
| Grupo de clientes | Farmacias Económicas |

---

## 🔍 Desglose de los 203 Artículos

| Marca | Cantidad | Ejemplo |
|-------|----------|---------|
| Procter | 53 | Detergentes, higiene |
| PISA | 24 | Medicamentos |
| Bayer/Lakeside | 23 | Aspirina, Flanax, Tabcin |
| Armstrong | 19 | Antibióticos, Zyrtec |
| Cosbel/Frabel | 11 | Enjuagues bucales |
| Colgate-Palmolive | 10 | Pastas dentales |
| Grisi | 10 | Productos variados |
| Grin | 12 | Productos variados |
| Genomma | 13 | Suplementos |
| **+ 12 más** | **93** | (ver LISTA_COMPLETA_ARTICULOS.md) |
| **TOTAL** | **203** | — |

---

## 🎯 Casos de Uso

### Caso 1: Implementación Inicial
1. Lee **SETUP.md** (secciones 1-5)
2. Sigue instrucciones de configuración
3. Importa los 203 artículos (archivo CSV)
4. Ejecuta verificaciones

### Caso 2: Entender la Arquitectura
1. Lee **DESIGN.md** completamente
2. Revisa código en `models/` y `engines/`
3. Ejecuta tests: `odoo -m test -d <db> sale_discount_policy`

### Caso 3: Mantener/Actualizar Restricciones
1. Consulta **RESTRICTED_BRANDS.md**
2. Usa **LISTA_COMPLETA_ARTICULOS.md** como referencia
3. Para nuevos artículos: Actualiza CSV y re-importa

### Caso 4: Troubleshooting
1. Consulta sección **Troubleshooting** en **SETUP.md**
2. Revisa **DESIGN.md** para lógica de decisión
3. Ejecuta verificaciones en **Post-Installation Checks**

---

## 📋 Importancia de Cada Archivo

### SETUP.md — 🔴 CRÍTICO
**Por qué:** Instrucciones paso a paso. Sin esto, la implementación fallará.

### ARTICULOS_SIN_DESCUENTO.csv — 🔴 CRÍTICO
**Por qué:** Los 203 artículos específicos que deben estar excluidos. Sin este archivo importado correctamente, el sistema será inconsistente.

### DESIGN.md — 🟡 IMPORTANTE
**Por qué:** Si algo no funciona como se espera, aquí está la lógica. Esencial para debugging.

### RESTRICTED_BRANDS.md — 🟡 IMPORTANTE
**Por qué:** Referencia rápida de marcas. Necesario para mantener y actualizar restricciones.

### LISTA_COMPLETA_ARTICULOS.md — 🟢 REFERENCIAS
**Por qué:** Información detallada. Útil cuando necesitas buscar un artículo específico por EAN.

---

## 🔗 Enlaces Relacionados

- **Módulo:** `/medicinedepot/sale_discount_policy/`
- **Tests:** `/medicinedepot/sale_discount_policy/tests/`
- **Models:** `/medicinedepot/sale_discount_policy/models/`
- **Engine:** `/medicinedepot/sale_discount_policy/engines/discount_engine.py`

---

## ✅ Checklist Post-Implementación

- [ ] Módulo instalado (`sale_discount_policy` en Apps)
- [ ] Policy record configurado (almacenes autorizados)
- [ ] Clientes Farmacias Económicas etiquetados
- [ ] 203 artículos importados y etiquetados
- [ ] Test 1 pasado (discount aplicado a cliente FE, warehouse OK, producto genérico)
- [ ] Test 2 pasado (discount anulado para artículo restringido)
- [ ] Test 3 pasado (discount anulado para cliente diferente)
- [ ] Test 4 pasado (discount anulado para warehouse no autorizado)
- [ ] POS session verificado (discount visual en precios)
- [ ] Verificación report ejecutado (manual vs automático = 0 deltas)

---

## 📞 Soporte

**Para preguntas sobre:**
- Instalación → Ver **SETUP.md**
- Lógica técnica → Ver **DESIGN.md**
- Artículos específicos → Ver **LISTA_COMPLETA_ARTICULOS.md**
- Marcas → Ver **RESTRICTED_BRANDS.md**
- Bugs → Contacta al equipo de desarrollo con el output de troubleshooting

---

**Última actualización:** 2026-05-05  
**Módulo:** sale_discount_policy 19.0.1.0.0  
**Odoo:** 19.0+
