SET NOCOUNT ON;

WITH Bodegas AS (
    -- Almacenes principales (NO obra). Los mismos del indicador de devoluciones.
    SELECT WhsCode
    FROM (VALUES ('Bodega40'), ('02')) AS b (WhsCode)
),
Stock AS (
    SELECT W.WhsCode,
        W.ItemCode,
           W.OnHand * CASE WHEN W.AvgPrice > 0 THEN W.AvgPrice ELSE I.AvgPrice END AS Valor
    FROM dbo.OITW W
    INNER JOIN dbo.OITM I ON I.ItemCode = W.ItemCode
    LEFT JOIN Bodegas b   ON b.WhsCode  = W.WhsCode
    WHERE b.WhsCode IS NULL       -- solo almacenes de obra
    AND W.OnHand > 0
),
UltIngreso AS (
    SELECT N.Warehouse, N.ItemCode, MAX(N.DocDate) AS Fecha
    FROM dbo.OINM N
    WHERE N.InQty > 0
    AND EXISTS (SELECT 1 FROM Stock s
                WHERE s.WhsCode = N.Warehouse AND s.ItemCode = N.ItemCode)
    GROUP BY N.Warehouse, N.ItemCode
)
SELECT MONTH(GETDATE()) AS Mes,
    SUM(S.Valor)     AS [Valor en obra],
    SUM(CASE WHEN U.Fecha IS NULL
                OR DATEDIFF(DAY, U.Fecha, GETDATE()) > 30
                THEN S.Valor ELSE 0 END) AS [Más de 30 días]
FROM Stock S
LEFT JOIN UltIngreso U ON U.Warehouse = S.WhsCode
                    AND U.ItemCode  = S.ItemCode