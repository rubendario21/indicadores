SET NOCOUNT ON;

WITH PrimeraOC AS (
    SELECT l.BaseEntry     AS SolEntry,
        MIN(o.DocDate)  AS FechaOC
    FROM dbo.POR1 l
    INNER JOIN dbo.OPOR o ON o.DocEntry = l.DocEntry
    WHERE l.BaseType = 1470000113      -- copiada desde solicitud de compra
    AND o.CANCELED = 'N'
    GROUP BY l.BaseEntry
)
SELECT MONTH(p.FechaOC) AS Mes,
    ROUND(AVG(CAST(DATEDIFF(DAY, s.DocDate, p.FechaOC) AS DECIMAL(10, 2))), 0)
                                                    AS [Días promedio],
    MAX(DATEDIFF(DAY, s.DocDate, p.FechaOC))     AS [Días máximo],
    COUNT(*)                                     AS [Solicitudes atendidas]
FROM PrimeraOC p
INNER JOIN dbo.OPRQ s ON s.DocEntry = p.SolEntry
WHERE s.CANCELED = 'N'
AND YEAR(p.FechaOC) = :anio
AND p.FechaOC >= s.DocDate
GROUP BY MONTH(p.FechaOC)