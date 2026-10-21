select 
	month(o.DocDate) Mes,
	sum(r.LineTotal) Venta,
	sum(r.GrssProfit) Utilidad  
from dbo.ORDR o 
inner join dbo.RDR1 r on o.DocEntry = r.DocEntry 
where year(o.DocDate) = :anio and o.CANCELED = 'N'
group by month(o.DocDate)