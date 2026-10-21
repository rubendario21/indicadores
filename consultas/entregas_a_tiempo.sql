SET NOCOUNT ON;

WITH EntregasOV AS (
    -- Entregas copiadas directamente de la orden de venta
    SELECT 
        d.BaseEntry AS OVEntry,
        e.DocDate   AS FechaEntrega
    FROM dbo.DLN1 d
    INNER JOIN dbo.ODLN e ON e.DocEntry = d.DocEntry
    WHERE d.BaseType = 17
    AND e.CANCELED = 'N'

    UNION ALL

    -- Entregas copiadas de una factura de reserva que viene de la orden de venta
    SELECT 
        f.BaseEntry AS OVEntry,
        e.DocDate   AS FechaEntrega
    FROM dbo.DLN1 d
    INNER JOIN dbo.ODLN e  ON e.DocEntry  = d.DocEntry
    INNER JOIN dbo.INV1 f  ON f.DocEntry  = d.BaseEntry AND f.LineNum   = d.BaseLine
    INNER JOIN dbo.OINV fr ON fr.DocEntry = f.DocEntry
    WHERE d.BaseType  = 13
    AND f.BaseType  = 17
    AND fr.isIns    = 'Y'
    AND fr.CANCELED = 'N'
    AND e.CANCELED  = 'N'
),
UltimaEntrega AS (
    SELECT OVEntry, MAX(FechaEntrega) AS FechaUltEntrega
    FROM EntregasOV
    GROUP BY OVEntry
)
SELECT 
    MONTH(o.DocDate) AS Mes,
    COUNT(*)         AS Entregadas,
    SUM(CASE WHEN CAST(u.FechaUltEntrega AS DATE) <= CAST(o.DocDueDate AS DATE)
                THEN 1 ELSE 0 END) AS ATiempo
FROM dbo.ORDR o
INNER JOIN UltimaEntrega u ON u.OVEntry = o.DocEntry
WHERE YEAR(o.DocDate) = :anio AND o.CANCELED = 'N'
GROUP BY MONTH(o.DocDate)