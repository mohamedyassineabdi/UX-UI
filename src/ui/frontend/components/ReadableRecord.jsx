// Shows structured data as labelled text, never as raw JSON.
const humanize = key => String(key).replace(/([a-z0-9])([A-Z])/g, "$1 $2").replace(/[_-]+/g, " ").trim().replace(/^./, c => c.toUpperCase());
const empty = value => value == null || value === "" || (Array.isArray(value) && !value.length) || (typeof value === "object" && !Array.isArray(value) && !Object.keys(value).length);

export function ReadableValue({ value }) {
  if (empty(value)) return <span className="readable-empty">—</span>;
  if (typeof value === "boolean") return <span>{value ? "Yes" : "No"}</span>;
  if (Array.isArray(value)) return value.every(item => typeof item !== "object" || item === null) ? <span>{value.join(", ")}</span> : <ul className="readable-list">{value.map((item, index) => <li key={index}><ReadableValue value={item}/></li>)}</ul>;
  if (typeof value === "object") return <ReadableRecord record={value}/>;
  return <span>{String(value)}</span>;
}

// fields: optional [[key, label], ...] to pick and order what is shown.
export default function ReadableRecord({ record, fields }) {
  const entries = fields ? fields.map(([key, label]) => [label, record?.[key]]) : Object.entries(record || {}).map(([key, value]) => [humanize(key), value]);
  const shown = entries.filter(([, value]) => !empty(value));
  if (!shown.length) return <p className="readable-empty">No further details recorded.</p>;
  return <dl className="readable-record">{shown.map(([label, value]) => <div key={label}><dt>{label}</dt><dd><ReadableValue value={value}/></dd></div>)}</dl>;
}
