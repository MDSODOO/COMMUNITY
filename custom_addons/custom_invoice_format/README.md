# custom_invoice_format — v19.0.1.15.0

**Categoría**: Accounting/Accounting | **Licencia**: LGPL-3

## Propósito

Formato personalizado de factura cliente CFDI 4.0 para Medicine Depot. Sobreescribe el template QWeb de factura de Odoo con el diseño visual corporativo (logotipo, colores, estructura de tabla, datos fiscales mexicanos).

## Dependencias

```python
depends = ['account', 'l10n_mx_edi']
```

## Modelos

### `account.move` (extensión)

Extiende el modelo base de facturas para incluir campos o lógica adicional requerida por el formato personalizado.

## Vistas / Reportes

| Archivo | Contenido |
|---|---|
| `views/report_invoice.xml` | Template QWeb del reporte de factura personalizado |

## Migraciones

| Versión | Acción |
|---|---|
| 19.0.1.1.0 | Formato base |
| 19.0.1.8.0 | Ajustes CFDI 4.0 |
| 19.0.1.9.0 | Correcciones de layout |
| 19.0.1.10.0 | Consolidación final |
| 19.0.1.13.0 | Corrección de tabla del complemento CFDI en wkhtmltopdf |
| 19.0.1.14.0 | Reubica totales/CFDI fuera del contenedor nativo angosto |
| 19.0.1.15.0 | Elimina XPath frágil de título nativo para evitar ParseError |

## Notas técnicas

- Requiere `l10n_mx_edi` para acceder a los campos CFDI (`l10n_mx_edi_cfdi_uuid`, complementos fiscales)
- El template QWeb hereda de `account.report_invoice_with_payments` y lo sobreescribe con `inherit_id`
- Score actual: 2/10 en auditoría previa — pendiente revisión de calidad

## Uso

Se activa automáticamente al imprimir cualquier factura de cliente. No requiere configuración adicional.

[⏳ MÓDULO(S) ACTUALIZADO(S)/AUDITADO(S) EN ESTE PASO: custom_invoice_format]
