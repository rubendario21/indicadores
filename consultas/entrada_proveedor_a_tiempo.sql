SET NOCOUNT ON;

WITH OrdenCompra AS (
    SELECT 
        MONTH(o.DocDate)          AS Mes,
        COUNT(DISTINCT o.DocEntry) AS Cantidad
    FROM dbo.OPOR o
    inner join dbo.PDN1 d on o.DocEntry = d.BaseEntry
    inner join dbo.OPDN o2 on d.DocEntry = o2.DocEntry and o2.CANCELED = 'N'
    WHERE YEAR(o.DocDate) = :anio AND o.CANCELED = 'N' and cast(o2.DocDate as date) <= cast(o.DocDueDate as date) 
    GROUP BY MONTH(o.DocDate)
),
Entradas AS (
    SELECT 
        MONTH(o.DocDate)          AS Mes,
        COUNT(DISTINCT o.DocEntry) AS Cantidad
    FROM dbo.OPDN o
    WHERE YEAR(o.DocDate) = :anio AND o.CANCELED = 'N'
    GROUP BY MONTH(o.DocDate)
)
SELECT 
    o1.Mes,
    o1.Cantidad                                      AS "ATiempo",
    ISNULL(o2.Cantidad, 0)                           AS Entradas,
    1.0 * ISNULL(o1.Cantidad, 0) / o2.Cantidad       AS PctConversion
FROM OrdenCompra o1
LEFT JOIN Entradas o2 ON o2.Mes = o1.Mes