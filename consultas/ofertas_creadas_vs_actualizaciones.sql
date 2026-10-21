SET NOCOUNT ON;

WITH Creadas AS (
    SELECT MONTH(DocDate) AS Mes,
        COUNT(*)       AS Cantidad
    FROM dbo.OQUT
    WHERE CANCELED = 'N'
    AND YEAR(DocDate) = :anio
    GROUP BY MONTH(DocDate)
),
Actualizaciones AS (
    SELECT MONTH(UpdateDate)        AS Mes,
        COUNT(*)                 AS Cantidad,
        COUNT(DISTINCT DocEntry) AS Ofertas
    FROM dbo.ADOC
    WHERE ObjType = '23'
    AND YEAR(UpdateDate) = :anio
    GROUP BY MONTH(UpdateDate)
),
Meses AS (
    SELECT Mes FROM Creadas
    UNION
    SELECT Mes FROM Actualizaciones
)
SELECT m.Mes,
    ISNULL(c.Cantidad, 0) AS Creadas,
    ISNULL(a.Cantidad, 0) AS Actualizaciones,
    ISNULL(a.Ofertas, 0)  AS OfertasActualizadas
FROM Meses m
LEFT JOIN Creadas c         ON c.Mes = m.Mes
LEFT JOIN Actualizaciones a ON a.Mes = m.Mes