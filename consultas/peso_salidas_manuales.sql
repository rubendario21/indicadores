SET NOCOUNT ON;

SELECT 
    MONTH(T0.DocDate) AS Mes,
    SUM(CASE WHEN T1.BaseType <> 202 THEN T1.Quantity * T1.StockPrice ELSE 0 END) AS SalidasManuales,
    SUM(CASE WHEN T1.BaseType = 202 THEN T1.Quantity * T1.StockPrice ELSE 0 END) AS EmisionesProduccion,
    SUM(T1.Quantity * T1.StockPrice) AS TotalSalidas
FROM dbo.OIGE T0
INNER JOIN dbo.IGE1 T1 ON T1.DocEntry = T0.DocEntry
WHERE T0.CANCELED = 'N' AND YEAR(T0.DocDate) = :anio
GROUP BY MONTH(T0.DocDate)