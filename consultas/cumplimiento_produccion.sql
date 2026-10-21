SET NOCOUNT ON;

SELECT MONTH(W.CloseDate) AS Mes,
    COUNT(*)                                                   AS [OF cerradas],
    SUM(CASE WHEN W.CmpltQty >= W.PlannedQty THEN 1 ELSE 0 END) AS [OF completas],
    SUM(W.PlannedQty)                                          AS [Planificada],
    SUM(W.CmpltQty)                                            AS [Recibida],
    SUM(W.RjctQty)                                             AS [Rechazada]
FROM dbo.OWOR W
WHERE W.Status = 'L'        -- cerradas
  AND W.Type <> 'D'         -- excluye desmontaje
  AND YEAR(W.CloseDate) = :anio
GROUP BY MONTH(W.CloseDate)