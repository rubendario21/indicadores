SET NOCOUNT ON;

WITH Convertido AS (
    SELECT 
        MONTH(o.DocDate)          AS Mes,
        sum(o.DocTotal ) AS Cantidad
    FROM dbo.OQUT o
    INNER JOIN dbo.RDR1 r on o.DocEntry = r.BaseEntry 
    WHERE YEAR(o.DocDate) = :anio AND o.CANCELED = 'N'
    GROUP BY MONTH(o.DocDate)
),
Cotizado AS (
    SELECT 
        MONTH(o.DocDate)          AS Mes,
        sum(o.DocTotal) AS Cantidad
    FROM dbo.OQUT o
    WHERE YEAR(o.DocDate) = :anio AND o.CANCELED = 'N'
    GROUP BY MONTH(o.DocDate)
)
SELECT 
    o1.Mes,
    o1.Cantidad                                      AS Convertido,
    ISNULL(o2.Cantidad, 0)                           AS Cotizado
FROM Convertido  o1
LEFT JOIN Cotizado  o2 ON o2.Mes = o1.Mes