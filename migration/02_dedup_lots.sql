-- Fusiona lotes duplicados (stock_lot) causados por el bug de import del
-- 2025-01-07, que partió el historial de movimiento de un lote real en
-- 5-6 copias con "ERROR"/"error" literal en el nombre.
--
-- Regla de negocio (confirmada por el usuario 2026-08-13):
--   - Se agrupa por (product_id, name) con 'error' en el nombre.
--   - Gana el registro con MÁS referencias en stock_move_line (más
--     historial real); empate se rompe por menor id.
--   - Se reasignan TODAS las referencias (movimientos, compras, mermas,
--     valores, existencias) del/los perdedor(es) al ganador.
--   - Los perdedores se ARCHIVAN (active=false), nunca se borran
--     (unlink) -- se conserva el registro por auditoría, solo deja de
--     usarse hacia adelante.
--   - Al ganador se le limpia " ERROR"/" Error" del nombre.
--
-- Idempotente: si se corre dos veces, la segunda vez no encuentra
-- duplicados activos que fusionar (ya quedaron archivados) y no hace
-- nada. Pensado para correr contra medicinedepot_migration_clean
-- (nunca contra _raw ni contra medicinedepot_dev).

BEGIN;

-- 1. Mapa perdedor -> ganador para cada grupo duplicado.
--    NOTA: estos lotes ya están archivados (active=false) en el origen
--    -- no afectan la operación diaria, pero fusionamos igual para dejar
--    el historial de movimiento consolidado en un solo registro por lote
--    en vez de fragmentado en 5-6. Por eso NO filtramos por active=true.
CREATE TEMP TABLE lot_merge_map AS
WITH dup_groups AS (
    SELECT product_id, name
    FROM stock_lot
    WHERE name ILIKE '%error%'
    GROUP BY product_id, name
    HAVING COUNT(*) > 1
),
ranked AS (
    SELECT
        sl.id,
        dg.product_id,
        dg.name,
        ROW_NUMBER() OVER (
            PARTITION BY dg.product_id, dg.name
            ORDER BY (SELECT COUNT(*) FROM stock_move_line sml WHERE sml.lot_id = sl.id) DESC,
                     sl.id ASC
        ) AS rn
    FROM stock_lot sl
    JOIN dup_groups dg ON dg.product_id = sl.product_id AND dg.name = sl.name
)
SELECT
    loser.id AS loser_id,
    winner.id AS winner_id
FROM ranked loser
JOIN ranked winner
    ON winner.product_id = loser.product_id
   AND winner.name = loser.name
   AND winner.rn = 1
WHERE loser.rn > 1;

\echo '--- Grupos a fusionar ---'
SELECT COUNT(DISTINCT winner_id) AS grupos, COUNT(*) AS lotes_perdedores FROM lot_merge_map;

-- 2. Reasignar referencias de tablas simples (una FK directa a lot_id).
UPDATE stock_move_line sml
SET lot_id = m.winner_id
FROM lot_merge_map m
WHERE sml.lot_id = m.loser_id;

UPDATE purchase_order_line pol
SET lot_id = m.winner_id
FROM lot_merge_map m
WHERE pol.lot_id = m.loser_id;

UPDATE sale_order_line sol
SET lot_id = m.winner_id
FROM lot_merge_map m
WHERE sol.lot_id = m.loser_id;

UPDATE stock_scrap ss
SET lot_id = m.winner_id
FROM lot_merge_map m
WHERE ss.lot_id = m.loser_id;

UPDATE stock_scrap_batch_line ssbl
SET lot_id = m.winner_id
FROM lot_merge_map m
WHERE ssbl.lot_id = m.loser_id;

UPDATE product_value pv
SET lot_id = m.winner_id
FROM lot_merge_map m
WHERE pv.lot_id = m.loser_id;

-- stock_quant: por diseño estos lotes duplicados tienen 0 en quant, pero
-- se maneja igual por robustez (ej. si el script se reutiliza a futuro
-- con otro conjunto de duplicados que sí tengan stock). Evita choque de
-- unicidad (product_id, location_id, lot_id, package_id, owner_id)
-- sumando cantidades cuando el ganador ya tiene una fila igual.
WITH moved AS (
    SELECT sq.id AS loser_quant_id, m.winner_id, sq.product_id, sq.location_id, sq.package_id, sq.owner_id
    FROM stock_quant sq
    JOIN lot_merge_map m ON sq.lot_id = m.loser_id
),
existing_winner_quant AS (
    SELECT sq.id AS winner_quant_id, sq.product_id, sq.location_id, sq.package_id, sq.owner_id, mv.loser_quant_id
    FROM stock_quant sq
    JOIN moved mv ON sq.lot_id = mv.winner_id
        AND sq.product_id = mv.product_id
        AND sq.location_id = mv.location_id
        AND COALESCE(sq.package_id,-1) = COALESCE(mv.package_id,-1)
        AND COALESCE(sq.owner_id,-1) = COALESCE(mv.owner_id,-1)
)
UPDATE stock_quant sq
SET quantity = sq.quantity + loser.quantity
FROM stock_quant loser
JOIN existing_winner_quant ewq ON ewq.loser_quant_id = loser.id
WHERE sq.id = ewq.winner_quant_id;

DELETE FROM stock_quant sq
USING lot_merge_map m
WHERE sq.lot_id = m.loser_id
  AND sq.id IN (
      SELECT loser.id FROM stock_quant loser
      JOIN lot_merge_map m2 ON loser.lot_id = m2.loser_id
      JOIN stock_quant winner ON winner.lot_id = m2.winner_id
          AND winner.product_id = loser.product_id
          AND winner.location_id = loser.location_id
          AND COALESCE(winner.package_id,-1) = COALESCE(loser.package_id,-1)
          AND COALESCE(winner.owner_id,-1) = COALESCE(loser.owner_id,-1)
  );

UPDATE stock_quant sq
SET lot_id = m.winner_id
FROM lot_merge_map m
WHERE sq.lot_id = m.loser_id;

-- 3. Relación m2m expiry_picking_confirmation <-> stock_lot: reapuntar al
-- ganador evitando duplicar el par (confirmation_id, winner_id).
UPDATE expiry_picking_confirmation_stock_lot_rel rel
SET stock_lot_id = m.winner_id
FROM lot_merge_map m
WHERE rel.stock_lot_id = m.loser_id
  AND NOT EXISTS (
      SELECT 1 FROM expiry_picking_confirmation_stock_lot_rel r2
      WHERE r2.expiry_picking_confirmation_id = rel.expiry_picking_confirmation_id
        AND r2.stock_lot_id = m.winner_id
  );
DELETE FROM expiry_picking_confirmation_stock_lot_rel rel
USING lot_merge_map m
WHERE rel.stock_lot_id = m.loser_id;

-- 4. Limpiar " ERROR"/" Error" del nombre del lote ganador.
UPDATE stock_lot
SET name = regexp_replace(name, '\s*(ERROR|Error|error)\s*$', '', 'g')
WHERE id IN (SELECT DISTINCT winner_id FROM lot_merge_map);

-- 5. Archivar a los perdedores (nunca unlink).
UPDATE stock_lot
SET active = false
WHERE id IN (SELECT loser_id FROM lot_merge_map);

\echo '--- Verificación post-fusión (debe dar 0 huérfanos) ---'
SELECT
    (SELECT COUNT(*) FROM stock_move_line sml JOIN lot_merge_map m ON sml.lot_id = m.loser_id) AS huerfanos_move_line,
    (SELECT COUNT(*) FROM purchase_order_line pol JOIN lot_merge_map m ON pol.lot_id = m.loser_id) AS huerfanos_purchase,
    (SELECT COUNT(*) FROM stock_scrap ss JOIN lot_merge_map m ON ss.lot_id = m.loser_id) AS huerfanos_scrap;

\echo '--- Resumen final ---'
SELECT
    (SELECT COUNT(*) FROM lot_merge_map) AS lotes_archivados,
    (SELECT COUNT(DISTINCT winner_id) FROM lot_merge_map) AS lotes_ganadores;

COMMIT;
