SET NOCOUNT ON;

WITH Lineas AS (
    SELECT W.CloseDate,
        L.PlannedQty,
        L.IssuedQty,
        I.AvgPrice
    FROM dbo.OWOR W
    INNER JOIN dbo.WOR1 L ON L.DocEntry = W.DocEntry
    INNER JOIN dbo.OITM I ON I.ItemCode = L.ItemCode
WHERE W.Status = 'L'          -- OF cerradas
    AND W.Type  <> 'D'          -- excluye desmontaje
    AND L.ItemType = 4          -- solo artículos
    AND L.IssueType = 'M'       -- solo emisión manual
    AND YEAR(W.CloseDate) = :anio
)
SELECT MONTH(CloseDate) AS Mes,
    COUNT(*)         AS [Componentes],
    SUM(CASE
            WHEN PlannedQty > 0
            AND IssuedQty BETWEEN PlannedQty * 0.98 AND PlannedQty * 1.02 THEN 1
            WHEN PlannedQty = 0 AND IssuedQty = 0 THEN 1
            ELSE 0
        END)                        AS [Dentro de tolerancia],
       SUM(PlannedQty * AvgPrice)      AS [Valor planificado],
       SUM(IssuedQty  * AvgPrice)      AS [Valor emitido]
FROM Lineas
GROUP BY MONTH(CloseDate)