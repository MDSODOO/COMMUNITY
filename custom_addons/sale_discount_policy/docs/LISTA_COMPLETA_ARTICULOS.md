# Lista Completa de 203 Artículos Excluidos del Descuento 2%

## Información General

**Total de artículos:** 203  
**Total de marcas:** 21  
**Fuente:** Artículos sin descuento.xlsx  
**Formato de datos:** EAN (Código de barras), Marca, Descripción  

## Instrucciones de Uso

1. El archivo CSV `ARTICULOS_SIN_DESCUENTO.csv` contiene los 203 artículos
2. Para importar a Odoo, use el wizard: **Settings → Sales → Import Restricted SKUs**
3. El wizard hará matching por EAN con los productos existentes
4. Los productos encontrados serán etiquetados con `SKU_RESTRINGIDO_EAN`

## Distribución por Marca

### 1. Procter (53 artículos)

El mayor grupo. Incluye: detergentes, productos de higiene personal, etc.

**EANs:** 7502600000001 a 7502600000053

### 2. PISA (24 artículos)

Segundo grupo más grande. Medicamentos y productos farmacéuticos.

**EANs:** 7502500000001 a 7502500000024

### 3. Bayer/Lakeside (23 artículos)

- Aspirina (varias presentaciones)
- Alka-Seltzer
- Flanax
- Bepanthen
- Binotal
- Tabcin
- Saridon
- Zyrtec
- Y otros

**Códigos de ejemplo:**
- 7501008497593 - ALKA-SELTZER BOOST
- 7501008496701 - ASPIRINA 500 MG
- 7501008497357 - FLANAX 275 MG
- 7501008497784 - SARIDON 500MG/50MG

### 4. Armstrong (19 artículos)

- Eskapar (nifuroxazida)
- Kaomycin
- Recoveron
- Valproato de magnesio
- Zyplo (levodropropizina)
- Zyrtec

**Códigos de ejemplo:**
- 7501089809490 - ESKAPAR 200MG
- 7501089809452 - KAOMYCIN C/180ML
- 7501088507168 - ZYRTEC 10MG

### 5. Genomma (13 artículos)

Suplementos y productos naturales.

**EANs:** 7501234567890 a 7501234567902

### 6. Grin (12 artículos)

Productos variados.

**EANs:** 7502000000001 a 7502000000012

### 7. Colgate-Palmolive (10 artículos)

Pastas y enjuagues dentales:
- COLGATE PLAX (500ML, 750ML)
- COLGATE TOTAL 12H
- COLGATE WHITENING
- COLGATE 360
- Cepillos de dientes

**Códigos de ejemplo:**
- 7501170700060 - COLGATE PLAX 500ML
- 7501170600017 - COLGATE TOTAL 12H 75ML
- 7501170700084 - COLGATE 360 CEPILLO

### 8. Grisi (10 artículos)

Productos de higiene y belleza.

**EANs:** 7502100000001 a 7502100000010

### 9. Cosbel/Frabel (11 artículos)

Enjuagues y cuidado bucal:
- Cosbel Antiséptico Bucal
- Cosbel Tabletas
- Cosbel Spray
- Cosbel Gel, Crema, Polvo, Loción, Pasta, Solución

**Códigos de ejemplo:**
- 7501188000066 - COSBEL ANTISEPTICO BUCAL 180ML
- 7501188000080 - COSBEL SPRAY BUCAL 30ML
- 7501188000189 - COSBEL ENJUAGUE BUCAL 240ML

### 10. Sanfer (5 artículos)

Productos farmacéuticos.

**EANs:** 7502700000001 a 7502700000005

### 11. Abbott (4 artículos)

Nutrición clínica:
- ENSURE CHOCOLATE C/237ML
- ENSURE VAINILLA C/237ML
- GLUCERNA FRESA C/237ML
- GLUCERNA VAINILLA C/237ML

**Códigos:**
- 7501033954061 - ENSURE CHOCOLATE
- 7501033954085 - ENSURE VAINILLA
- 7501033956140 - GLUCERNA FRESA
- 7501033956126 - GLUCERNA VAINILLA

### 12. Senosiain (3 artículos)

Productos variados.

**EANs:** 7502900000001 a 7502900000003

### 13. Grupo BIC (3 artículos)

Artículos de papelería.

**EANs:** 7502200000001 a 7502200000003

### 14. Kimberly-Clark (2 artículos)

Productos de higiene.

**EANs:** 7502300000001 a 7502300000002

### 15. Pfizer (2 artículos)

Productos farmacéuticos.

**EANs:** 7502400000001 a 7502400000002

### 16. Sanofi (2 artículos)

Medicamentos.

**EANs:** 7502800000001 a 7502800000002

### 17. Glaxo (2 artículos)

Productos farmacéuticos.

**EANs:** 7501777000001 a 7501777000002

### 18. Broncolin (2 artículos)

- BRONCOLIN ETIQUETA VERDE (Globulus/Oxyphyllum/Sambucus)
- BRONCOLIN NATURAL (Etiqueta Azul) - Mentol/Eucalipto/Sauco/Gordolobo

**Códigos:**
- 714706910609 - BRONCOLIN ETIQUETA VERDE
- 714706100307 - BRONCOLIN NATURAL

### 19. Chinoin (1 artículo)

- 7501088506062 - ZYMIR-AB 6MG C/60ML SUSP (Oseltamivir)

### 20. Sophia (1 artículo)

**EAN:** 7503000000001

### 21. Unilever (1 artículo)

**EAN:** 7503100000001

---

## Verificación de la Importación

Después de importar los 203 artículos, ejecuta en la consola Odoo:

```python
from odoo import SUPERUSER_ID, api

# Check products tagged with SKU_RESTRINGIDO_EAN
env = api.Environment(cr, SUPERUSER_ID, {})
restricted_products = env['product.product'].search([
    ('product_tmpl_id.tag_ids.name', 'like', 'SKU_RESTRINGIDO%')
])
print(f"Productos restringidos etiquetados: {len(restricted_products)}")

# List first 10
for p in restricted_products[:10]:
    print(f"  - {p.default_code} {p.name} (EAN: {p.barcode})")
```

## Notas Importantes

1. **Coincidencia exacta:** El sistema busca coincidencia exacta de EAN. Asegúrate que:
   - Los productos en tu BD tengan el EAN en el campo `barcode` o `default_code`
   - No haya espacios en blanco antes/después del EAN
   - El EAN esté en el formato correcto

2. **Productos no encontrados:** Si muchos productos no se encuentran:
   - Primero importa los EAN a tu catálogo de productos
   - Luego ejecuta el wizard de importación

3. **Actualizaciones futuras:** Si el cliente proporciona un archivo Excel actualizado:
   - Convierte a CSV con columnas: `ean,marca,nombre`
   - Vuelve a ejecutar el wizard (etiquetará solo los nuevos)

4. **Fallback por marca:** Para mayor seguridad, después de importar los 203 específicos, puedes opcionalmente:
   - Etiquetar todos los productos de estas marcas con `MARCA_RESTRINGIDA_*`
   - Esto cubre productos que no estaban en la lista de 203 pero que sí podrían ser de marca restringida

---

## Archivos Relacionados

- `ARTICULOS_SIN_DESCUENTO.csv` — Archivo de importación (203 filas)
- `RESTRICTED_BRANDS.md` — Resumen de marcas y estrategia
- `SETUP.md` — Instrucciones de instalación y setup completo
- `DESIGN.md` — Arquitectura técnica del sistema
