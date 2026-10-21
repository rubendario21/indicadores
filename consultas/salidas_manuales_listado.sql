SET NOCOUNT ON;

SELECT ISNULL(U.U_NAME, '(Sin usuario)') AS [Responsable],
    cn.Name                        AS [Concepto],
       SUM(CASE WHEN MONTH(T0.DocDate) = 1  THEN T1.InvQty * T1.StockPrice ELSE 0 END) AS [Ene],
       SUM(CASE WHEN MONTH(T0.DocDate) = 2  THEN T1.InvQty * T1.StockPrice ELSE 0 END) AS [Feb],
       SUM(CASE WHEN MONTH(T0.DocDate) = 3  THEN T1.InvQty * T1.StockPrice ELSE 0 END) AS [Mar],
       SUM(CASE WHEN MONTH(T0.DocDate) = 4  THEN T1.InvQty * T1.StockPrice ELSE 0 END) AS [Abr],
       SUM(CASE WHEN MONTH(T0.DocDate) = 5  THEN T1.InvQty * T1.StockPrice ELSE 0 END) AS [May],
       SUM(CASE WHEN MONTH(T0.DocDate) = 6  THEN T1.InvQty * T1.StockPrice ELSE 0 END) AS [Jun],
       SUM(CASE WHEN MONTH(T0.DocDate) = 7  THEN T1.InvQty * T1.StockPrice ELSE 0 END) AS [Jul],
       SUM(CASE WHEN MONTH(T0.DocDate) = 8  THEN T1.InvQty * T1.StockPrice ELSE 0 END) AS [Ago],
       SUM(CASE WHEN MONTH(T0.DocDate) = 9  THEN T1.InvQty * T1.StockPrice ELSE 0 END) AS [Sep],
       SUM(CASE WHEN MONTH(T0.DocDate) = 10 THEN T1.InvQty * T1.StockPrice ELSE 0 END) AS [Oct],
       SUM(CASE WHEN MONTH(T0.DocDate) = 11 THEN T1.InvQty * T1.StockPrice ELSE 0 END) AS [Nov],
       SUM(CASE WHEN MONTH(T0.DocDate) = 12 THEN T1.InvQty * T1.StockPrice ELSE 0 END) AS [Dic],
       SUM(T1.InvQty * T1.StockPrice)    AS [Total año],
    COUNT(DISTINCT T0.DocEntry)       AS [Documentos]
FROM dbo.OIGE T0
INNER JOIN dbo.IGE1 T1 ON T1.DocEntry = T0.DocEntry
LEFT JOIN dbo.OUSR U   ON U.USERID    = T0.UserSign
inner join [@EST_CONC_SALINV] cn on t1.U_EST_CONC_SALINV = cn.Code
WHERE T0.CANCELED = 'N' AND T1.BaseType <> 202          -- solo salidas manuales
AND YEAR(T0.DocDate) = :anio
GROUP BY U.U_NAME,cn.Name
ORDER BY [Total año] DESC