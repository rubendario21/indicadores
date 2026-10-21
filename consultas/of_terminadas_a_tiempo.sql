SET NOCOUNT ON;

WITH UltRecibo AS (
    SELECT W.DocEntry      AS OFEntry,
        MAX(T0.DocDate) AS FechaUltRecibo
    FROM dbo.OWOR W
    INNER JOIN dbo.IGN1 T1 ON T1.BaseEntry = W.DocEntry
                        AND T1.BaseType  = 202
                        AND T1.ItemCode  = W.ItemCode   -- solo el producto terminado
    INNER JOIN dbo.OIGN T0 ON T0.DocEntry  = T1.DocEntry
    WHERE T0.CANCELED = 'N'
    GROUP BY W.DocEntry
)
SELECT MONTH(W.CloseDate) AS Mes,
    COUNT(*)           AS [OF cerradas],
    SUM(CASE WHEN R.FechaUltRecibo <= W.DueDate THEN 1 ELSE 0 END) AS [A tiempo],
    AVG(CASE WHEN R.FechaUltRecibo > W.DueDate
                THEN CAST(DATEDIFF(DAY, W.DueDate, R.FechaUltRecibo) AS DECIMAL(10, 2))
        END)           AS [Días de retraso]
FROM dbo.OWOR W
INNER JOIN UltRecibo R ON R.OFEntry = W.DocEntry
WHERE W.Status = 'L'
AND W.Type  <> 'D'
AND YEAR(W.CloseDate) = :anio
GROUP BY MONTH(W.CloseDate)