SET NOCOUNT ON;

WITH Lineas AS (
    SELECT T0.DocDate,
        T0.SlpCode,
           T1.Quantity * T1.PriceBefDi * CASE WHEN T1.Rate = 0 THEN 1 ELSE T1.Rate END
                                                        AS ValorBruto,
           T1.LineTotal * (1 - ISNULL(T0.DiscPrcnt, 0) / 100.0)
                                                        AS ValorNeto
    FROM dbo.ORDR T0
    INNER JOIN dbo.RDR1 T1 ON T1.DocEntry = T0.DocEntry
    WHERE T0.CANCELED = 'N'
    AND YEAR(T0.DocDate) = :anio
)
SELECT MONTH(DocDate)                  AS Mes,
    SUM(ValorBruto)                 AS [Antes de descuento],
    SUM(ValorBruto - ValorNeto)     AS [Descuento]
FROM Lineas
GROUP BY MONTH(DocDate)