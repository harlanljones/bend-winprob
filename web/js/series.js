// Chart line marks: the one place a line's ink, width, dash and points are set. Each page inks its
// Pele chart from these (inkLines) and draws its printed legend from the same objects (legendItem).
// id is the Pele series name, which Pele writes as the line's data-id.

export const SERIES = {
  bend: { id: "Bend", stroke: "var(--graphite)", dot: "filled" },
  mlb: { id: "MLB", stroke: "var(--print)", dot: "open" },
};

// Prediction-market reference prices: one optional CSV column per venue, in display order.
// The venue keys are the ones markets.py writes and cloudflare/worker.js accepts.
export const VENUES = [
  { key: "kalshi", name: "Kalshi", note: "market price", stroke: "var(--graphite-soft)", dash: "8 3", width: 1.5, cap: "butt" },
  { key: "polymarket", name: "Polymarket", note: "international market price", stroke: "var(--print)", dash: "8 3 1.5 3", width: 1.5, cap: "butt" },
  { key: "polymarket_us", name: "Polymarket US", note: "US-regulated market price", stroke: "var(--graphite-soft)", dash: "0 4", width: 2, cap: "round" },
].map(v => ({ ...v, id: v.name }));

// CSS that inks each series inside `scope`: Pele colors lines by position, so every line is set
// here by its data-id. Points: "filled" in the line's ink, "open" on stock with a 1.5px ring, else none.
export function lineCss(scope, series) {
  return series.map(({ id, stroke, width, dash, cap, dot }) => {
    const line = `${scope} .pele-line[data-id="${id}"]`;
    const path = [`stroke: ${stroke}`, width && `stroke-width: ${width}`, dash && `stroke-dasharray: ${dash}`, cap && `stroke-linecap: ${cap}`];
    return `${line} path { ${path.filter(Boolean).join("; ")}; }\n`
      + (dot === "filled" ? `${line} circle { fill: ${stroke}; stroke: none; }\n`
        : dot === "open" ? `${line} circle { fill: var(--stock); stroke: ${stroke}; stroke-width: 1.5; }\n`
        : `${line} circle { display: none; }\n`);
  }).join("");
}

// Add those rules to the page once, before the chart is drawn.
export function inkLines(scope, series) {
  const style = document.createElement("style");
  style.textContent = lineCss(scope, series);
  document.head.append(style);
}
