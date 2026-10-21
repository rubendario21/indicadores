SET NOCOUNT ON;

WITH PrimeraOrden AS (
    SELECT r.BaseEntry   AS OfertaEntry,
        MIN(o.DocDate) AS FechaOrden
    FROM dbo.RDR1 r
    INNER JOIN dbo.ORDR o ON o.DocEntry = r.DocEntry
    WHERE r.BaseType = 23
    AND o.CANCELED = 'N'
    GROUP BY r.BaseEntry
)
SELECT MONTH(p.FechaOrden) AS Mes,
    ROUND(AVG(CAST(DATEDIFF(DAY, q.DocDate, p.FechaOrden) AS DECIMAL(10, 2))), 0)
                                                    AS [Días promedio],
    MAX(DATEDIFF(DAY, q.DocDate, p.FechaOrden))    AS [Días máximo],
    COUNT(*)                                       AS [Convertidas]
FROM PrimeraOrden p
INNER JOIN dbo.OQUT q ON q.DocEntry = p.OfertaEntry
WHERE q.CANCELED = 'N'
AND YEAR(p.FechaOrden) = :anio
AND p.FechaOrden >= q.DocDate
GROUP BY MONTH(p.FechaOrden)