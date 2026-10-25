// Helpers shared by the scorebook (web/index.html) and the benchmark page (web/bench/index.html).

export const $ = id => document.getElementById(id);
export const esc = s => String(s).replace(/[&<>"]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" })[c]);

// Numbers as printed: a true minus sign, "—" where there is no value.
export const MINUS = "\u2212";
const missing = x => x === null || x === undefined;
export const f4 = x => (missing(x) ? "—" : x.toFixed(4));
export const signed = (x, d = 4) => (missing(x) ? "—" : (x < 0 ? MINUS : "+") + Math.abs(x).toFixed(d));
export const pct = x => (missing(x) ? "—" : `${x.toFixed(1)}%`);
export const count = x => Number(x).toLocaleString();
// A 95% interval in a table cell, and in a sentence.
export const ciBracket = ([lo, hi]) => `[${signed(lo)}, ${signed(hi)}]`;
export const ciTo = ([lo, hi]) => `${signed(lo)} to ${signed(hi)}`;

// bench.py's verdict on a paired comparison: its stamp class, the stamp's words, and the sentence.
export const VERDICTS = {
  "clear win": { cls: "win", short: "Clear win", sentence: "A clear win for Bend" },
  "clear loss": { cls: "loss", short: "Clear loss", sentence: "A clear loss for Bend" },
  "no clear difference": { cls: "even", short: "No clear difference", sentence: "No clear difference" },
};
const verdict = v => VERDICTS[v] || VERDICTS["no clear difference"];
export const verdictStamp = v => `<b class="v ${verdict(v).cls}">${verdict(v).short}</b>`;
export const verdictSentence = v => verdict(v).sentence;

// The printed legend: a drawn sample of each line as the chart strokes it, its name, its source.
// dot is "filled", "open" (stock fill, 1.5px ring) or absent; width, dash and cap as the line is stroked.
export function legendItem(name, note, { stroke, dash, width, cap, dot }) {
  const line = (width ? `stroke-width:${width};` : "") + (dash ? `stroke-dasharray:${dash};` : "") + (cap ? `stroke-linecap:${cap};` : "");
  return `<li><svg viewBox="0 0 30 10" aria-hidden="true"><line x1="1" y1="5" x2="29" y2="5" stroke="${stroke}"`
    + (line ? ` style="${line}"` : "") + `/>`
    + (dot === "filled" ? `<circle cx="15" cy="5" r="2.6" fill="${stroke}"/>` : "")
    + (dot === "open" ? `<circle cx="15" cy="5" r="2.6" fill="var(--stock)" stroke="${stroke}" stroke-width="1.5"/>` : "")
    + `</svg><b>${name}</b>${note}</li>`;
}
