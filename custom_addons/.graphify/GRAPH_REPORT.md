# Graph Report - .  (2026-07-22)

## Corpus Check
- Large corpus: 498 files · ~2,151,676 words. Semantic extraction will be expensive (many Claude tokens). Consider running on a subfolder, or use --no-semantic to run AST-only.

## Summary
- 3257 nodes · 5216 edges · 231 communities detected
- Extraction: 98% EXTRACTED · 2% INFERRED · 0% AMBIGUOUS · INFERRED: 100 edges (avg confidence: 0.52)
- Token cost: 0 input · 0 output
- Edge kinds: calls: 2025 · method: 1935 · contains: 611 · rationale_for: 318 · references: 97 · uses: 93 · inherits: 37 · imports: 36 · imports_from: 31 · conceptually_related_to: 28 · semantically_similar_to: 5


## Input Scope
- Requested: all
- Resolved: all (source: cli)
- Included files: 498 · Candidates: recursive
- Excluded: 0 untracked · 0 ignored · 4 sensitive · 0 missing committed
## God Nodes (most connected - your core abstractions)
1. `f` - 62 edges
2. `PosSession` - 57 edges
3. `c` - 50 edges
4. `TestPurchaseInvoiceImportWizardZipFlow` - 44 edges
5. `p` - 41 edges
6. `PurchaseInvoiceImportWizard` - 38 edges
7. `N` - 36 edges
8. `sr` - 36 edges
9. `TestProductionLotMigration` - 34 edges
10. `it` - 33 edges

## Surprising Connections (you probably didn't know these)
- `Guards pharma_invoice_layout_*_hide (7 guards)` --semantically_similar_to--> `Fix reporte Consolidado (header duplicado, pharma_reports guards)`  [INFERRED] [semantically similar]
  custom_invoice_format/CHANGELOG.md → medicine_depot_scrap_batch/CHANGELOG.md
- `Vulnerabilidad crítica: escritura pública sudo() por email en /afiliacion` --semantically_similar_to--> `Vulnerabilidad quant_text (exposición global de stock)`  [INFERRED] [semantically similar]
  medicine_depot_portal/AFILIACION_WORKFLOW_AUDIT.md → bi_pos_stock/README.md
- `Fix Dark Mode Backend (wizard CFDI)` --semantically_similar_to--> `Dark Mode Selector Fix (PDP/Similar Cards)`  [INFERRED] [semantically similar]
  purchase_invoice_parser/CHANGELOG.md → medicine_depot_website/CHANGELOG.md
- `Regla de negocio: 'A la mano' (nunca Disponible/Stock/Existencias)` --semantically_similar_to--> `Campo cantidad_la_mano (computed, stored)`  [INFERRED] [semantically similar]
  custom_shop_qty_selector/README.md → md_lots_management/README.md
- `Cascada FEFO de lotes en POS` --conceptually_related_to--> `lot_selection (Motor central de selección FEFO)`  [INFERRED]
  bi_pos_stock/CHANGELOG.md → lot_selection/README.md

## Hyperedges (group relationships)
- **Convención de terminología 'A la mano' aplicada transversalmente** — regla_a_la_mano, md_lots_management_cantidad_la_mano_field, lab_inventory_report_module, custom_shop_qty_selector_module [EXTRACTED 0.90]
- **Patrón de bug: módulo faltante en guards de layout pharma_reports causa header duplicado** — pharma_reports_module, custom_invoice_format_pharma_invoice_layout_guards, medicine_depot_scrap_batch_consolidado_report_fix [INFERRED 0.80]
- **Pila de trazabilidad de lotes FEFO (venta, POS, bajas)** — lot_selection_module, bi_pos_stock_fefo_lot_cascade, medicine_depot_scrap_batch_module, md_lots_management_module [INFERRED 0.75]
- **Auditoría global de módulos (commit 678aa01)** — medicine_depot_website_module, pharma_reports_module, sale_lot_report_module [EXTRACTED 0.95]
- **Patrón de bug: selector de Dark Mode inconsistente con DOM Odoo 19** — medicine_depot_website_dark_mode_fix, purchase_invoice_parser_dark_mode_fix, backend_dark_mode_audit_doc [EXTRACTED 0.90]
- **Módulos bridge de compatibilidad hacia pharma_reports** — pharma_reports_module, purchase_order_report_module, sale_lot_report_module [INFERRED 0.85]

## Communities

### Community 0 - "Community 0"
Cohesion: 0.05
Nodes (5): at, dt, fe, ft, it

### Community 1 - "Community 1"
Cohesion: 0.07
Nodes (8): PosSession, Dirección de la empresa sin el nombre al inicio (evita duplicado con company_nam, Órdenes de devolución (total negativo) listadas por separado.          Reproduce, Notas de apertura/cierre de caja registradas en la(s) sesión(es)., Desglose de IVA por tasa: base gravable e impuesto.          Se calcula con ``co, Conciliación esperado/contado/diferencia por método de pago.          Para los m, ReportCorteZDocument, ReportSaleDetails

### Community 2 - "Community 2"
Cohesion: 0.07
Nodes (2): a, f

### Community 3 - "Community 3"
Cohesion: 0.07
Nodes (15): PurchaseInvoiceImportWizard, PurchaseInvoiceImportWizardLine, Popula lot_ids desde el campo Descripcion de cada concepto CFDI.         Usado p, Pre-detecta el formato del proveedor desde el nombre del archivo XML., Lee los precios actuales de supplierinfo ANTES de crear la OC.          Devuelve, Detecta cambios de precio respecto a un snapshot y genera notificaciones., Lotes del wizard con nombre asignado (listos para usarse en la OC).          Ret, BRUDIFARMA: toda la información de lotes está en el XML.         Prioridad: Adde (+7 more)

### Community 4 - "Community 4"
Cohesion: 0.05
Nodes (4): K, ke, or, Qe

### Community 5 - "Community 5"
Cohesion: 0.07
Nodes (2): be, lt

### Community 6 - "Community 6"
Cohesion: 0.08
Nodes (9): Controller, MedicineDepotPublicController, Devuelve el partner de la compañía activa en el website, con fallback al usuario, Public website routes for the Bento redesign., Lowercase + strip company prefixes so 'MDS MERIDA' → 'merida'., Add lat/lng + state_key + city to a branch card dict., WebsiteSaleShopAccess, MedicineDepotPharmacovigilanceReport (+1 more)

### Community 7 - "Community 7"
Cohesion: 0.08
Nodes (26): BiPosStockUiController, _branch_warehouse_id(), CartBarcodeScannerController, _lot_expiration_cutoff(), lot_filtered_stock_qty_map(), Almacen de la sucursal asignada al cliente autenticado, si aplica.      La sucur, Cantidad 'A la mano' (On Hand) para un product.product, con el         mismo cri, Cutoff datetime for lots allowed in eCommerce (today + 6 months). (+18 more)

### Community 8 - "Community 8"
Cohesion: 0.06
Nodes (23): PosSession, ProductProduct, Only expose the minimum safe fields needed for display purposes., FIXED SECURITY FLAW: Original used self.search([]) with no filters.          The, Return branch-scoped stock quantities for this POS session.          Called from, Compute per-product stock quantities scoped to this POS's branch locations., # NOTE: this used to point at the Odoo Studio model 'x_line' (field, Single RPC entry point for all stock data needed at POS session open.          R (+15 more)

### Community 9 - "Community 9"
Cohesion: 0.08
Nodes (10): ProductTemplate, Mismo criterio que stock.lot._get_qty_a_la_mano_locations         (md_lots_manag, {related_record.id: unidades vendidas} agregando la venta de cada         produc, FEFO-sorted lot list para self (un solo producto): [{lot_id,         lot_name, e, Return the field name linking products to their active ingredient/substance., RPC del boton dedicado "detalle de lotes FEFO" en el Kanban de         Inventari, Return the field name linking products to the "line" model.          Acepta tant, Abre el detalle regulatorio COFEPRIS en un modal de solo lectura.          Equiv (+2 more)

### Community 10 - "Community 10"
Cohesion: 0.09
Nodes (17): LotStockResolver, Búsqueda robusta con conversión a global (patrón multiempresa).          1. Busc, Busca un lote por producto y nombre.         Intenta: exact case-insensitive → c, Devuelve el lote existente o lo crea (patrón get-or-create multiempresa)., Pre-carga todos los lotes de los productos dados en una sola query.         lot_, Resuelve stock.lot en batch para evitar el patrón N+1.      Uso:         resolve, PurchaseOrderBuilder, Crea un purchase.order a partir del estado actual del wizard de importación CFDI (+9 more)

### Community 11 - "Community 11"
Cohesion: 0.07
Nodes (4): l, m, rr(), u

### Community 12 - "Community 12"
Cohesion: 0.09
Nodes (6): ProductionLot, Extensión del modelo stock.lot con personalizaciones     que anteriormente estab, Patrón get-or-create: si el lote ya existe para (name, product_id, company_id),, Actualiza campos auditables al modificar el lote., Valida que las fechas de vencimiento tengan sentido., Abre la lista de quants filtrada por este lote.

### Community 13 - "Community 13"
Cohesion: 0.07
Nodes (21): _clean_product_name(), PickingType, PosConfig, PosOrder, ProductProduct, CHANGED: No longer sends raw stock_location_id or quant_text.         Branch sto, Return a product name stripped of its barcode prefix.      Odoo's default ``disp, Triggers branch-scoped real-time stock sync to POS sessions on confirmed moves. (+13 more)

### Community 14 - "Community 14"
Cohesion: 0.15
Nodes (3): he, te, ue

### Community 15 - "Community 15"
Cohesion: 0.10
Nodes (15): MedicineDepotPortal, Extiende el Portal del Cliente para alimentar el dashboard Bento., Construye valores de campos selection Studio del portal., Valida formato de email; delega a utils.is_valid_email que usa tools.email_norma, Calcula estado de afiliación y faltantes documentales del partner., Valores de plantilla para el dashboard Bento.          Se calculan exclusivament, Portal home: añade valores del bento DESPUÉS de super() para         que /my/doc, Extiende /my/account para manejar fields Studio + alerta de expediente. (+7 more)

### Community 16 - "Community 16"
Cohesion: 0.08
Nodes (5): Localiza Virtual Locations/Scrap con cuatro niveles de fallback         para gar, Ancla siempre la ubicación de bajas a Virtual Locations/Scrap,         sin excep, Compatibilidad entre versiones de Odoo:         - Algunas usan stock.location.is, StockScrapBatch, StockScrapBatchLine

### Community 17 - "Community 17"
Cohesion: 0.06
Nodes (5): Tamaño inválido cae al default (115) sin lanzar excepción., Campo dummy que silencia AttributeError de l10n_mx_edi en Odoo 19., Proveedores mexicanos suelen usar coma como separador decimal., Tests de lógica pura del módulo custom_invoice_format.      Cubre métodos que no, TestCustomInvoiceFormatLogic

### Community 18 - "Community 18"
Cohesion: 0.11
Nodes (3): br(), gr, Vr

### Community 19 - "Community 19"
Cohesion: 0.09
Nodes (7): AVATAR_PALETTE, BRANCH_COLORS, FOLDERS, FULL_FIELDS, hashColor(), MdMailClient, MESSAGE_FIELDS

### Community 20 - "Community 20"
Cohesion: 0.10
Nodes (6): AccountMove, AccountMoveInherit, Fallback lot extraction via stock moves when native API returns empty., Return CFDI values for the printed invoice without assuming field names., Split long SAT strings so wkhtmltopdf keeps them inside the cell., Map Odoo's invoice lot values back to the main invoice lines.          POS/globa

### Community 21 - "Community 21"
Cohesion: 0.13
Nodes (1): TestPurchaseInvoiceImportWizardZipFlow

### Community 22 - "Community 22"
Cohesion: 0.11
Nodes (2): we, ze

### Community 23 - "Community 23"
Cohesion: 0.11
Nodes (17): CART_SUBMIT_SELECTOR, _cartGuardScope(), _cartSubmitButtons(), _ensureWishlistVisible(), EXACT_LABEL, _findCartSubmitTarget(), _guardEvent(), _hasInvalidCustomQty() (+9 more)

### Community 24 - "Community 24"
Cohesion: 0.10
Nodes (2): pe, wr

### Community 25 - "Community 25"
Cohesion: 0.10
Nodes (15): _get_product_line_display(), _get_product_line_field_name(), PurchasePriceNotification, Devuelve el field name en product.template que apunta a md.product.line.      "L, Aplica el precio nuevo al supplierinfo del producto y marca como aplicado., Marca como leída o archiva la notificación según su estado., Botón del formulario: aplica el precio sobre el registro actual.          Envolt, Botón del formulario: marca como leída o elimina el registro actual. (+7 more)

### Community 26 - "Community 26"
Cohesion: 0.11
Nodes (1): sr

### Community 27 - "Community 27"
Cohesion: 0.12
Nodes (11): CFDIDocument, CFDILine, CFDIParser, Router de estrategias por RFC para desacoplar estructuras proveedor-específicas., QUIFAMESA (QFM861010BL0):         - Usa estructura estándar en cfdi:Concepto., BRUDIFARMA (BRU971010227):         - Mantiene parseo fiscal desde Concepto., Parsea la fecha del CFDI de forma robusta. Retorna string ISO YYYY-MM-DD., Detecta nodos de Retenciones en el comprobante y los contabiliza. (+3 more)

### Community 28 - "Community 28"
Cohesion: 0.11
Nodes (3): ct, pt, wt

### Community 29 - "Community 29"
Cohesion: 0.12
Nodes (5): constructor(), decodeBitmap(), ge, gt, lr

### Community 30 - "Community 30"
Cohesion: 0.12
Nodes (3): er, ir(), tr

### Community 31 - "Community 31"
Cohesion: 0.17
Nodes (3): jt, Qt, zt

### Community 32 - "Community 32"
Cohesion: 0.10
Nodes (2): ReplenishmentLine, StockScreen

### Community 33 - "Community 33"
Cohesion: 0.14
Nodes (19): _bindBridgeEvents(), _buildInfoHTML(), _esc(), _focusBranch(), _focusBranchSet(), _focusState(), _initLeafletMap(), _initMap() (+11 more)

### Community 34 - "Community 34"
Cohesion: 0.11
Nodes (12): PortalPickingVisibility, Extiende la visibilidad de órdenes en /my/orders y añade /my/pickings.      FUNC, Detalle de un albarán con validación de acceso por partner., Domain hermético para pickings del usuario portal.          Incluye:         - E, Añade contador de albaranes a la tarjeta de inicio /my., Lista paginada de albaranes del usuario portal., CustomerPortal, base_domain del super() debe incorporarse al dominio resultante. (+4 more)

### Community 35 - "Community 35"
Cohesion: 0.11
Nodes (1): N

### Community 36 - "Community 36"
Cohesion: 0.14
Nodes (2): mt, x

### Community 37 - "Community 37"
Cohesion: 0.14
Nodes (2): et, st

### Community 38 - "Community 38"
Cohesion: 0.16
Nodes (3): ht, vt, xt

### Community 39 - "Community 39"
Cohesion: 0.19
Nodes (1): pr

### Community 40 - "Community 40"
Cohesion: 0.14
Nodes (1): ve

### Community 41 - "Community 41"
Cohesion: 0.13
Nodes (2): Nr, yr

### Community 42 - "Community 42"
Cohesion: 0.10
Nodes (1): xe

### Community 43 - "Community 43"
Cohesion: 0.09
Nodes (12): La exportación Excel de inventario físico debe estar registrada., El reporte de Orden de Venta debe estar registrado., El reporte de Orden de Compra debe estar registrado., El reporte de Transferencias debe estar registrado., El paperformat de ventas pharma debe existir en la BD., El paperformat de compras pharma debe existir en la BD., El template QWeb de OV debe estar registrado como ir.ui.view., Verifica que los reportes farmacéuticos estén correctamente registrados.      Re (+4 more)

### Community 44 - "Community 44"
Cohesion: 0.13
Nodes (22): Commit 678aa01: auditoría global de módulos, Commit af30ff8: fusión lot_selection + pharma_reports, Auditoría custom_invoice_format — Score 2/10 (F), Ocultar complemento fiscal CFDI 4.0 en documentos de proveedor, custom_invoice_format (Formato de Factura CFDI 4.0), Migración purga de PDF cacheado (invoice_pdf_report_file), Guards pharma_invoice_layout_*_hide (7 guards), lot_selection (Motor central de selección FEFO) (+14 more)

### Community 45 - "Community 45"
Cohesion: 0.20
Nodes (2): cr, mr

### Community 46 - "Community 46"
Cohesion: 0.12
Nodes (1): p

### Community 47 - "Community 47"
Cohesion: 0.11
Nodes (2): I, T

### Community 48 - "Community 48"
Cohesion: 0.16
Nodes (6): formatExpiryDate(), getDaysLeft(), getExpiryColorClass(), isShortExpiry(), lotLabelWithExpiry(), parseExpiryDate()

### Community 49 - "Community 49"
Cohesion: 0.17
Nodes (1): ee

### Community 50 - "Community 50"
Cohesion: 0.14
Nodes (6): MdKanbanLotDetailPopup, MdLotDetailButton, formatExpiryDate(), getDaysLeft(), getExpiryColorClass(), parseExpiryDate()

### Community 51 - "Community 51"
Cohesion: 0.18
Nodes (16): _activateCard(), _emit(), _filterByState(), _findCardByCity(), _findPinByCity(), _highlightNearestBranch(), _normalizeBranchToken(), _setupCopyButtons() (+8 more)

### Community 52 - "Community 52"
Cohesion: 0.16
Nodes (1): ie

### Community 53 - "Community 53"
Cohesion: 0.14
Nodes (2): dr, Q

### Community 54 - "Community 54"
Cohesion: 0.19
Nodes (12): AddendaLot, AddendaParserRegistry, BaseAddendaParser, BrudifarmaAddendaParser, get_addenda_parser(), Convierte formato 'DD.MM.YYYY' a datetime.date., Retorna el parser de Addenda para el RFC dado, o None si no hay implementación., Interfaz base para parsers de Addenda CFDI identificados por RFC de emisor. (+4 more)

### Community 55 - "Community 55"
Cohesion: 0.11
Nodes (7): Regla de negocio: el campo de inventario físico debe llamarse 'A la mano'., En un entorno con md_product_lines instalado, la columna detectada         debe, Cada uno de los 4 laboratorios de negocio debe tener un mapeo         explícito, La vista SQL debe ser consultable, esté vacía o con datos reales., Si md_product_lines está instalado y hay productos con         product_line_id p, Tests para report.lab.inventory — modelo SQL view con detección dinámica.      M, TestLabInventoryReportModel

### Community 56 - "Community 56"
Cohesion: 0.12
Nodes (18): AddendaParserRegistry (patrón de auto-registro propuesto), BrudifarmaAddendaParser (Addenda BRUDIFARMA), Commit c84e84f: revertir bloqueo estricto de IVA, CFDIParser (services/cfdi_parser.py), KnownRFC (constante centralizada propuesta), LotStockResolver (servicio propuesto), LotParserProvider (estrategias PDF: Generic/Quifamesa), ProductMatcher (barcode/código/nombre → product.product) (+10 more)

### Community 57 - "Community 57"
Cohesion: 0.23
Nodes (1): rt

### Community 58 - "Community 58"
Cohesion: 0.20
Nodes (1): MdLauncher

### Community 59 - "Community 59"
Cohesion: 0.11
Nodes (3): AfiliacionTemplateTest, Prueba smoke de POST multipart para validar guardado sin crash., Pruebas unitarias para la página de afiliación profesional.

### Community 60 - "Community 60"
Cohesion: 0.13
Nodes (3): de, h, tt

### Community 61 - "Community 61"
Cohesion: 0.13
Nodes (2): g, w

### Community 62 - "Community 62"
Cohesion: 0.15
Nodes (2): ne, re

### Community 63 - "Community 63"
Cohesion: 0.21
Nodes (1): Xr

### Community 64 - "Community 64"
Cohesion: 0.17
Nodes (1): LotSelectionPopup

### Community 65 - "Community 65"
Cohesion: 0.17
Nodes (7): EcommerceOrderPopup, addLineToOrder(), _buildProductToTemplateMap(), getBranchStockForProduct(), getPosStoreRef(), processServerData(), _recomputeStockByTmpl()

### Community 66 - "Community 66"
Cohesion: 0.28
Nodes (1): je

### Community 67 - "Community 67"
Cohesion: 0.13
Nodes (7): HttpCase, Tests HTTP para el flujo de farmacovigilancia., Tests HTTP para el flujo de afiliación., TestAfiliacionEndpoint, TestPharmacovigilanciaFlow, Regression: GET /shop/<slug> must not raise AccessError on stock.warehouse     f, TestPublicShopProductPage

### Community 68 - "Community 68"
Cohesion: 0.19
Nodes (10): _countFilled(), _onFileChange(), _onGeneralInput(), _onPrivacyChange(), _onSubmit(), _refreshAffiliacion(), _setFileStatus(), _showStep() (+2 more)

### Community 69 - "Community 69"
Cohesion: 0.22
Nodes (4): _sample_cfdi(), TestAddendaParser, TestZipExtractor, _zip_bytes()

### Community 70 - "Community 70"
Cohesion: 0.15
Nodes (15): Bug: company_id de sesión/website en vez del warehouse resuelto, Badge de % de descuento (o_md_discount_badge), custom_shop_qty_selector (Qty pill + Badge A la mano), Bug: onchange inline pierde carrera contra onChangeAttribute nativo, Bug: request.website.get_current_pricelist() no existe en Odoo 19, Ordenar filtros por popularidad de ventas (POS+web, 90 días), Bug: filtros custom de /shop nunca filtraban el listado real, md_bento_theme (Tema Bento-box + Glassmorphism) (+7 more)

### Community 71 - "Community 71"
Cohesion: 0.19
Nodes (1): b

### Community 72 - "Community 72"
Cohesion: 0.16
Nodes (2): c, s

### Community 73 - "Community 73"
Cohesion: 0.17
Nodes (1): CfdiUploadField

### Community 74 - "Community 74"
Cohesion: 0.18
Nodes (5): readableTextColor(), TAG_COLOR_PALETTE, tagColorStyle(), HOMOLOGACION_LABELS, RegulatoryDetailPopup

### Community 75 - "Community 75"
Cohesion: 0.13
Nodes (9): PosOrderLine, PosSession, Extend get_existing_lots() to include expiration_date and sort FEFO.      The st, Return ALL lots for a product in this branch, sorted FEFO.          Called on-de, Return a flat dict of every available lot for all tracked POS products., Override: adds expiration_date to each lot dict and applies FEFO sort., Autoritativo server-side: rechaza vender mas de lo "A la mano"         (On Hand), Add lot expiry data to POS session RPC surface.      Two public methods:       - (+1 more)

### Community 76 - "Community 76"
Cohesion: 0.21
Nodes (8): _enrich(), _map_url(), _normalize(), Invalidar caché cuando cambien datos de sucursales., Return the stock.warehouse assigned to the authenticated partner's branch., Retorna JSON de sucursales para el widget de Google Maps. Resultado cacheado por, Website, _whatsapp_url()

### Community 77 - "Community 77"
Cohesion: 0.19
Nodes (6): BrudifarmaProvider, _extract_text(), GenericProvider, LotParserProvider, QuifamesaProvider, Extrae texto del PDF usando pdfplumber (preferido) o pypdf como fallback.

### Community 78 - "Community 78"
Cohesion: 0.18
Nodes (1): ae

### Community 79 - "Community 79"
Cohesion: 0.20
Nodes (2): ar, d

### Community 80 - "Community 80"
Cohesion: 0.16
Nodes (1): me

### Community 81 - "Community 81"
Cohesion: 0.22
Nodes (2): Para cada movimiento con lote preseleccionado en la OC:           - Sincroniza l, StockPicking

### Community 82 - "Community 82"
Cohesion: 0.15
Nodes (14): Regla de negocio: columna 'A la mano', price_change_report_wizard.py (modelo), Reporte Final de Auditoría (docs/audits), Migración Bento del wizard 'Importar XML de Proveedor', Auditoría de Engine purchase_invoice_parser (Score 65/10 B), Plan de Mejoras purchase_invoice_parser (auditoría 2026-05-19), purchase_invoice_parser (CFDI → Orden de Compra), Bug x_studio_linea_id vs x_studio_line (+6 more)

### Community 83 - "Community 83"
Cohesion: 0.15
Nodes (13): Refactorización de Seguridad Multi-Sucursal (branch_stock), PosSession._compute_branch_stock(), Riesgo de deadlock en cierre simultáneo de sucursales, Restricción multi-sucursal 100% frontend (falsa seguridad), _get_branch_stock_locations() (fuente única de verdad), Sync Post-Commit de stock (postcommit), Vulnerabilidad quant_text (exposición global de stock), Vulnerabilidad StockLocation sin filtro (_load_pos_data_search_read) (+5 more)

### Community 84 - "Community 84"
Cohesion: 0.21
Nodes (9): _get_or_create_tag(), MdWebsiteApi, MdWebsiteAutocomplete, POST /web/medicd/submit — crea oportunidad CRM para el programa MedicD desde el, Override to allow cross-origin calls in staging/preview environments., Busca o crea una etiqueta CRM por nombre exacto. Usa sudo() para acceso público., POST /web/afiliacion/submit — crea oportunidad CRM con documentos adjuntos desde, _valid_email() (+1 more)

### Community 85 - "Community 85"
Cohesion: 0.27
Nodes (1): fr

### Community 86 - "Community 86"
Cohesion: 0.21
Nodes (1): y

### Community 87 - "Community 87"
Cohesion: 0.18
Nodes (1): j

### Community 88 - "Community 88"
Cohesion: 0.26
Nodes (3): Return the field name linking product.template to md.product.line         (módul, ReportPhysicalInventoryDocument, StockQuant

### Community 89 - "Community 89"
Cohesion: 0.21
Nodes (6): partner_ref de la OC debe aparecer en ref de la factura generada., OC sin partner_ref no debe sobrescribir campos de la factura., Dos OCs con refs distintas → factura con 'REF-A / REF-B'., Dos OCs con el mismo partner_ref → ref sin duplicados., Tests de propagación de partner_ref de OC a factura de proveedor., TestPurchaseVendorRef

### Community 90 - "Community 90"
Cohesion: 0.15
Nodes (4): Tests para endpoints JSON del shop., Tests para _md_get_active_ingredients y _md_get_product_lines., TestLotFilteredStockQtyMap, TestShopJsonEndpoints

### Community 91 - "Community 91"
Cohesion: 0.21
Nodes (1): bt

### Community 92 - "Community 92"
Cohesion: 0.32
Nodes (1): ce

### Community 93 - "Community 93"
Cohesion: 0.23
Nodes (1): kt

### Community 94 - "Community 94"
Cohesion: 0.23
Nodes (1): r()

### Community 95 - "Community 95"
Cohesion: 0.21
Nodes (5): initCardStagger(), initCounters(), initScrollReveals(), observerRegistry, registerObserver()

### Community 96 - "Community 96"
Cohesion: 0.17
Nodes (4): PurchaseInvoiceImportWizardLot, Retorna (partner, confidence, method).         company_id: filtrar por compañía, En CFDI el RFC es único y determinista — no se necesita fuzzy matching.     Estr, SupplierMatcher

### Community 97 - "Community 97"
Cohesion: 0.18
Nodes (5): PurchaseOrder, PurchaseOrderLine, Añade partner_ref de la OC a los valores de la factura de proveedor.          Ll, Notifica cambios MANUALES de precio en líneas de OCs ya confirmadas.          La, Consolida referencias cuando varias OCs se agrupan en una sola factura.

### Community 98 - "Community 98"
Cohesion: 0.24
Nodes (5): Detecta qué columna de product_template apunta a md.product.line., Acción planificada: se ejecuta el último día de cada mes.          Base lista pa, Log información de diagnóstico detallada al cargar el modelo.          Ayuda a i, ReportLabInventory, ReportLabInventoryPDF

### Community 99 - "Community 99"
Cohesion: 0.30
Nodes (7): _is_ignored_zip_entry(), _looks_like_pdf(), _normalise_name(), _normalise_token(), XmlPdfPair, ZipContents, ZipExtractor

### Community 100 - "Community 100"
Cohesion: 0.21
Nodes (6): Confirmar la OV propaga el lot_id a las líneas de movimiento., Tests del motor FEFO de lot_selection.     Regla de negocio: inventario físico =, El dominio debe incluir lotes con cantidad A la mano > 0., Productos sin seguimiento → dominio vacío (no aplica FEFO)., Al hacer onchange, debe seleccionarse el lote con caducidad más próxima., TestLotSelectionDomain

### Community 101 - "Community 101"
Cohesion: 0.20
Nodes (1): le

### Community 102 - "Community 102"
Cohesion: 0.20
Nodes (1): PriceNotificationMenu

### Community 103 - "Community 103"
Cohesion: 0.24
Nodes (4): initBranchesGeo(), initGeolocation(), initQRCodes(), initStaticPinInteractions()

### Community 104 - "Community 104"
Cohesion: 0.33
Nodes (9): _closeDrawer(), _debounce(), destroy(), _handleResize(), _openDrawer(), _setupDrawer(), start(), _teardownDrawer() (+1 more)

### Community 105 - "Community 105"
Cohesion: 0.18
Nodes (11): lab_inventory_report (Reporte de inventario A la mano por laboratorio), Auditoría ODOO19_COMPATIBILITY_AUDIT (md_lots_management), Campo cantidad_la_mano (computed, stored), Consulta Handheld (vista Kanban móvil para escáner), Grupo de seguridad group_lots_handheld_user, Bug: groups_id renombrado a group_ids en Odoo 19, md_lots_management (Gestión de Lotes — migración de Studio), Vista huérfana en BD (ir.ui.view id=4383, sin dueño en ningún módulo) (+3 more)

### Community 106 - "Community 106"
Cohesion: 0.18
Nodes (1): LotDetailPopup

### Community 107 - "Community 107"
Cohesion: 0.31
Nodes (4): assignLotToLine(), getFefoLots(), getFefoLotsForTemplate(), sortFefo()

### Community 108 - "Community 108"
Cohesion: 0.20
Nodes (5): BiPosSupplierSnapshot, BiPosSupplierSnapshotLine, ImportBfSnapshotWizard, Devuelve dict para join O(1) por barcode y por vendor_code., Importa un Excel BF desde un ir.attachment ya subido.          Detecta automátic

### Community 109 - "Community 109"
Cohesion: 0.22
Nodes (3): PurchaseOrderLine, UI-only: pre-llena la fecha con la del lote seleccionado SOLO si         el camp, Escribe la fecha de la línea de OC directo en stock.lot.         Única fuente de

### Community 110 - "Community 110"
Cohesion: 0.36
Nodes (10): _advance(), destroy(), _expireCampaignSlides(), _goTo(), _setPaused(), start(), _startTimer(), _stopTimer() (+2 more)

### Community 111 - "Community 111"
Cohesion: 0.18
Nodes (6): Un usuario no logueado debe ser redirigido al login al intentar acceder., Un usuario no logueado debe ser redirigido al login al intentar acceder a /my/be, Un usuario logueado puede acceder a /my/dashboard y /my/bento, renderizando el B, Un usuario logueado puede acceder a /my/account y ver las tarjetas Bento del for, Tests unitarios y HTTP para el redireccionamiento al dashboard Bento y navbar., TestBentoDashboardRedirect

### Community 112 - "Community 112"
Cohesion: 0.24
Nodes (5): Producto con tracking='lot' sin ningún lote resuelto desde el         CFDI/PDF (, Producto configurado con IVA de compra 16% en Odoo, pero el CFDI         trae un, Hard Stops: bloquear la creación de la Orden de Compra cuando el CFDI     trae u, Excepción intencional: un CFDI que declara explícitamente 0%/Exento         para, TestInvoiceParserHardStops

### Community 113 - "Community 113"
Cohesion: 0.24
Nodes (5): Tests de validación de caducidad en órdenes de compra., Confirmar OC con lote vencido debe lanzar UserError., Confirmar OC con lote sin fecha de caducidad debe lanzar UserError., La fecha en la línea de OC debe sincronizarse al stock.lot., TestLotSelectionPurchase

### Community 114 - "Community 114"
Cohesion: 0.18
Nodes (6): Test 3: El campo usuario_creacion se asigna automáticamente, Configuración inicial para todos los tests., Test 4: fecha_entrada tiene fecha default, Tests unitarios para la migración de Studio → Código puro en stock.lot, Test 2: qty_a_la_mano se computa correctamente, TestProductionLotMigration

### Community 115 - "Community 115"
Cohesion: 0.18
Nodes (3): MdWebsiteApiTest, GET en endpoint POST debe devolver 405 o redirigir, no 200., Segundo envío con mismo email debe devolver 409.

### Community 116 - "Community 116"
Cohesion: 0.38
Nodes (9): _arch_column_type(), _decode_arch_payload(), _is_residual_delivery_copy(), migrate(), _patch_arch(), _patch_payload(), _remove_node(), _report_action_refs() (+1 more)

### Community 117 - "Community 117"
Cohesion: 0.38
Nodes (9): _audit_website_scoped_products(), _has_columns(), migrate(), Post-migration 19.0.2.10.0 - conservative shop publication sync.  This migration, Best-effort ACL sync for optional Studio models.      Missing or inconsistent St, _repair_base_unit_count(), _republish_global_shop_products(), _sync_studio_acls() (+1 more)

### Community 118 - "Community 118"
Cohesion: 0.22
Nodes (10): Auditoría Dark Mode Backend (2026-07-01), crm (Odoo CRM, dependencia externa), MdWebsiteAutocomplete Inheritance Fix, Bento/Glassmorphism Design System, CHANGELOG 2.md (versión duplicada/desactualizada), Dark Mode Selector Fix (PDP/Similar Cards), medicine_depot_website (Website Module), Public REST API (products/affiliate) (+2 more)

### Community 119 - "Community 119"
Cohesion: 0.20
Nodes (1): se

### Community 120 - "Community 120"
Cohesion: 0.20
Nodes (1): e()

### Community 121 - "Community 121"
Cohesion: 0.24
Nodes (1): nt

### Community 123 - "Community 123"
Cohesion: 0.29
Nodes (1): ut

### Community 124 - "Community 124"
Cohesion: 0.20
Nodes (1): O

### Community 125 - "Community 125"
Cohesion: 0.27
Nodes (1): ye

### Community 126 - "Community 126"
Cohesion: 0.38
Nodes (9): closeModal(), handleScannedBarcode(), onOpenScanner(), openModal(), setModalStatus(), startCamera(), stopCamera(), submitManualCode() (+1 more)

### Community 127 - "Community 127"
Cohesion: 0.20
Nodes (5): Tests para la anulación de posición fiscal fronteriza cuando la sucursal emisora, Caso 1: Compañía emisora no fronteriza (Mérida 97070) + cliente fronterizo (Chet, Caso 2: Compañía emisora fronteriza (Chetumal 77000) + cliente fronterizo (Chetu, Caso 3: Posición fiscal sin restricción geográfica (zip_from/zip_to vacíos)., TestFiscalPositionBorderZone

### Community 128 - "Community 128"
Cohesion: 0.20
Nodes (4): Item 7 · /login responde 200 y sirve el formulario nativo intacto.          Si e, Item 22 · la vista de sucursales expone los datos de horario que el         badg, Smoke tests for Phase 1 website templates., TestPhase1Templates

### Community 129 - "Community 129"
Cohesion: 0.20
Nodes (1): TestLotParserProvider

### Community 130 - "Community 130"
Cohesion: 0.39
Nodes (8): _arch_column_type(), _decode_arch_payload(), migrate(), _patch_arch(), _patch_payload(), Compatibility cleanup for obsolete has_packages QWeb guards., _remove_node(), _write_view()

### Community 131 - "Community 131"
Cohesion: 0.22
Nodes (1): oe

### Community 132 - "Community 132"
Cohesion: 0.22
Nodes (4): Cantidad 'A la mano' (On Hand) para el producto de esta linea,         con el mi, Solo escribe en lot_domain, nunca en lot_id.         Filtra por existencia a la, Auto-selecciona el lote con caducidad más próxima (FEFO)., SaleOrderLine

### Community 133 - "Community 133"
Cohesion: 0.22
Nodes (4): Calcula el estado consolidado de envío a partir de los pickings.          Lógica, SaleOrder, SaleOrderInherit, SaleOrderLineInherit

### Community 134 - "Community 134"
Cohesion: 0.22
Nodes (3): _HW_PROXY_404_PATTERNS, _NETWORK_ERROR_MESSAGES, _SILENT_URL_PATTERNS

### Community 135 - "Community 135"
Cohesion: 0.22
Nodes (4): Test para el método pos_custom_screen_entrypoint, Test para el método pos_custom_screen_entrypoint con query string, Test para el método pos_custom_screen_entrypoint con múltiples rutas, TestBiPosStock

### Community 136 - "Community 136"
Cohesion: 0.22
Nodes (4): TestLabInventoryPdfReport, Direct check: the public user must be able to read free_qty via sudo()     witho, TestFreeQtySudoForPublic, TransactionCase

### Community 137 - "Community 137"
Cohesion: 0.22
Nodes (4): Test 22: producto global crea lote global aunque llegue una compañía., Test 23: producto de compañía también crea lote global., Test 24: lote global visible usando otra compañía activa., Test 27: company_id no toma la compañía activa por defecto.

### Community 138 - "Community 138"
Cohesion: 0.22
Nodes (1): TestStockScrapBatch

### Community 139 - "Community 139"
Cohesion: 0.43
Nodes (7): _count_model_dependencies(), _ensure_access(), _has_critical_dependencies(), migrate(), Upgrade: rellena lot_expiration_date desde stock.lot para líneas     existentes., _table_count(), _table_exists()

### Community 140 - "Community 140"
Cohesion: 0.46
Nodes (7): _has_columns(), migrate(), Post-migration 19.0.2.11.0 - defensive retry for production upgrades.  This vers, _repair_base_unit_count(), _republish_global_shop_products(), _sync_studio_acls(), _table_exists()

### Community 141 - "Community 141"
Cohesion: 0.32
Nodes (7): _disable_native_mx_invoice_views(), post_init_hook(), post_load(), Desactiva las vistas QWeb de `l10n_mx_edi` heredadas sobre     `account.report_i, Hook por proceso (sin env). No tocamos BD aqui., Force invoice/bill report actions to use the same A4 paperformat.      Odoo 19 k, _synchronize_invoice_report_actions()

### Community 142 - "Community 142"
Cohesion: 0.25
Nodes (1): ot

### Community 143 - "Community 143"
Cohesion: 0.36
Nodes (2): HandheldKanbanController, handheldKanbanView

### Community 144 - "Community 144"
Cohesion: 0.43
Nodes (6): _forceEagerProductImages(), _normalizeLabels(), _setupCardTilt(), _setupMarqueePause(), _setupReveal(), start()

### Community 145 - "Community 145"
Cohesion: 0.25
Nodes (3): MdProductLine, ProductLine, Habilita md.product.line como modelo cargable al POS (mixin     pos.load.mixin)

### Community 146 - "Community 146"
Cohesion: 0.43
Nodes (3): ProductMatcher, Estrategia de matching para conceptos CFDI:     1. Barcode exacto (NoIdentificac, Retorna (product, confidence, method).

### Community 147 - "Community 147"
Cohesion: 0.38
Nodes (3): clearPosCaches(), shouldBypassPosServiceWorker(), unregisterPosServiceWorkers()

### Community 148 - "Community 148"
Cohesion: 0.29
Nodes (7): Dark mode POS (bi_pos_stock), Cascada FEFO de lotes en POS, Pantalla Low Stock / Replenishment (reabastecimiento), bi_pos_stock (Multi-Branch POS Stock Module), orderline_discount_patch.js (getEffectiveDiscountInfo), Fusión visual de lotes en el ticket (mergeReceiptLotLines), Reporte Z Farmacéutico (correo + Excel)

### Community 149 - "Community 149"
Cohesion: 0.29
Nodes (1): URL_NORMALIZATION

### Community 150 - "Community 150"
Cohesion: 0.38
Nodes (2): PosSession, Agrega md.active.substance y md.product.line a la lista de modelos     que el PO

### Community 151 - "Community 151"
Cohesion: 0.38
Nodes (3): getLotColor(), getLotExpiry(), getLotExpiryLabel()

### Community 152 - "Community 152"
Cohesion: 0.57
Nodes (6): cascadeLotFill(), _cascadeToNextLots(), getLineLot(), _setValue(), updateQuantityNumber(), getLotStock()

### Community 153 - "Community 153"
Cohesion: 0.29
Nodes (3): Test 19: Crear lote con cantidad actualiza A la mano, Test 20: El wizard actualiza A la mano y devuelve notificación, Test 21: get-or-create incrementa A la mano

### Community 154 - "Community 154"
Cohesion: 0.29
Nodes (2): PharmacovigilanceTemplateTest, Pruebas smoke para la página pública de farmacovigilancia.

### Community 155 - "Community 155"
Cohesion: 0.43
Nodes (2): Tests unitarios para _get_affiliation_state., TestAffiliationState

### Community 156 - "Community 156"
Cohesion: 0.33
Nodes (5): _post_init_create_studio_acls(), Install/uninstall hooks for custom_shop_qty_selector.  Las ACLs publicas para lo, Crea ir.model.access publica (read) por cada modelo Studio presente., Limpieza explicita por seguridad — Odoo ya las elimina via ir.model.data., _uninstall_cleanup_studio_acls()

### Community 157 - "Community 157"
Cohesion: 0.33
Nodes (1): EcommerceOrdersScreen

### Community 160 - "Community 160"
Cohesion: 0.33
Nodes (1): yt

### Community 161 - "Community 161"
Cohesion: 0.47
Nodes (3): applyDarkClass(), isDarkStored(), MdDarkModeToggle

### Community 162 - "Community 162"
Cohesion: 0.53
Nodes (4): getStack(), promoteAlert(), shouldPromote(), start()

### Community 163 - "Community 163"
Cohesion: 0.40
Nodes (2): _onSubmit(), _showMsg()

### Community 164 - "Community 164"
Cohesion: 0.40
Nodes (4): AccountFiscalPositionInherit, _is_zip_in_border_zone(), Comprueba si un código postal cae en un rango de Franja Fronteriza.      Args:, Calcula la posición fiscal, anulando la posición fronteriza si la sucursal emiso

### Community 165 - "Community 165"
Cohesion: 0.40
Nodes (3): Send a real-time bus.bus notification to the matching POS session     whenever a, Push an ECOMMERCE_ORDER message to every open POS session         whose warehous, SaleOrder

### Community 166 - "Community 166"
Cohesion: 0.47
Nodes (2): Redirige automáticamente a los usuarios de Consulta Handheld a esa     vista al, ResUsers

### Community 167 - "Community 167"
Cohesion: 0.53
Nodes (1): StockMoveLine

### Community 168 - "Community 168"
Cohesion: 0.47
Nodes (4): _flushOpenOrdersToIDB(), _onVisibilityChange(), ready(), _registerOrderPersistenceListeners()

### Community 169 - "Community 169"
Cohesion: 0.40
Nodes (4): clean(), is_valid_email(), Valida formato de email. Usa tools.email_normalize cuando está disponible., Extrae, limpia y escapa HTML de un campo de un dict POST.

### Community 170 - "Community 170"
Cohesion: 0.40
Nodes (2): MdActiveSubstance, Habilita md.active.substance como modelo cargable al POS (mixin     pos.load.mix

### Community 171 - "Community 171"
Cohesion: 0.60
Nodes (1): PriceNotificationReportWizard

### Community 172 - "Community 172"
Cohesion: 0.40
Nodes (1): MdRegulatoryReview

### Community 174 - "Community 174"
Cohesion: 0.40
Nodes (1): Odoo Shell helper para auditar y limpiar lotes globales duplicados.  Uso desde l

### Community 175 - "Community 175"
Cohesion: 0.50
Nodes (2): _applyBadgeStyles(), setup()

### Community 176 - "Community 176"
Cohesion: 0.40
Nodes (4): clean_lot_name(), parse_date(), Limpia un nombre de lote extrayendo prefijos 'Lote:' y sufijos de caducidad., Parsea una fecha con mes numérico o nombre español abreviado.

### Community 177 - "Community 177"
Cohesion: 0.50
Nodes (1): Z

### Community 178 - "Community 178"
Cohesion: 0.83
Nodes (3): bindSubmitSpinner(), ensureGlassLoginIsland(), start()

### Community 179 - "Community 179"
Cohesion: 0.67
Nodes (2): _buildBar(), start()

### Community 180 - "Community 180"
Cohesion: 0.50
Nodes (2): IrActionsServer, Backport Odoo 19 fix: keep all server-action variables on one env.

### Community 181 - "Community 181"
Cohesion: 0.50
Nodes (1): LotAssignCompanyWizard

### Community 182 - "Community 182"
Cohesion: 0.50
Nodes (1): PriceChangeReportWizard

### Community 183 - "Community 183"
Cohesion: 0.50
Nodes (2): ProductTemplate, Cargamos los campos regulatorios en product.template porque ahi es     donde viv

### Community 184 - "Community 184"
Cohesion: 0.50
Nodes (1): MedicineDepotScrapHistoryLegacy

### Community 185 - "Community 185"
Cohesion: 0.50
Nodes (1): MedicineDepotScrapSummary2025

### Community 186 - "Community 186"
Cohesion: 0.83
Nodes (3): _setValue(), _stockLimitError(), updateQuantityNumber()

### Community 187 - "Community 187"
Cohesion: 0.50
Nodes (1): formatQty()

### Community 188 - "Community 188"
Cohesion: 0.50
Nodes (1): DEPRECIADO: Este módulo es un shim de compatibilidad para la API histórica. Usar

### Community 189 - "Community 189"
Cohesion: 1.00
Nodes (2): _find_target_action(), migrate()

### Community 190 - "Community 190"
Cohesion: 1.00
Nodes (2): _find_target_action(), migrate()

### Community 191 - "Community 191"
Cohesion: 0.67
Nodes (2): migrate(), Drop stale generated customer-invoice PDFs.      Odoo stores the rendered invoic

### Community 192 - "Community 192"
Cohesion: 0.67
Nodes (1): Pre-migration 19.0.2.12.0 — sanear product_product.base_unit_count.  Corre ANTES

### Community 193 - "Community 193"
Cohesion: 0.67
Nodes (1): Post-migration 19.0.2.9.0 — fix shop 404s + base_unit_count warning.  Contexto:

### Community 194 - "Community 194"
Cohesion: 0.67
Nodes (2): post_init_hook(), Desvincula los reportes nativos de pos.session del menú de impresión.      Despu

### Community 197 - "Community 197"
Cohesion: 0.67
Nodes (1): MD_CUSTOM_FILTER_NAMES

### Community 198 - "Community 198"
Cohesion: 0.67
Nodes (2): _post_init_hook(), Pobla lot_expiration_date desde stock.lot.expiration_date en líneas     existent

### Community 199 - "Community 199"
Cohesion: 0.67
Nodes (2): post_init_hook(), Corrige registros existentes cuya ubicacion de bajas no sea Virtual Locations/Sc

### Community 200 - "Community 200"
Cohesion: 0.67
Nodes (2): LegacyPosOrder, LegacyPosOrderLine

### Community 201 - "Community 201"
Cohesion: 0.67
Nodes (1): MdPosOrderUnified

### Community 202 - "Community 202"
Cohesion: 0.67
Nodes (1): ResPartnerProviderProfile

### Community 203 - "Community 203"
Cohesion: 0.67
Nodes (1): ResCompany

### Community 204 - "Community 204"
Cohesion: 0.67
Nodes (1): StockMove

### Community 205 - "Community 205"
Cohesion: 0.67
Nodes (2): _post_init_compute_delivery_status(), Recalcula portal_delivery_status para todas las órdenes existentes.      Al inst

### Community 206 - "Community 206"
Cohesion: 0.67
Nodes (1): ReportScrapBatchConsolidated

### Community 207 - "Community 207"
Cohesion: 1.00
Nodes (2): can_be_merged_with(), getLineLotName()

### Community 208 - "Community 208"
Cohesion: 0.67
Nodes (1): LotALaManoWizard

### Community 219 - "Community 219"
Cohesion: 1.00
Nodes (1): MdNameAbbreviation

### Community 220 - "Community 220"
Cohesion: 1.00
Nodes (1): ResConfigSettings

### Community 221 - "Community 221"
Cohesion: 1.00
Nodes (1): ResPartner

### Community 222 - "Community 222"
Cohesion: 1.00
Nodes (1): Compatibility bridge for legacy module name `purchase_lot_selection`.

### Community 223 - "Community 223"
Cohesion: 1.00
Nodes (1): Compatibility bridge for legacy module name `purchase_order_report`.

### Community 224 - "Community 224"
Cohesion: 1.00
Nodes (2): purchase_vendor_ref, Propagación de partner_ref a factura de proveedor

### Community 225 - "Community 225"
Cohesion: 1.00
Nodes (2): Lógica de zona fronteriza (IVA reducido), sale_account_custom

### Community 226 - "Community 226"
Cohesion: 1.00
Nodes (1): Compatibility bridge for legacy module name `sale_lot_report`.

### Community 227 - "Community 227"
Cohesion: 1.00
Nodes (1): Compatibility bridge for legacy module name `sale_lot_selection`.

### Community 228 - "Community 228"
Cohesion: 1.00
Nodes (1): BiWarningPopup

### Community 230 - "Community 230"
Cohesion: 1.00
Nodes (1): Test 5: Validar que fecha_vencimiento_estimado <= expiration_date

### Community 231 - "Community 231"
Cohesion: 1.00
Nodes (1): Test 6: El estado del lote solo acepta valores válidos

### Community 232 - "Community 232"
Cohesion: 1.00
Nodes (1): Test 7: Las notas de calidad se guardan correctamente

### Community 233 - "Community 233"
Cohesion: 1.00
Nodes (1): Test 8: Códigos de proveedor y referencias de compra

### Community 234 - "Community 234"
Cohesion: 1.00
Nodes (1): Test 9: Búsqueda de lotes por estado_lote

### Community 235 - "Community 235"
Cohesion: 1.00
Nodes (1): Test 10: Búsqueda de lotes por código de proveedor

### Community 236 - "Community 236"
Cohesion: 1.00
Nodes (1): Test 11: Verificar que timestamps de auditoría se registran

### Community 237 - "Community 237"
Cohesion: 1.00
Nodes (1): Test 12: Verificar que los permisos de lectura funcionan

### Community 238 - "Community 238"
Cohesion: 1.00
Nodes (1): Test 13: fecha_ultima_modificacion refleja write_date del lote

### Community 239 - "Community 239"
Cohesion: 1.00
Nodes (1): Test 14: qty_a_la_mano debe ser 0 si no hay quants

### Community 240 - "Community 240"
Cohesion: 1.00
Nodes (1): Test 15: Búsqueda de lotes vencidos

### Community 241 - "Community 241"
Cohesion: 1.00
Nodes (1): Configuración antes de cada test.

### Community 242 - "Community 242"
Cohesion: 1.00
Nodes (1): Test 16: Los lotes se crean con active=True por defecto

### Community 243 - "Community 243"
Cohesion: 1.00
Nodes (1): Test 17: Archivar un lote cambia active=False y lo oculta de búsquedas normales

### Community 244 - "Community 244"
Cohesion: 1.00
Nodes (1): Test 18: get-or-create retorna lote archivado sin crear duplicado

### Community 245 - "Community 245"
Cohesion: 1.00
Nodes (1): Test 25: create multi reutiliza el lote global dentro del mismo lote.

### Community 246 - "Community 246"
Cohesion: 1.00
Nodes (1): Test 26: lot_name se resuelve contra el lote global existente.

### Community 247 - "Community 247"
Cohesion: 1.00
Nodes (1): Test 1: Crear lote con campos personalizados

## Ambiguous Edges - Review These
- `Auditoría de Engine purchase_invoice_parser (Score 65/10 B)` → `Reporte Final de Auditoría (docs/audits)`  [AMBIGUOUS]
  purchase_invoice_parser/CLAUDE.md · relation: conceptually_related_to

## Knowledge Gaps
- **378 isolated node(s):** `Return a valid HTTP response for custom POS screen deep links.      The stock sc`, `Desvincula los reportes nativos de pos.session del menú de impresión.      Despu`, `Send a real-time bus.bus notification to the matching POS session     whenever a`, `Push an ECOMMERCE_ORDER message to every open POS session         whose warehous`, `Extend get_existing_lots() to include expiration_date and sort FEFO.      The st` (+373 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **Thin community `Community 2`** (2 nodes): `a`, `f`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 5`** (2 nodes): `be`, `lt`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 21`** (1 nodes): `TestPurchaseInvoiceImportWizardZipFlow`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 22`** (2 nodes): `we`, `ze`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 24`** (2 nodes): `pe`, `wr`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 26`** (1 nodes): `sr`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 32`** (2 nodes): `ReplenishmentLine`, `StockScreen`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 35`** (1 nodes): `N`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 36`** (2 nodes): `mt`, `x`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 37`** (2 nodes): `et`, `st`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 39`** (1 nodes): `pr`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 40`** (1 nodes): `ve`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 41`** (2 nodes): `Nr`, `yr`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 42`** (1 nodes): `xe`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 45`** (2 nodes): `cr`, `mr`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 46`** (1 nodes): `p`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 47`** (2 nodes): `I`, `T`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 49`** (1 nodes): `ee`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 52`** (1 nodes): `ie`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 53`** (2 nodes): `dr`, `Q`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 57`** (1 nodes): `rt`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 58`** (1 nodes): `MdLauncher`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 61`** (2 nodes): `g`, `w`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 62`** (2 nodes): `ne`, `re`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 63`** (1 nodes): `Xr`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 64`** (1 nodes): `LotSelectionPopup`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 66`** (1 nodes): `je`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 71`** (1 nodes): `b`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 72`** (2 nodes): `c`, `s`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 73`** (1 nodes): `CfdiUploadField`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 78`** (1 nodes): `ae`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 79`** (2 nodes): `ar`, `d`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 80`** (1 nodes): `me`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 81`** (2 nodes): `Para cada movimiento con lote preseleccionado en la OC:           - Sincroniza l`, `StockPicking`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 85`** (1 nodes): `fr`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 86`** (1 nodes): `y`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 87`** (1 nodes): `j`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 91`** (1 nodes): `bt`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 92`** (1 nodes): `ce`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 93`** (1 nodes): `kt`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 94`** (1 nodes): `r()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 101`** (1 nodes): `le`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 102`** (1 nodes): `PriceNotificationMenu`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 106`** (1 nodes): `LotDetailPopup`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 119`** (1 nodes): `se`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 120`** (1 nodes): `e()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 121`** (1 nodes): `nt`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 123`** (1 nodes): `ut`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 124`** (1 nodes): `O`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 125`** (1 nodes): `ye`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 129`** (1 nodes): `TestLotParserProvider`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 131`** (1 nodes): `oe`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 138`** (1 nodes): `TestStockScrapBatch`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 142`** (1 nodes): `ot`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 143`** (2 nodes): `HandheldKanbanController`, `handheldKanbanView`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 149`** (1 nodes): `URL_NORMALIZATION`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 150`** (2 nodes): `PosSession`, `Agrega md.active.substance y md.product.line a la lista de modelos     que el PO`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 154`** (2 nodes): `PharmacovigilanceTemplateTest`, `Pruebas smoke para la página pública de farmacovigilancia.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 155`** (2 nodes): `Tests unitarios para _get_affiliation_state.`, `TestAffiliationState`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 157`** (1 nodes): `EcommerceOrdersScreen`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 160`** (1 nodes): `yt`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 163`** (2 nodes): `_onSubmit()`, `_showMsg()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 166`** (2 nodes): `Redirige automáticamente a los usuarios de Consulta Handheld a esa     vista al`, `ResUsers`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 167`** (1 nodes): `StockMoveLine`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 170`** (2 nodes): `MdActiveSubstance`, `Habilita md.active.substance como modelo cargable al POS (mixin     pos.load.mix`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 171`** (1 nodes): `PriceNotificationReportWizard`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 172`** (1 nodes): `MdRegulatoryReview`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 174`** (1 nodes): `Odoo Shell helper para auditar y limpiar lotes globales duplicados.  Uso desde l`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 175`** (2 nodes): `_applyBadgeStyles()`, `setup()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 177`** (1 nodes): `Z`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 179`** (2 nodes): `_buildBar()`, `start()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 180`** (2 nodes): `IrActionsServer`, `Backport Odoo 19 fix: keep all server-action variables on one env.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 181`** (1 nodes): `LotAssignCompanyWizard`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 182`** (1 nodes): `PriceChangeReportWizard`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 183`** (2 nodes): `ProductTemplate`, `Cargamos los campos regulatorios en product.template porque ahi es     donde viv`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 184`** (1 nodes): `MedicineDepotScrapHistoryLegacy`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 185`** (1 nodes): `MedicineDepotScrapSummary2025`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 187`** (1 nodes): `formatQty()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 188`** (1 nodes): `DEPRECIADO: Este módulo es un shim de compatibilidad para la API histórica. Usar`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 189`** (2 nodes): `_find_target_action()`, `migrate()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 190`** (2 nodes): `_find_target_action()`, `migrate()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 191`** (2 nodes): `migrate()`, `Drop stale generated customer-invoice PDFs.      Odoo stores the rendered invoic`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 192`** (1 nodes): `Pre-migration 19.0.2.12.0 — sanear product_product.base_unit_count.  Corre ANTES`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 193`** (1 nodes): `Post-migration 19.0.2.9.0 — fix shop 404s + base_unit_count warning.  Contexto:`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 194`** (2 nodes): `post_init_hook()`, `Desvincula los reportes nativos de pos.session del menú de impresión.      Despu`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 197`** (1 nodes): `MD_CUSTOM_FILTER_NAMES`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 198`** (2 nodes): `_post_init_hook()`, `Pobla lot_expiration_date desde stock.lot.expiration_date en líneas     existent`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 199`** (2 nodes): `post_init_hook()`, `Corrige registros existentes cuya ubicacion de bajas no sea Virtual Locations/Sc`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 200`** (2 nodes): `LegacyPosOrder`, `LegacyPosOrderLine`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 201`** (1 nodes): `MdPosOrderUnified`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 202`** (1 nodes): `ResPartnerProviderProfile`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 203`** (1 nodes): `ResCompany`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 204`** (1 nodes): `StockMove`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 205`** (2 nodes): `_post_init_compute_delivery_status()`, `Recalcula portal_delivery_status para todas las órdenes existentes.      Al inst`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 206`** (1 nodes): `ReportScrapBatchConsolidated`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 207`** (2 nodes): `can_be_merged_with()`, `getLineLotName()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 208`** (1 nodes): `LotALaManoWizard`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 219`** (1 nodes): `MdNameAbbreviation`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 220`** (1 nodes): `ResConfigSettings`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 221`** (1 nodes): `ResPartner`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 222`** (1 nodes): `Compatibility bridge for legacy module name `purchase_lot_selection`.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 223`** (1 nodes): `Compatibility bridge for legacy module name `purchase_order_report`.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 224`** (2 nodes): `purchase_vendor_ref`, `Propagación de partner_ref a factura de proveedor`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 225`** (2 nodes): `Lógica de zona fronteriza (IVA reducido)`, `sale_account_custom`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 226`** (1 nodes): `Compatibility bridge for legacy module name `sale_lot_report`.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 227`** (1 nodes): `Compatibility bridge for legacy module name `sale_lot_selection`.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 228`** (1 nodes): `BiWarningPopup`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 230`** (1 nodes): `Test 5: Validar que fecha_vencimiento_estimado <= expiration_date`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 231`** (1 nodes): `Test 6: El estado del lote solo acepta valores válidos`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 232`** (1 nodes): `Test 7: Las notas de calidad se guardan correctamente`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 233`** (1 nodes): `Test 8: Códigos de proveedor y referencias de compra`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 234`** (1 nodes): `Test 9: Búsqueda de lotes por estado_lote`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 235`** (1 nodes): `Test 10: Búsqueda de lotes por código de proveedor`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 236`** (1 nodes): `Test 11: Verificar que timestamps de auditoría se registran`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 237`** (1 nodes): `Test 12: Verificar que los permisos de lectura funcionan`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 238`** (1 nodes): `Test 13: fecha_ultima_modificacion refleja write_date del lote`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 239`** (1 nodes): `Test 14: qty_a_la_mano debe ser 0 si no hay quants`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 240`** (1 nodes): `Test 15: Búsqueda de lotes vencidos`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 241`** (1 nodes): `Configuración antes de cada test.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 242`** (1 nodes): `Test 16: Los lotes se crean con active=True por defecto`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 243`** (1 nodes): `Test 17: Archivar un lote cambia active=False y lo oculta de búsquedas normales`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 244`** (1 nodes): `Test 18: get-or-create retorna lote archivado sin crear duplicado`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 245`** (1 nodes): `Test 25: create multi reutiliza el lote global dentro del mismo lote.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 246`** (1 nodes): `Test 26: lot_name se resuelve contra el lote global existente.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 247`** (1 nodes): `Test 1: Crear lote con campos personalizados`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **What is the exact relationship between `Auditoría de Engine purchase_invoice_parser (Score 65/10 B)` and `Reporte Final de Auditoría (docs/audits)`?**
  _Edge tagged AMBIGUOUS (relation: conceptually_related_to) - confidence is low._
- **Why does `TestPurchaseInvoiceImportWizardZipFlow` connect `Community 21` to `Community 69`, `Community 54`, `Community 27`, `Community 10`, `Community 77`, `Community 146`, `Community 99`, `Community 136`?**
  _High betweenness centrality (0.019) - this node is a cross-community bridge._
- **Why does `f` connect `Community 2` to `Community 63`, `Community 30`, `Community 72`?**
  _High betweenness centrality (0.012) - this node is a cross-community bridge._
- **Why does `MedicineDepotPortal` connect `Community 15` to `Community 34`, `Community 67`, `Community 155`?**
  _High betweenness centrality (0.008) - this node is a cross-community bridge._
- **Are the 12 inferred relationships involving `TestPurchaseInvoiceImportWizardZipFlow` (e.g. with `AddendaLot` and `BrudifarmaAddendaParser`) actually correct?**
  _`TestPurchaseInvoiceImportWizardZipFlow` has 12 INFERRED edges - model-reasoned connections that need verification._
- **What connects `Return a valid HTTP response for custom POS screen deep links.      The stock sc`, `Desvincula los reportes nativos de pos.session del menú de impresión.      Despu`, `Send a real-time bus.bus notification to the matching POS session     whenever a` to the rest of the system?**
  _378 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Community 0` be split into smaller, more focused modules?**
  _Cohesion score 0.0525879917184265 - nodes in this community are weakly interconnected._