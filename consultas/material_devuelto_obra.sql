SET NOCOUNT ON;

WITH Bodegas AS (
    -- Almacenes principales (NO obra). Ajustar con los códigos reales.
    SELECT WhsCode
    FROM (VALUES ('Bodega40')) AS b (WhsCode)
),
Movimientos AS (
    SELECT MONTH(T0.DocDate) AS Mes,
        CASE
            WHEN bo.WhsCode IS NOT NULL AND bd.WhsCode IS NULL THEN 'Envio'
            WHEN bo.WhsCode IS NULL AND bd.WhsCode IS NOT NULL THEN 'Devolucion'
        END AS Tipo,
           T1.InvQty * T1.StockPrice AS Valor
    FROM dbo.OWTR T0
    INNER JOIN dbo.WTR1 T1 ON T1.DocEntry = T0.DocEntry
    LEFT JOIN Bodegas bo ON bo.WhsCode = T1.FromWhsCod   -- origen es bodega
    LEFT JOIN Bodegas bd ON bd.WhsCode = T1.WhsCode      -- destino es bodega
    WHERE T0.CANCELED = 'N'
    AND YEAR(T0.DocDate) = :anio
)
SELECT Mes,
    SUM(CASE WHEN Tipo = 'Envio'      THEN Valor ELSE 0 END) AS [Enviado a obra],
    SUM(CASE WHEN Tipo = 'Devolucion' THEN Valor ELSE 0 END) AS [Devuelto de obra]
FROM Movimientos
WHERE Tipo IS NOT NULL
GROUP BY Mes