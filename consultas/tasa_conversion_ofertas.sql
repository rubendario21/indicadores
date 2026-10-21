SET NOCOUNT ON;

WITH Ofertas AS (
    SELECT 
        MONTH(o.DocDate)          AS Mes,
        COUNT(DISTINCT o.DocEntry) AS Cantidad
    FROM dbo.OQUT o
    WHERE YEAR(o.DocDate) = :anio
    AND o.CANCELED = 'N'
    GROUP BY MONTH(o.DocDate)
),
OfertasOrdenes AS (
    SELECT 
        MONTH(o.DocDate)          AS Mes,
        COUNT(DISTINCT o.DocEntry) AS Cantidad
    FROM dbo.OQUT o
    INNER JOIN dbo.RDR1 r ON r.BaseEntry = o.DocEntry AND r.BaseType  = 23
    INNER JOIN dbo.ORDR od ON od.DocEntry = r.DocEntry AND od.CANCELED = 'N'
    WHERE YEAR(o.DocDate) = :anio AND o.CANCELED = 'N'
    GROUP BY MONTH(o.DocDate)
)
SELECT 
    o1.Mes,
    o1.Cantidad                                      AS "Creadas",
    ISNULL(o2.Cantidad, 0)                           AS "Convertidas",
    1.0 * ISNULL(o2.Cantidad, 0) / o1.Cantidad       AS PctConversion
FROM Ofertas o1
LEFT JOIN OfertasOrdenes o2 ON o2.Mes = o1.Mes