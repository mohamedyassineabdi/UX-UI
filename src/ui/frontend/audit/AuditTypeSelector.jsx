import Icon3D from "../components/Icon3D.jsx";
import Icon from "../components/Icon.jsx";
export const SOURCES = [
  { id: "website", name: "Website", description: "Explore a live website" },
  { id: "screenshot", name: "Screenshots", description: "Review captured screens" },
  { id: "mobile", name: "Mobile App", description: "Explore an Android app" },
  { id: "figma", name: "Figma", description: "Review a design file" },
];
export default function AuditTypeSelector({ value, onChange }) {
  return <fieldset className="source-fieldset"><legend><span className="step-number">1</span> Choose your source</legend><div className="source-grid">{SOURCES.map(source => <label className={`source-card ${value === source.id ? "is-selected" : ""}`} key={source.id}><input type="radio" name="audit-source" value={source.id} checked={value === source.id} onChange={() => onChange(source.id)}/><span className="source-icon"><Icon3D name={source.id} size={44}/></span><span className="source-copy"><strong>{source.name}</strong><span>{source.description}</span></span><span className="source-check"><Icon name="check" size={14}/></span></label>)}</div></fieldset>;
}
