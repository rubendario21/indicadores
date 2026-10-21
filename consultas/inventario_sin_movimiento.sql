SET NOCOUNT ON;

WITH Stock AS (
    SELECT W.WhsCode,
        W.ItemCode,
           W.OnHand * CASE WHEN W.AvgPrice > 0 THEN W.AvgPrice ELSE I.AvgPrice END AS Valor
    FROM dbo.OITW W
    INNER JOIN dbo.OITM I ON I.ItemCode = W.ItemCode
    WHERE W.OnHand > 0
),
UltMovimiento AS (
    SELECT N.Warehouse, N.ItemCode, MAX(N.DocDate) AS Fecha
    FROM dbo.OINM N
    WHERE EXISTS (SELECT 1 FROM Stock s
                WHERE s.WhsCode = N.Warehouse AND s.ItemCode = N.ItemCode)
    GROUP BY N.Warehouse, N.ItemCode
)
SELECT SUM(S.Valor) AS [Valor inventario],
    SUM(CASE WHEN U.Fecha IS NULL
                OR DATEDIFF(DAY, U.Fecha, GETDATE()) > 180
                THEN S.Valor ELSE 0 END) AS [Más de 180 días],
    SUM(CASE WHEN U.Fecha IS NULL
                OR DATEDIFF(DAY, U.Fecha, GETDATE()) > 365
                THEN S.Valor ELSE 0 END) AS [Más de 1 año]
FROM Stock S
LEFT JOIN UltMovimiento U ON U.Warehouse = S.WhsCode
                        AND U.ItemCode  = S.ItemCode