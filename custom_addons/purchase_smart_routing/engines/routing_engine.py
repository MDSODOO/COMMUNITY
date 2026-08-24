"""
Motor de enrutamiento de compras — lógica pura, sin dependencias de Odoo.
Soporta N proveedores con umbral de precio configurable.

v2.0 — sustituye purchase_router_engine.py (solo 2 proveedores, umbral fijo).
       Ahora trabaja con N proveedores y el umbral es un parámetro configurable.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

_logger = logging.getLogger(__name__)


@dataclass
class SupplierOffer:
    """Oferta de un proveedor para un producto concreto."""
    partner_id: int
    partner_name: str
    supplierinfo_id: int
    effective_price: float
    available_stock: float


@dataclass
class SupplierAssignment:
    """Resultado de asignación de cantidad a un proveedor específico."""
    partner_id: int
    supplierinfo_id: int
    qty: float
    price: float
    stock: float
    rank: int
    is_winner: bool
    motivo: str
    # Motivos posibles:
    #   OK           — asignado al proveedor óptimo con stock suficiente
    #   UMBRAL       — mantenido con proveedor actual (diff < threshold_pct)
    #   STOCK_INSUF  — proveedor primario con stock insuficiente (hay fallback)
    #   FALLBACK     — proveedor de respaldo que cubre el faltante
    #   NO_ASIGNADO  — proveedor con existencia a la mano pero con demanda ya cubierta
    #   PARCIAL      — última asignación que no cubre la demanda completa


@dataclass
class AllocationResult:
    """Resultado completo de la asignación para un único producto."""
    product_id: int
    qty_demanded: float
    assignments: list  # list[SupplierAssignment]
    notes: str = ""

    @property
    def qty_satisfied(self) -> float:
        return sum(a.qty for a in self.assignments)

    @property
    def qty_unsatisfied(self) -> float:
        return max(self.qty_demanded - self.qty_satisfied, 0.0)


def allocate_product(
    product_id: int,
    qty_demanded: float,
    offers: list,  # list[SupplierOffer]
    current_partner_id: Optional[int] = None,
    threshold_pct: float = 0.06,
) -> AllocationResult:
    """
    Asigna qty_demanded entre los proveedores con existencia a la mano (N proveedores).

    Algoritmo:
      1. Filtrar ofertas con precio > 0 y stock > 0 → "con existencia a la mano".
      2. Ordenar ofertas con existencia a la mano por effective_price ASC.
      3. Lógica de umbral: si el proveedor actual NO es el más barato
         pero la diferencia porcentual < threshold_pct, lo reposiciona en #1
         para evitar cambios de proveedor por diferencias menores al umbral.
      4. Asignación greedy: asignar qty al proveedor #1 hasta agotar su stock,
         luego fallback al #2, al #3, etc.

    Args:
        product_id:        ID del producto en Odoo (solo para trazabilidad).
        qty_demanded:      Cantidad total demandada.
        offers:            Lista de SupplierOffer con existencia a la mano para este producto.
        current_partner_id: Partner de la OC original. Usado en la lógica de umbral.
        threshold_pct:     Fracción mínima de diferencia de precio para cambiar
                           proveedor. Por defecto 6% (0.06).

    Returns:
        AllocationResult con la distribución óptima y notas de auditoría.
    """
    available = [
        o for o in offers
        if o.effective_price > 0 and o.available_stock > 0
    ]

    if not available:
        return AllocationResult(
            product_id=product_id,
            qty_demanded=qty_demanded,
            assignments=[],
            notes="SIN_PROVEEDOR: ninguna oferta con precio y existencia a la mano",
        )

    # Ordenar por precio efectivo ASC
    available.sort(key=lambda o: o.effective_price)
    umbral_aplicado = False

    # Lógica de umbral: si el proveedor actual no es el más barato
    # pero la diferencia con el más barato es menor al umbral, mantenerlo como primero.
    if current_partner_id and len(available) >= 2:
        cheapest = available[0]
        if cheapest.partner_id != current_partner_id:
            current_offer = next(
                (o for o in available if o.partner_id == current_partner_id), None
            )
            if current_offer and current_offer.effective_price > 0:
                diff_pct = (
                    (current_offer.effective_price - cheapest.effective_price)
                    / current_offer.effective_price
                )
                if diff_pct < threshold_pct:
                    available.remove(current_offer)
                    available.insert(0, current_offer)
                    umbral_aplicado = True

    remaining = qty_demanded
    assignments = []
    notes_parts = []

    for rank, offer in enumerate(available, start=1):
        if remaining <= 0:
            assignments.append(SupplierAssignment(
                partner_id=offer.partner_id,
                supplierinfo_id=offer.supplierinfo_id,
                qty=0.0,
                price=offer.effective_price,
                stock=offer.available_stock,
                rank=rank,
                is_winner=False,
                motivo="NO_ASIGNADO",
            ))
            continue

        qty_to_assign = min(remaining, offer.available_stock)
        is_winner = (rank == 1 and qty_to_assign > 0)

        if umbral_aplicado and rank == 1:
            motivo = "UMBRAL"
        elif rank == 1 and qty_to_assign < remaining:
            motivo = "STOCK_INSUF"
            notes_parts.append(
                f"Stock insuficiente en {offer.partner_name}: "
                f"{offer.available_stock:.0f}/{remaining:.0f} uds"
            )
        elif rank > 1 and qty_to_assign > 0:
            motivo = f"FALLBACK→{offer.partner_name[:12]}"
            notes_parts.append(
                f"Fallback → {offer.partner_name}: {qty_to_assign:.0f} uds"
            )
        else:
            motivo = "OK"

        assignments.append(SupplierAssignment(
            partner_id=offer.partner_id,
            supplierinfo_id=offer.supplierinfo_id,
            qty=qty_to_assign,
            price=offer.effective_price,
            stock=offer.available_stock,
            rank=rank,
            is_winner=is_winner,
            motivo=motivo,
        ))
        remaining -= qty_to_assign

    # Calcular ahorro vs segundo proveedor (precio de lista original, sin reordenamiento por umbral)
    original_sorted = sorted(offers, key=lambda o: o.effective_price)
    priced_offers = [o for o in original_sorted if o.effective_price > 0]
    if len(priced_offers) >= 2:
        ahorro_unit = priced_offers[1].effective_price - priced_offers[0].effective_price
        winner_assign = next((a for a in assignments if a.is_winner), None)
        if ahorro_unit > 0 and winner_assign and winner_assign.qty > 0:
            savings_total = ahorro_unit * winner_assign.qty
            notes_parts.insert(0, f"Ahorro ${savings_total:,.2f} vs 2° proveedor")

    if remaining > 0:
        notes_parts.append(f"Demanda insatisfecha: {remaining:.0f} uds")

    return AllocationResult(
        product_id=product_id,
        qty_demanded=qty_demanded,
        assignments=assignments,
        notes=" | ".join(notes_parts) if notes_parts else "OK",
    )
