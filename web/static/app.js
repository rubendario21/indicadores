"use strict";

const estado = { datos: null, anio: new Date().getFullYear(), graficos: [], cargando: false };
const $ = (sel) => document.querySelector(sel);
const CARGANDO = '<div class="cargando"><div class="spinner"></div><p>Consultando SAP y Zoho…</p></div>';

// ---------------------------------------------------------------- formato (igual que graficos.formatear)

function co(n, decimales = 0) {
  const [ent, dec] = Math.abs(n).toFixed(decimales).split(".");
  const miles = ent.replace(/\B(?=(\d{3})+(?!\d))/g, ".");
  return (n < 0 ? "-" : "") + miles + (dec ? "," + dec : "");
}

function compacto(v) {
  const a = Math.abs(v);
  if (a >= 1e12) return co(v / 1e12, 1) + " B";
  if (a >= 1e9) return co(v / 1e9, 1) + " MM";
  if (a >= 1e6) return co(Math.round(v / 1e6)) + " M";
  if (a >= 1e3) return co(Math.round(v / 1e3)) + " mil";
  return co(Math.round(v));
}

function fmt(v, formato) {
  if (v === null || v === undefined || Number.isNaN(v)) return "–";
  if (formato === "millones") return "$ " + compacto(v);
  if (formato === "moneda") return "$ " + co(Math.round(v));
  if (formato === "porcentaje") return (v !== 0 && Math.abs(v) < 0.01 ? co(v * 100, 1) : co(Math.round(v * 100))) + "%";
  return co(Math.round(v));
}

function fmtEje(v, formato) {
  if (formato === "porcentaje") return co(Math.round(v * 100)) + "%";
  if (formato === "millones" || formato === "moneda") return "$ " + compacto(v);
  return co(v);
}

const cumple = (v, meta, sentido) => (sentido === "<=" ? v <= meta : v >= meta);
const metaTexto = (m) => (m ? `${m.sentido === "<=" ? "Máximo" : "Mínimo"} ${fmt(m.valor, m.formato)}` : "Sin meta");
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const color = (nombre) => getComputedStyle(document.documentElement).getPropertyValue(nombre).trim();
const SERIES = ["--serie-1", "--serie-2", "--serie-3", "--serie-4", "--serie-5"];

// ---------------------------------------------------------------- datos

async function cargar(forzar = false, silencioso = false) {
  if (estado.cargando) return;
  estado.cargando = true;
  const boton = $("#refrescar");
  boton.disabled = true;
  boton.classList.add("girando");
  if (!estado.datos && !silencioso) $("#contenido").innerHTML = CARGANDO;
  try {
    const r = await fetch(`/api/indicadores?anio=${estado.anio}${forzar ? "&forzar=true" : ""}`);
    if (r.status === 401) { location.href = "/login"; return; }
    if (!r.ok) throw new Error(`El servidor respondió ${r.status}`);
    const nuevos = await r.json();
    const cambio = nuevos.actualizado !== estado.datos?.actualizado || nuevos.anio !== estado.datos?.anio;
    estado.datos = nuevos;
    if (cambio) {
      const y = window.scrollY;
      render();
      if (silencioso) window.scrollTo(0, y);
    } else {
      pintarActualizado();
    }
  } catch (e) {
    console.error(e);
    if (!estado.datos) $("#contenido").innerHTML = `<div class="aviso aviso-error">No se pudieron cargar los indicadores: ${esc(e.message)}</div>`;
  } finally {
    estado.cargando = false;
    boton.disabled = false;
    boton.classList.remove("girando");
  }
}

function pintarActualizado() {
  const d = estado.datos;
  if (!d) return;
  const fecha = new Date(d.actualizado);
  const min = Math.max(0, Math.round((Date.now() - fecha) / 60000));
  const hora = fecha.toLocaleTimeString("es-CO", { hour: "2-digit", minute: "2-digit" });
  $("#actualizado").textContent = `Actualizado ${hora} · ${min === 0 ? "ahora" : `hace ${min} min`}`;
  $("#actualizado").title = `Consulta en vivo a SAP y Zoho (${d.segundos} s). Se renueva cada ${d.cache_min} min.`;
}

// ---------------------------------------------------------------- navegación

function ruta() {
  const p = new URLSearchParams(location.hash.slice(1));
  return { proceso: p.get("p"), indicador: p.get("i") };
}

function irA(proceso, indicador) {
  const p = new URLSearchParams();
  if (proceso) p.set("p", proceso);
  if (indicador) p.set("i", indicador);
  location.hash = p.toString() || "resumen";
}

function render() {
  const d = estado.datos;
  if (!d) return;
  $("#empresa").textContent = `${d.empresa} · ${d.anio}`;
  $("#usuario").textContent = d.usuario || "";
  pintarActualizado();
  estado.graficos.forEach((g) => g.dispose());
  estado.graficos = [];

  const { proceso, indicador } = ruta();
  const actual = d.procesos.find((p) => p.nombre === proceso);
  renderMenu(actual?.nombre);
  if (actual) renderProceso(actual, indicador);
  else renderResumen();
}

function renderMenu(activo) {
  const enlace = (p) => {
    const puntos = p.indicadores.filter((i) => i.estado !== "neutro")
      .map((i) => `<span class="punto ${i.estado}" title="${esc(i.nombre)}: ${esc(i.estado_texto)}"></span>`).join("");
    const href = "#" + new URLSearchParams({ p: p.nombre }).toString();
    return `<a href="${href}" class="${p.nombre === activo ? "activo" : ""}">${esc(p.nombre)}<span class="puntos">${puntos}</span></a>`;
  };
  $("#menu").innerHTML = `<a href="#resumen" class="${activo ? "" : "activo"}">Resumen general</a>
    <div class="separador">Procesos</div>${estado.datos.procesos.map(enlace).join("")}`;
}

// ---------------------------------------------------------------- resumen

function renderResumen() {
  const todos = estado.datos.procesos.flatMap((p) => p.indicadores);
  const n = (e) => todos.filter((i) => i.estado === e).length;
  const medidos = n("cumple") + n("nocumple");
  const global = medidos ? n("cumple") / medidos : null;

  let html = `<div class="encabezado"><div><h1>Resumen general</h1>
    <p>Resultado acumulado de ${estado.datos.anio} frente a la meta de cada indicador</p></div></div>
    <div class="kpis">
      ${kpi("Cumplimiento global", fmt(global, "porcentaje"), `${n("cumple")} de ${medidos} indicadores con meta`)}
      ${kpi('<span class="estado cumple">Cumplen</span>', n("cumple"), "en o mejor que la meta")}
      ${kpi('<span class="estado nocumple">No cumplen</span>', n("nocumple"), "por debajo de la meta")}
      ${kpi('<span class="estado">Sin meta</span>', n("neutro"), "en línea base o solo seguimiento")}
      ${n("error") ? kpi('<span class="estado error">Con error</span>', n("error"), "no se pudieron calcular") : ""}
    </div>`;

  for (const p of estado.datos.procesos) {
    const href = "#" + new URLSearchParams({ p: p.nombre }).toString();
    html += `<section class="seccion"><div class="seccion-titulo"><h2>${esc(p.nombre)}</h2>
      <a href="${href}">Ver detalle →</a></div><div class="mosaico">
      ${p.indicadores.map((i) => ficha(p, i)).join("")}</div></section>`;
  }
  $("#contenido").innerHTML = html;

  document.querySelectorAll(".ficha").forEach((el) => {
    el.addEventListener("click", () => irA(el.dataset.proceso, el.dataset.id));
    const ind = todos.find((i) => i.id === el.dataset.id);
    const caja = el.querySelector(".chispa");
    if (caja) chispa(caja, ind);
  });
}

function kpi(etiqueta, valor, nota) {
  return `<div class="kpi"><div class="kpi-etiqueta">${etiqueta}</div>
    <div class="kpi-valor">${valor}</div><div class="kpi-nota">${esc(nota)}</div></div>`;
}

function ficha(p, i) {
  const tieneSerie = i.tipo === "mensual" && (i.porcentaje?.valores || i.series?.length);
  return `<button class="ficha" data-proceso="${esc(p.nombre)}" data-id="${esc(i.id)}">
    <div class="ficha-pie"><span class="ficha-nombre">${esc(i.nombre)}</span><span class="chip">${esc(i.sistema)}</span></div>
    <div class="ficha-valor">${i.estado === "error" ? "–" : fmt(i.resultado.valor, i.resultado.formato)}</div>
    <div class="ficha-pie"><span>Meta: ${metaTexto(i.meta)}</span><span class="estado ${i.estado}">${esc(i.estado_texto)}</span></div>
    ${tieneSerie ? '<div class="chispa"></div>' : ""}
  </button>`;
}

// ---------------------------------------------------------------- proceso

function renderProceso(p, enfocar) {
  const conExcel = p.indicadores.some((i) => i.tipo === "mensual" || i.tipo === "detalle");
  const excel = `/api/excel?${new URLSearchParams({ proceso: p.nombre, anio: estado.anio })}`;
  const n = (e) => p.indicadores.filter((i) => i.estado === e).length;

  $("#contenido").innerHTML = `<div class="encabezado"><div><h1>${esc(p.nombre)}</h1>
      <p>${p.indicadores.length} indicadores · ${n("cumple")} cumplen · ${n("nocumple")} no cumplen</p></div>
      ${conExcel ? `<a class="boton boton-borde" href="${excel}">⤓ Descargar Excel</a>` : ""}</div>
    <div class="rejilla">${p.indicadores.map(tarjeta).join("")}</div>`;

  for (const i of p.indicadores) {
    const el = document.getElementById("ind-" + i.id);
    if (i.tipo === "mensual" && !i.error) prepararPestanas(el, i);
  }
  if (enfocar) {
    const el = document.getElementById("ind-" + enfocar);
    if (el) { el.scrollIntoView({ behavior: "smooth", block: "start" }); el.classList.add("resaltada"); }
  } else {
    window.scrollTo(0, 0);
  }
}

function tarjeta(i) {
  let cuerpo = "";
  if (i.error) {
    cuerpo = `<div class="aviso aviso-error">No se pudo calcular: ${esc(i.error)}</div>`;
  } else if (i.tipo === "mensual") {
    const pestanas = i.porcentaje
      ? [["pct", i.porcentaje.etiqueta === "%" ? "% mensual" : i.porcentaje.etiqueta], ["vol", "Volumen"], ["tabla", "Tabla"]]
      : [["vol", "Gráfico"], ["tabla", "Tabla"]];
    cuerpo = `${cifras(i)}<div class="pestanas" role="tablist">${pestanas.map(([k, t], n) =>
      `<button data-vista="${k}" class="${n === 0 ? "activa" : ""}">${esc(t)}</button>`).join("")}</div>
      <div class="vista"></div>
      ${i.formato === "millones" ? '<div class="nota">Cifras en pesos: M = millones · MM = miles de millones</div>' : ""}`;
  } else if (i.tipo === "foto") {
    cuerpo = cifras(i) + `<div class="foto">${i.valores.map((v) =>
      `<div><div class="cifra-etiqueta">${esc(v.nombre)}</div><div class="cifra-valor pequena">${fmt(v.valor, i.formato)}</div></div>`).join("")}</div>
      <div class="nota">Valores al ${new Date().toLocaleDateString("es-CO")}</div>`;
  } else {
    cuerpo = tablaLibre(i);
  }
  return `<article class="tarjeta" id="ind-${esc(i.id)}">
    <div class="tarjeta-cabeza"><div><h3>${esc(i.nombre)} <span class="chip">${esc(i.sistema)}</span></h3>
      <p class="tarjeta-desc">${esc(i.descripcion)}</p></div>
      <span class="estado ${i.estado}">${esc(i.estado_texto)}</span></div>
    ${cuerpo}</article>`;
}

function cifras(i) {
  const etiqueta = i.tipo === "foto" ? "Al día de hoy"
    : i.porcentaje ? `Acumulado ${estado.anio}` : `Promedio mensual ${estado.anio}`;
  return `<div class="cifras">
    <div><div class="cifra-etiqueta">${etiqueta}</div><div class="cifra-valor">${fmt(i.resultado.valor, i.resultado.formato)}</div></div>
    <div><div class="cifra-etiqueta">Meta</div><div class="cifra-valor pequena">${metaTexto(i.meta)}</div></div>
  </div>`;
}

function prepararPestanas(el, i) {
  const vista = el.querySelector(".vista");
  const mostrar = (k) => {
    el.querySelectorAll(".pestanas button").forEach((b) => b.classList.toggle("activa", b.dataset.vista === k));
    const previo = estado.graficos.find((g) => g.getDom().parentElement === vista);
    if (previo) { previo.dispose(); estado.graficos.splice(estado.graficos.indexOf(previo), 1); }
    if (k === "tabla") { vista.innerHTML = tablaMensual(i); return; }
    vista.innerHTML = '<div class="grafico"></div>';
    const caja = vista.firstElementChild;
    if (k === "pct") graficoPct(caja, i); else graficoSeries(caja, i);
  };
  el.querySelectorAll(".pestanas button").forEach((b) => b.addEventListener("click", () => mostrar(b.dataset.vista)));
  mostrar(i.porcentaje ? "pct" : "vol");
}

// ---------------------------------------------------------------- tablas

function claseMeta(v, meta, sentido) {
  if (v === null || meta === null || meta === undefined) return "";
  return cumple(v, meta, sentido) ? "ok" : "mal";
}

function totalSerie(valores, acumulado) {
  const v = valores.filter((x) => x !== null);
  if (!v.length) return null;
  const suma = v.reduce((a, b) => a + b, 0);
  return acumulado === "suma" ? suma : suma / v.length;
}

function tablaMensual(i) {
  const titulo = { suma: "Total", promedio: "Prom." }[i.acumulado];
  let html = `<div class="tabla-envoltura"><table class="datos"><thead><tr><th class="txt">Serie</th>
    ${i.meses.map((m) => `<th>${m}</th>`).join("")}${titulo ? `<th class="tot">${titulo}</th>` : ""}</tr></thead><tbody>`;
  i.series.forEach((s, n) => {
    html += `<tr><td class="serie">${esc(s.nombre)}</td>${s.valores.map((v) =>
      `<td class="${n === 0 ? claseMeta(v, i.meta_serie, i.meta_sentido) : ""}">${fmt(v, i.formato)}</td>`).join("")}
      ${titulo ? `<td class="tot">${fmt(totalSerie(s.valores, i.acumulado), i.formato)}</td>` : ""}</tr>`;
  });
  if (i.porcentaje) {
    const pct = i.porcentaje;
    const tot = i.resultado.valor;
    html += `<tr class="pct"><td class="serie">${esc(pct.etiqueta)}</td>${pct.valores.map((v) =>
      `<td class="${claseMeta(v, pct.meta, i.meta_sentido)}">${fmt(v, "porcentaje")}</td>`).join("")}
      ${titulo ? `<td class="tot ${claseMeta(tot, pct.meta, i.meta_sentido)}">${fmt(tot, "porcentaje")}</td>` : ""}</tr>`;
  }
  html += "</tbody></table></div>";
  if (i.meta) html += '<div class="nota">Verde: cumple la meta · Rojo: no la cumple</div>';
  return html;
}

function tablaLibre(i) {
  const cols = i.columnas || [];
  const filas = i.filas || [];
  if (!filas.length) return '<div class="vacio">Sin registros</div>';
  let html = `<div class="tabla-envoltura"><table class="datos"><thead><tr>${cols.map((c) =>
    `<th class="${c.numerica ? "" : "txt"}">${esc(c.nombre)}</th>`).join("")}</tr></thead><tbody>`;
  for (const f of filas) {
    html += `<tr>${f.map((v, n) => cols[n].numerica
      ? `<td>${fmt(v, i.formato)}</td>` : `<td class="txt">${esc(v ?? "")}</td>`).join("")}</tr>`;
  }
  if (i.acumulado === "suma") {
    html += `<tr class="total">${cols.map((c, n) => {
      if (!c.numerica) return `<td class="txt">${n === 0 ? "TOTAL" : ""}</td>`;
      return `<td>${fmt(filas.reduce((a, f) => a + (f[n] || 0), 0), i.formato)}</td>`;
    }).join("")}</tr>`;
  }
  html += "</tbody></table></div>";
  if (i.total_filas > filas.length) html += `<div class="nota">Mostrando ${filas.length} de ${i.total_filas} filas; el detalle completo está en el Excel.</div>`;
  return html;
}

// ---------------------------------------------------------------- gráficos

function base() {
  return {
    animationDuration: 400,
    textStyle: { fontFamily: "system-ui, -apple-system, Segoe UI, sans-serif", color: color("--tinta-2") },
    grid: { left: 8, right: 16, top: 34, bottom: 4, containLabel: true },
    tooltip: {
      trigger: "axis",
      backgroundColor: color("--superficie"), borderColor: color("--borde"),
      textStyle: { color: color("--tinta"), fontSize: 12 },
      axisPointer: { type: "line", lineStyle: { color: color("--eje") } },
    },
  };
}

function ejes(i, formato) {
  return {
    xAxis: {
      type: "category", data: i.meses, axisTick: { show: false },
      axisLine: { lineStyle: { color: color("--eje") } }, axisLabel: { color: color("--tinta-3") },
    },
    yAxis: {
      type: "value", splitLine: { lineStyle: { color: color("--grilla") } },
      axisLabel: { color: color("--tinta-3"), formatter: (v) => fmtEje(v, formato) },
    },
  };
}

function lineaMeta(valor, formato) {
  if (valor === null || valor === undefined) return undefined;
  return {
    symbol: "none", silent: true,
    lineStyle: { color: color("--meta"), type: [6, 4], width: 1.5 },
    label: { formatter: "Meta " + fmt(valor, formato), position: "insideEndTop", color: color("--tinta-2"), fontSize: 11 },
    data: [{ yAxis: valor }],
  };
}

function iniciar(caja) {
  const g = echarts.init(caja, null, { renderer: "svg" });
  estado.graficos.push(g);
  return g;
}

function filaTooltip(marca, nombre, valor) {
  return `<div style="display:flex;justify-content:space-between;gap:16px"><span>${marca}${esc(nombre)}</span><b>${valor}</b></div>`;
}

function graficoPct(caja, i) {
  const pct = i.porcentaje;
  const g = iniciar(caja);
  g.setOption({
    ...base(), ...ejes(i, "porcentaje"),
    tooltip: {
      ...base().tooltip,
      formatter: (ps) => {
        const n = ps[0].dataIndex;
        let t = `<b>${i.meses[n]} ${estado.anio}</b>`;
        t += filaTooltip(ps[0].marker, pct.etiqueta, fmt(pct.valores[n], "porcentaje"));
        i.series.forEach((s) => (t += filaTooltip("", s.nombre, fmt(s.valores[n], i.formato))));
        if (pct.meta !== null) t += filaTooltip("", "Meta", fmt(pct.meta, "porcentaje"));
        return t;
      },
    },
    series: [{
      name: pct.etiqueta, type: "line", data: pct.valores, connectNulls: false,
      lineStyle: { width: 2, color: color("--serie-1") }, itemStyle: { color: color("--serie-1") },
      symbol: "circle", symbolSize: 8,
      areaStyle: { color: color("--serie-1"), opacity: 0.08 },
      markLine: lineaMeta(pct.meta, "porcentaje"),
    }],
  });
}

function graficoSeries(caja, i) {
  const g = iniciar(caja);
  const lineas = i.tipo_grafico === "lineas";
  g.setOption({
    ...base(), ...ejes(i, i.formato),
    legend: i.series.length > 1 ? { top: 0, left: 0, icon: "roundRect", itemWidth: 10, itemHeight: 10, textStyle: { color: color("--tinta-2") } } : undefined,
    tooltip: {
      ...base().tooltip,
      formatter: (ps) => `<b>${ps[0].name} ${estado.anio}</b>` +
        ps.map((p) => filaTooltip(p.marker, p.seriesName, fmt(p.value, i.formato))).join(""),
    },
    series: i.series.map((s, n) => ({
      name: s.nombre, type: lineas ? "line" : "bar", data: s.valores,
      itemStyle: { color: color(SERIES[n % SERIES.length]), borderRadius: lineas ? 0 : [4, 4, 0, 0] },
      lineStyle: { width: 2 }, symbol: "circle", symbolSize: 8,
      barMaxWidth: 22, barGap: "12%",
      markLine: n === 0 ? lineaMeta(i.meta_serie, i.formato) : undefined,
    })),
  });
}

function chispa(caja, i) {
  const valores = i.porcentaje?.valores || i.series[0].valores;
  const meta = i.porcentaje ? i.porcentaje.meta : i.meta_serie;
  const g = iniciar(caja);
  g.setOption({
    animation: false,
    grid: { left: 4, right: 4, top: 4, bottom: 4 },
    xAxis: { type: "category", show: false, data: i.meses, boundaryGap: false },
    yAxis: { type: "value", show: false, scale: true },
    series: [{
      type: "line", data: valores, symbol: "none", silent: true,
      lineStyle: { width: 2, color: color("--serie-1") },
      areaStyle: { color: color("--serie-1"), opacity: 0.08 },
      markLine: meta === null || meta === undefined ? undefined : {
        symbol: "none", silent: true, label: { show: false },
        lineStyle: { color: color("--meta"), type: [4, 3], width: 1 }, data: [{ yAxis: meta }],
      },
    }],
  });
}

// ---------------------------------------------------------------- inicio

function iniciarApp() {
  const sel = $("#anio");
  const hoy = new Date().getFullYear();
  for (let a = hoy; a >= hoy - 3; a--) sel.add(new Option(a, a));
  sel.value = estado.anio;
  sel.addEventListener("change", () => { estado.anio = +sel.value; estado.datos = null; cargar(); });
  $("#refrescar").addEventListener("click", () => cargar(true));
  window.addEventListener("hashchange", render);
  window.addEventListener("resize", () => estado.graficos.forEach((g) => g.resize()));
  matchMedia("(prefers-color-scheme: dark)").addEventListener("change", render);
  setInterval(pintarActualizado, 30000);
  // Renueva solo mientras la pestaña está visible
  setInterval(() => { if (!document.hidden && estado.datos) cargar(false, true); }, 60000);
  cargar();
}

iniciarApp();
