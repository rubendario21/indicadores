SET NOCOUNT ON;

WITH Recibido AS (
    SELECT MONTH(T0.DocDate) AS Mes,
           SUM(T1.LineTotal * (1 - ISNULL(T0.DiscPrcnt, 0) / 100.0)) AS Valor
    FROM dbo.OPDN T0
    INNER JOIN dbo.PDN1 T1 ON T1.DocEntry = T0.DocEntry
    WHERE T0.CANCELED = 'N'
    AND YEAR(T0.DocDate) = :anio
    GROUP BY MONTH(T0.DocDate)
),
Devuelto AS (
    SELECT MONTH(T0.DocDate) AS Mes,
           SUM(T1.LineTotal * (1 - ISNULL(T0.DiscPrcnt, 0) / 100.0)) AS Valor
    FROM dbo.ORPD T0
    INNER JOIN dbo.RPD1 T1 ON T1.DocEntry = T0.DocEntry
    WHERE T0.CANCELED = 'N'
    AND YEAR(T0.DocDate) = :anio
    GROUP BY MONTH(T0.DocDate)
),
Meses AS (
    SELECT Mes FROM Recibido
    UNION
    SELECT Mes FROM Devuelto
)
SELECT m.Mes,
    ISNULL(r.Valor, 0) AS [Recibido],
    ISNULL(d.Valor, 0) AS [Devuelto]
FROM Meses m
LEFT JOIN Recibido r ON r.Mes = m.Mes
LEFT JOIN Devuelto d ON d.Mes = m.Mes