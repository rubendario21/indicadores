SET NOCOUNT ON;

WITH Metas AS (
    -- Meta de pedidos por mes, en pesos (antes de IVA). Ajustar con gerencia.
    SELECT Mes, Meta
    FROM (VALUES
        (1,  1200000000), (2,  1200000000), (3,  1200000000),
        (4,  1200000000), (5,  1200000000), (6,  1200000000),
        (7,  1200000000), (8,  1200000000), (9,  1200000000),
        (10, 1200000000), (11, 1200000000), (12, 1200000000)
    ) AS m (Mes, Meta)
),
Pedidos AS (
    SELECT MONTH(T0.DocDate) AS Mes,
           SUM(T1.LineTotal * (1 - ISNULL(T0.DiscPrcnt, 0) / 100.0)) AS Valor
    FROM dbo.ORDR T0
    INNER JOIN dbo.RDR1 T1 ON T1.DocEntry = T0.DocEntry
    WHERE T0.CANCELED = 'N'
    AND YEAR(T0.DocDate) = :anio
    GROUP BY MONTH(T0.DocDate)
)
SELECT m.Mes,
    ISNULL(p.Valor, 0) AS [Pedidos],
    m.Meta             AS [Meta]
FROM Metas m
LEFT JOIN Pedidos p ON p.Mes = m.Mes
WHERE m.Mes <= CASE WHEN :anio = YEAR(GETDATE()) THEN MONTH(GETDATE()) ELSE 12 END