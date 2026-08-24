# Workflow RPA: 04_Sync_Ordenes_Compra (n8n ↔ Odoo 19)

Flujo automatizado para recepción, validación y sincronización de Órdenes de Compra (PO) hacia Odoo 19 vía XML-RPC interno con notificación interactiva en Telegram.

---

## 🎯 Arquitectura del Flujo

```
[Proveedor B2B / API / Parser]
             │ (POST Webhook JSON)
             ▼
   [Webhook Inbound PO]
             │
   [Validar y Formatear Payload]
             │
   [Odoo Auth (XML-RPC: common/authenticate)]
             │
   [Check Auth] ──(Error)──► [Respond Auth Error (HTTP 401)]
             │ (OK)
   [Buscar Partner Odoo (search_read: res.partner por RFC/Nombre)]
             │
   [Resolver Partner]
             │
   [Crear PO en Odoo (create: purchase.order)]
             │
   [Preparar Notificación y Respuesta]
      ┌──────┴─────────────────────────────────┐
      ▼                                        ▼
[Telegram Alert B2B (con botón Odoo)]   [Respond Success (HTTP 201 JSON)]
```

---

## 🌐 Endpoint del Webhook en n8n

- **Producción:** `https://n8n.bodegademedicamentos.com/webhook/sync-purchase-order`
- **Test / Editor:** `https://n8n.bodegademedicamentos.com/webhook-test/sync-purchase-order`

---

## 📥 Ejemplo de Payload Entrante (JSON)

```json
{
  "partner_vat": "PFE140311874",
  "partner_name": "PFIZER S.A. DE C.V.",
  "partner_ref": "FAC-2026-9812",
  "date_order": "2026-08-10",
  "notes": "Entrega en Almacén Central Mérida - Pedido B2B Urgente",
  "lines": [
    {
      "product_code": "MED-001",
      "product_name": "Paracetamol 500mg Tab 20",
      "quantity": 500,
      "price_unit": 28.50
    },
    {
      "product_code": "MED-045",
      "product_name": "Amoxicilina 500mg Cap 12",
      "quantity": 200,
      "price_unit": 65.00
    }
  ]
}
```

---

## 📤 Respuesta Exitosa del Webhook (HTTP 201)

```json
{
  "status": "success",
  "message": "Orden de compra procesada correctamente",
  "data": {
    "po_id": 482,
    "po_url": "https://odoo.bodegademedicamentos.com/odoo/purchase/482",
    "partner": "PFIZER S.A. DE C.V.",
    "partner_ref": "FAC-2026-9812",
    "total_estimated": 27250.00,
    "total_lines": 2
  }
}
```

---

## 📲 Notificación generada en Telegram

El flujo envía un mensaje en HTML al grupo/canal configurado con el botón inline:

> 📦 **Nueva Orden de Compra sincronizada (RPA)**
> 
> **ID Odoo:** 482  
> **Proveedor:** PFIZER S.A. DE C.V.  
> **Folio/Ref:** FAC-2026-9812  
> **Líneas procesadas:** 2  
> **Total estimado:** $27,250.00 MXN  
> **Origen:** Webhook RPA n8n  
> 
> `[ 🔗 Ver en Odoo ]`
