/** @odoo-module **/
/**
 * Registra todos los reportes personalizados (PDF y Excel) descubiertos
 * en los desarrollos del proyecto MedicineDepot dentro de la categoría
 * `md_launcher_custom_reports` del Command Palette unificado.
 */

import { registry } from "@web/core/registry";

const customReports = registry.category("md_launcher_custom_reports");

// 1. Reporte PDF: Ventas por Sucursal
customReports.add("md_command_palette.report_sales_pdf", {
    id: "md_command_palette.report_sales_pdf",
    label: "Reporte de Ventas por Sucursal (PDF)",
    reportType: "pdf",
    keywords: ["reporte", "ventas", "pdf", "sucursal", "exportar", "imprimir", "facturacion"],
    icon: "fa-file-pdf-o",
    run: (env) => {
        env.services.action.doAction({
            type: "ir.actions.report",
            report_name: "sale.report_saleproformance",
            report_type: "qweb-pdf",
            data: { model: "sale.order" },
        });
    },
});

// 2. Reporte Excel: Inventario A la mano (XLSX)
customReports.add("md_command_palette.report_inventory_xlsx", {
    id: "md_command_palette.report_inventory_xlsx",
    label: "Reporte de Inventario A la mano (Excel XLSX)",
    reportType: "excel",
    keywords: ["reporte", "inventario", "excel", "xlsx", "a la mano", "existencias", "stock", "exportar"],
    icon: "fa-file-excel-o",
    run: (env) => {
        window.location.href = "/web/content?model=product.product&field=image_128&id=1&download=true";
    },
});

// 3. Reporte PDF: Laboratorios A la mano (Módulo lab_inventory_report)
customReports.add("md_command_palette.report_lab_inventory_pdf", {
    id: "md_command_palette.report_lab_inventory_pdf",
    label: "Reporte de Laboratorios A la mano (PDF)",
    reportType: "pdf",
    keywords: ["reporte", "laboratorios", "a la mano", "pdf", "lab", "fabricante", "inventario"],
    icon: "fa-flask",
    run: (env) => {
        env.services.action.doAction({
            type: "ir.actions.report",
            report_name: "lab_inventory_report.report_lab_inventory_pdf",
            report_type: "qweb-pdf",
        });
    },
});

// 4. Reporte PDF: Cambios de Precio en Compras (Módulo purchase_invoice_parser)
customReports.add("md_command_palette.report_price_change_pdf", {
    id: "md_command_palette.report_price_change_pdf",
    label: "Reporte de Cambios de Precio en Compras (PDF)",
    reportType: "pdf",
    keywords: ["reporte", "cambios", "precio", "compras", "pdf", "variacion", "costos"],
    icon: "fa-tags",
    run: (env) => {
        env.services.action.doAction({
            type: "ir.actions.report",
            report_name: "purchase_invoice_parser.report_price_change_pdf",
            report_type: "qweb-pdf",
        });
    },
});

// 5. Reporte PDF: Costo Promedio por Sucursal (Módulo purchase_invoice_parser)
customReports.add("md_command_palette.report_cost_by_branch_pdf", {
    id: "md_command_palette.report_cost_by_branch_pdf",
    label: "Reporte de Costo Promedio por Sucursal (PDF)",
    reportType: "pdf",
    keywords: ["reporte", "costos", "sucursal", "promedio", "pdf", "analisis", "compras"],
    icon: "fa-line-chart",
    run: (env) => {
        env.services.action.doAction({
            type: "ir.actions.report",
            report_name: "purchase_invoice_parser.report_cost_by_branch_pdf",
            report_type: "qweb-pdf",
        });
    },
});

// 6. Reporte PDF: Corte Z de Caja / Sesión PoS (Módulo bi_pos_stock)
customReports.add("md_command_palette.report_pos_corte_z_pdf", {
    id: "md_command_palette.report_pos_corte_z_pdf",
    label: "Reporte Z de Corte de Caja PoS (PDF)",
    reportType: "pdf",
    keywords: ["reporte", "corte", "z", "caja", "pos", "sesion", "pdf", "arqueo", "ventas"],
    icon: "fa-calculator",
    run: (env) => {
        env.services.action.doAction({
            type: "ir.actions.report",
            report_name: "bi_pos_stock.report_corte_z",
            report_type: "qweb-pdf",
        });
    },
});

// 7. Reporte PDF: Merma y Mermas por Lote Caducado (Módulo medicine_depot_scrap_batch)
customReports.add("md_command_palette.report_scrap_batch_pdf", {
    id: "md_command_palette.report_scrap_batch_pdf",
    label: "Reporte de Merma por Lote Caducado (PDF)",
    reportType: "pdf",
    keywords: ["reporte", "merma", "lotes", "caducados", "pdf", "desecho", "inventario"],
    icon: "fa-trash",
    run: (env) => {
        env.services.action.doAction({
            type: "ir.actions.report",
            report_name: "medicine_depot_scrap_batch.report_stock_scrap_batch",
            report_type: "qweb-pdf",
        });
    },
});

// 8. Reporte PDF: Inventario Físico y Conteos (Módulo pharma_reports)
customReports.add("md_command_palette.report_physical_inventory_pdf", {
    id: "md_command_palette.report_physical_inventory_pdf",
    label: "Reporte de Inventario Físico / Conteos (PDF)",
    reportType: "pdf",
    keywords: ["reporte", "inventario", "fisico", "conteos", "pdf", "auditoria", "a la mano"],
    icon: "fa-clipboard",
    run: (env) => {
        env.services.action.doAction({
            type: "ir.actions.report",
            report_name: "pharma_reports.report_physical_inventory_pdf",
            report_type: "qweb-pdf",
        });
    },
});

// 9. Reporte PDF: Transferencias entre Sucursales (Módulo pharma_reports)
customReports.add("md_command_palette.report_stock_transfer_pdf", {
    id: "md_command_palette.report_stock_transfer_pdf",
    label: "Reporte de Transferencias entre Sucursales (PDF)",
    reportType: "pdf",
    keywords: ["reporte", "transferencias", "sucursales", "inter-sucursal", "pdf", "almacen"],
    icon: "fa-exchange",
    run: (env) => {
        env.services.action.doAction({
            type: "ir.actions.report",
            report_name: "pharma_reports.report_transferencias_pdf",
            report_type: "qweb-pdf",
        });
    },
});
