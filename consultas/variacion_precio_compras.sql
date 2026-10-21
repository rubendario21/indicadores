SET NOCOUNT ON;

WITH Lineas AS (
    -- Factura copiada directamente desde la OC
    SELECT f.DocEntry, f.LineNum,
        oc.Price    AS PrecioOC,
        oc.Currency AS MonedaOC,
        oc.DocEntry AS OCEntry
    FROM dbo.PCH1 f
    INNER JOIN dbo.POR1 oc ON oc.DocEntry = f.BaseEntry
                        AND oc.LineNum  = f.BaseLine
    WHERE f.BaseType = 22

    UNION ALL

    -- Factura copiada desde la entrada, que viene de la OC
    SELECT f.DocEntry, f.LineNum,
        oc.Price, oc.Currency, oc.DocEntry
    FROM dbo.PCH1 f
    INNER JOIN dbo.PDN1 e  ON e.DocEntry  = f.BaseEntry
                        AND e.LineNum   = f.BaseLine
    INNER JOIN dbo.POR1 oc ON oc.DocEntry = e.BaseEntry
                        AND oc.LineNum  = e.BaseLine
    WHERE f.BaseType = 20
    AND e.BaseType = 22
),
Detalle AS (
    SELECT h.DocDate,
        f.Quantity,
        l.PrecioOC,
        f.Price AS PrecioFactura,
        CASE WHEN f.Rate = 0 THEN 1 ELSE f.Rate END AS Tasa
    FROM Lineas l
    INNER JOIN dbo.PCH1 f ON f.DocEntry = l.DocEntry
                        AND f.LineNum  = l.LineNum
    INNER JOIN dbo.OPCH h ON h.DocEntry = f.DocEntry
    WHERE h.CANCELED = 'N'
    AND f.Currency = l.MonedaOC
)
SELECT MONTH(DocDate) AS Mes,
    SUM(Quantity * PrecioOC      * Tasa) AS [Valor a precio OC],
    SUM(Quantity * PrecioFactura * Tasa) AS [Valor facturado],
    SUM(CASE WHEN PrecioFactura > PrecioOC
                THEN Quantity * (PrecioFactura - PrecioOC) * Tasa
                ELSE 0 END)                 AS [Sobrecosto]
FROM Detalle
WHERE YEAR(DocDate) = :anio
GROUP BY MONTH(DocDate)