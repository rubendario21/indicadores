SET NOCOUNT ON;

WITH Vencidas AS (
    SELECT 
        MONTH(o.DocDate)          AS Mes,
        COUNT(DISTINCT o.DocEntry) AS Cantidad
    FROM dbo.OQUT o
    WHERE YEAR(o.DocDate) = :anio AND o.CANCELED = 'N' and o.DocStatus = 'O' and cast(o.DocDueDate as date) < cast(getdate() as date) 
    GROUP BY MONTH(o.DocDate)
),
Abiertas AS (
    SELECT 
        MONTH(o.DocDate)          AS Mes,
        COUNT(DISTINCT o.DocEntry) AS Cantidad
    FROM dbo.OQUT o
    WHERE YEAR(o.DocDate) = :anio AND o.CANCELED = 'N'
    GROUP BY MONTH(o.DocDate)
)
SELECT 
    o1.Mes,
    o1.Cantidad                                      AS Vencidas,
    ISNULL(o2.Cantidad, 0)                           AS Emitidas
FROM Vencidas o1
LEFT JOIN Abiertas o2 ON o2.Mes = o1.Mes