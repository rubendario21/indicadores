SET NOCOUNT ON;

WITH Lineas AS (
    SELECT W.CloseDate,
		W.Project,
		W.DocEntry,
		L.PlannedQty * o.AvgPrice AS Planificado,
		L.IssuedQty  * o.AvgPrice AS Emitido
    FROM dbo.OWOR W
    INNER JOIN dbo.WOR1 L ON L.DocEntry = W.DocEntry
    INNER JOIN dbo.OITM I ON I.ItemCode = L.ItemCode
    inner join dbo.OITW o on i.ItemCode = o.ItemCode and o.WhsCode = 'Bodega40'
    WHERE W.Status = 'L'                 -- OF cerradas
	AND W.Type  <> 'D'                 -- excluye desmontaje
	AND L.ItemType  = 4                -- solo artículos
	AND L.IssueType = 'M'              -- solo emisión manual
	AND ISNULL(W.Project, '') <> ''    -- solo OF de proyectos
	AND YEAR(W.CloseDate) = :anio
)
SELECT MONTH(CloseDate)                 AS Mes,
	SUM(Planificado)                 AS [Valor planificado],
	SUM(Emitido)                     AS [Valor emitido],
	SUM(ABS(Emitido - Planificado))  AS [Desviación absoluta]
FROM Lineas
GROUP BY MONTH(CloseDate)