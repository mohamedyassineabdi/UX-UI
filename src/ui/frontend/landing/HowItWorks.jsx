import { Fragment, useEffect, useState } from "react";
import Icon from "../components/Icon.jsx";
import capture from "./assets/w3c-bad-citylights.jpg";
import Reveal from "./Reveal.jsx";
import useInView from "./useInView.js";

// Three steps from capture to sign-off. Wide screens show one panel beside the list for the active step;
// narrow screens show each step's panel inline instead.
const OUTLINES = [[626, 33, 145, 19], [175, 144, 434, 69], [0, 146, 155, 140]];
const pct = (value, total) => `${(value / total) * 100}%`;

function StepPanel({ index, lang, t, axes }) {
  if (index === 0) return <div className="lp-how-panel lp-how-capture">
    <img src={capture} width="780" height="560" alt=""/>
    {OUTLINES.map(([x, y, w, h]) => <span key={`${x}-${y}`} aria-hidden="true" style={{ left: pct(x, 780), top: pct(y, 560), width: pct(w, 780), height: pct(h, 560) }}/>)}
  </div>;
  if (index === 1) return <div className="lp-how-panel lp-how-check">
    <ul className="lp-how-axes">{axes.map(axis => <li key={axis.id}>{axis.short[lang]}</li>)}</ul>
    <span className="lp-meter"><span>{t.coverage}</span><i><b style={{ width: "85%" }}/></i><em>85%</em></span>
  </div>;
  return <div className="lp-how-panel lp-how-sign">
    <code>select · WCAG 4.1.2 · axe-core</code>
    <span className="lp-flow">{t.flow.map((step, at) => <Fragment key={step}>{at > 0 && <Icon name="arrow" size={12}/>}<span className={at === t.flow.length - 1 ? "is-on" : undefined}>{step}</span></Fragment>)}</span>
  </div>;
}

// A step becomes active when it crosses a thin band at the middle of the viewport. Scrolling is never hijacked.
function Step({ index, active, onEnter, children }) {
  const [ref, inView] = useInView({ rootMargin: "-45% 0px -45% 0px" });
  useEffect(() => { if (inView) onEnter(index); }, [inView, index, onEnter]);
  return <li ref={ref} className="lp-how-step" aria-current={index === active ? "step" : undefined}>{children}</li>;
}

export default function HowItWorks({ lang, t, axes }) {
  const [active, setActive] = useState(0);
  return <section className="lp-wrap lp-how" aria-labelledby="lp-how-title">
    <Reveal as="h2" id="lp-how-title">{t.howTitle}</Reveal>
    <div className="lp-how-grid">
      <ol className="lp-how-steps">{t.steps.map(([title, text], index) => <Step key={title} index={index} active={active} onEnter={setActive}>
        <span className="lp-how-num" aria-hidden="true"/>
        <h3>{title}</h3>
        <p>{text}</p>
        <StepPanel index={index} lang={lang} t={t} axes={axes}/>
      </Step>)}</ol>
      <div className="lp-how-stage">
        <span className="lp-how-rail" aria-hidden="true"><b style={{ transform: `scaleY(${(active + 1) / t.steps.length})` }}/></span>
        <div className="lp-how-show" key={active}><StepPanel index={active} lang={lang} t={t} axes={axes}/></div>
      </div>
    </div>
  </section>;
}
