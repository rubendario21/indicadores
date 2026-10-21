SET NOCOUNT ON;
DECLARE @Dias INT = 30;   -- límite de días para considerar una OF envejecida

SELECT MONTH(W.StartDate) AS Mes,
       COUNT(*)           AS [OF iniciadas],
       SUM(CASE WHEN W.Status = 'R' THEN 1 ELSE 0 END) AS [Abiertas hoy],
       SUM(CASE WHEN W.Status = 'R'
                 AND DATEDIFF(DAY, W.StartDate, GETDATE()) > @Dias
                THEN 1 ELSE 0 END)                     AS [Envejecidas]
FROM dbo.OWOR W
WHERE W.Status IN ('R', 'L')     -- liberadas o cerradas
  AND W.Type <> 'D'
  AND YEAR(W.StartDate) = :anio
GROUP BY MONTH(W.StartDate)