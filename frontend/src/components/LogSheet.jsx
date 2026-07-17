// Driver's Daily Log — a faithful render of the standard paper ELD form
// (FMCSA record of duty status). SVG draws the precise 24h grid, duty line,
// Total Hours column and remarks drop-lines; HTML frames the header fields and
// the 70hr/8day recap.

const ROWS = [
  ["off_duty", "1. Off Duty"],
  ["sleeper", "2. Sleeper Berth"],
  ["driving", "3. Driving"],
  ["on_duty", "4. On Duty (not driving)"],
];
const ROW_INDEX = Object.fromEntries(ROWS.map(([k], i) => [k, i]));

// SVG geometry
const LABEL_W = 172;
const GRID_W = 768;
const TOTAL_W = 88;
const ROW_H = 52;
const GRID_TOP = 30;
const N_ROWS = ROWS.length;
const GRID_BOTTOM = GRID_TOP + N_ROWS * ROW_H;
const REMARKS_H = 188; // room for angled city labels below the grid
const SVG_W = LABEL_W + GRID_W + TOTAL_W;
const SVG_H = GRID_BOTTOM + REMARKS_H;

// Tick heights: hour = full row, 30-min = medium, 15/45-min = short.
const TICK_MED = 22;
const TICK_SHORT = 12;

const toMin = (hhmm) => {
  if (hhmm === "24:00") return 1440;
  const [h, m] = hhmm.split(":").map(Number);
  return h * 60 + m;
};
const xOf = (min) => LABEL_W + (min / 1440) * GRID_W;
const rowTop = (i) => GRID_TOP + i * ROW_H;
const rowMid = (i) => rowTop(i) + ROW_H / 2;

function hourLabel(h) {
  if (h === 0 || h === 24) return "Midnight";
  if (h === 12) return "Noon";
  return String(h > 12 ? h - 12 : h); // 12-hour clock, as on the paper form
}

const truncate = (s, n = 22) => (s && s.length > n ? s.slice(0, n - 1) + "…" : s);

function Field({ label, value, wide }) {
  return (
    <div className={`log-field${wide ? " wide" : ""}`}>
      <div className="log-field-value">{value || " "}</div>
      <div className="log-field-label">{label}</div>
    </div>
  );
}

export default function LogSheet({ day }) {
  // From/To use place-named changes; the remarks lane shows every duty change
  // (breaks/rests included, labeled by their note when there's no city).
  const cityRemarks = (day.remarks || []).filter((r) => r.location);
  const laneRemarks = (day.remarks || []).filter((r) => r.location || r.note);
  const from = cityRemarks[0]?.location || "";
  const to = cityRemarks[cityRemarks.length - 1]?.location || "";

  // One continuous stepped line: horizontal runs joined by verticals at each
  // duty change (segments are contiguous, so this needs no pen-up moves).
  const path = [];
  day.segments.forEach((seg, i) => {
    const x1 = xOf(toMin(seg.start)).toFixed(1);
    const x2 = xOf(toMin(seg.end)).toFixed(1);
    const y = rowMid(ROW_INDEX[seg.status]);
    path.push(`${i === 0 ? "M" : "L"} ${x1} ${y}`); // vertical transition (except first)
    path.push(`L ${x2} ${y}`);
  });

  const ticks = [];
  for (let i = 0; i < N_ROWS; i++) {
    const bottom = rowTop(i) + ROW_H;
    for (let m = 15; m < 1440; m += 15) {
      if (m % 60 === 0) continue; // hour lines drawn separately, full height
      const half = m % 60 === 30;
      const h = half ? TICK_MED : TICK_SHORT;
      ticks.push(
        <line key={`t${i}-${m}`} x1={xOf(m)} y1={bottom - h} x2={xOf(m)} y2={bottom}
          stroke={half ? "#334155" : "#64748b"} strokeWidth={half ? 1.6 : 1.1} />
      );
    }
  }

  return (
    <div className="logsheet">
      {/* header */}
      <div className="log-header">
        <div className="log-title">
          <strong>Driver's Daily Log</strong>
          <span>(24 hours)</span>
        </div>
        <Field label="Date (mm / dd / yyyy)" value={day.date} />
        <Field label="Total Miles Driving Today" value={day.total_miles} />
        <Field label="From" value={from} wide />
        <Field label="To" value={to} wide />
        <Field label="Name of Carrier" value="" wide />
        <Field label="Main Office Address" value="" wide />
        <Field label="Truck / Trailer No." value="" />
        <Field label="Home Terminal Address" value="" wide />
      </div>

      {/* grid — scrolls horizontally on narrow screens instead of shrinking */}
      <div className="logsheet-scroll">
      <svg viewBox={`0 0 ${SVG_W} ${SVG_H}`} className="logsheet-svg" role="img"
        aria-label={`Daily log grid for ${day.date}: off duty ${day.totals.off_duty}h, `
          + `sleeper ${day.totals.sleeper}h, driving ${day.totals.driving}h, `
          + `on duty ${day.totals.on_duty}h`}>
        <title>{`Driver's daily log grid for ${day.date}`}</title>
        {/* hour labels */}
        {Array.from({ length: 25 }, (_, h) => (
          <text key={`hl${h}`} x={xOf(h * 60)} y={GRID_TOP - 9} fontSize="11"
            textAnchor={h === 0 ? "start" : h === 24 ? "end" : "middle"} fill="#475569">
            {hourLabel(h)}
          </text>
        ))}
        <text x={LABEL_W + GRID_W + TOTAL_W / 2} y={GRID_TOP - 9} fontSize="10.5"
          textAnchor="middle" fill="#475569">Total Hrs</text>

        {/* quarter/half-hour ticks */}
        {ticks}

        {/* full-height hour lines */}
        {Array.from({ length: 25 }, (_, h) => (
          <line key={`hln${h}`} x1={xOf(h * 60)} y1={GRID_TOP} x2={xOf(h * 60)} y2={GRID_BOTTOM}
            stroke={h % 6 === 0 ? "#1e293b" : "#64748b"} strokeWidth={h % 6 === 0 ? 2 : 1.3} />
        ))}

        {/* rows: separators, labels, totals */}
        {ROWS.map(([key, label], i) => (
          <g key={key}>
            <line x1={LABEL_W} y1={rowTop(i)} x2={LABEL_W + GRID_W} y2={rowTop(i)}
              stroke="#475569" strokeWidth="0.8" />
            <text x={LABEL_W - 10} y={rowMid(i) + 4} fontSize="13" textAnchor="end" fill="#1f2937">
              {label}
            </text>
            <text x={LABEL_W + GRID_W + TOTAL_W / 2} y={rowMid(i) + 6} fontSize="17"
              textAnchor="middle" fill="#0f172a" fontWeight="700">
              {day.totals[key]}
            </text>
          </g>
        ))}
        <line x1={LABEL_W} y1={GRID_BOTTOM} x2={LABEL_W + GRID_W} y2={GRID_BOTTOM}
          stroke="#475569" strokeWidth="0.8" />
        {/* total-hours column separators */}
        <line x1={LABEL_W + GRID_W} y1={GRID_TOP} x2={LABEL_W + GRID_W} y2={GRID_BOTTOM}
          stroke="#475569" strokeWidth="1" />
        <line x1={SVG_W} y1={GRID_TOP} x2={SVG_W} y2={GRID_BOTTOM} stroke="#475569" strokeWidth="1" />
        <text x={LABEL_W + GRID_W + TOTAL_W / 2} y={GRID_BOTTOM + 18} fontSize="14"
          textAnchor="middle" fill="#0f172a" fontWeight="700">= {day.total_hours}</text>

        {/* duty line */}
        <path d={path.join(" ")} fill="none" stroke="#1d4ed8" strokeWidth="3"
          strokeLinejoin="round" strokeLinecap="round" />

        {/* remarks: drop-lines + angled city labels */}
        <text x={LABEL_W - 10} y={GRID_BOTTOM + 18} fontSize="11.5" textAnchor="end"
          fill="#475569" fontStyle="italic">Remarks</text>
        {laneRemarks.map((r, i) => {
          const x = xOf(toMin(r.time));
          return (
            <g key={`rm${i}`}>
              <line x1={x} y1={GRID_BOTTOM} x2={x} y2={GRID_BOTTOM + 20}
                stroke="#334155" strokeWidth="1.2" />
              <text x={x + 2} y={GRID_BOTTOM + 26} fontSize="13" fontWeight="600" fill="#0f172a"
                transform={`rotate(60 ${x + 2} ${GRID_BOTTOM + 26})`}>
                {truncate(r.location || r.note)}
              </text>
            </g>
          );
        })}
      </svg>
      </div>

      {/* recap */}
      <div className="log-recap">
        <span className="log-recap-title">Recap · 70 hr / 8 day</span>
        <div><span>{day.recap.on_duty_today}</span> on-duty hrs today</div>
        <div><span>{day.recap.used_last_8_days}</span> used, last 8 days</div>
        <div><span>{day.recap.available_tomorrow}</span> available tomorrow</div>
      </div>
    </div>
  );
}
