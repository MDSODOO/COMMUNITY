# purchase_order_report — v19.0.99.0.0 (Bridge)

**Categoría**: Reporting | **Tipo**: Módulo bridge de compatibilidad

## Propósito

Alias de compatibilidad hacia `pharma_reports`. Instalaciones antiguas que dependían de `purchase_order_report` siguen funcionando sin cambios de configuración.

**Toda la lógica real está en [`pharma_reports`](../pharma_reports/README.md).**

```python
depends = ['pharma_reports']
```

La versión `99` indica que este es un módulo bridge permanente — no se espera evolución funcional.

[⏳ MÓDULO(S) ACTUALIZADO(S)/AUDITADO(S) EN ESTE PASO: purchase_order_report]
