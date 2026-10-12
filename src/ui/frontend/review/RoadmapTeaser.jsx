import { useEffect, useRef, useState } from "react";
import { getRoadmapTeaser } from "../api/audits.js";
import { track } from "../lib/analytics.js";

// Lead-generation teaser: counts and a blurred placeholder roadmap only. The
// server payload never carries recommendation text.
const CAL_ORIGIN = /^https:\/\/(app\.)?cal\.com$/;
const CHIPS = [["quickWins", "quickWin"], ["structural", "structuralOne"], ["axes", "axesOne"]];
const BAR_WIDTHS = [72, 58, 81, 46];

function LockIcon() {
  return <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><rect x="4" y="11" width="16" height="10" rx="2"/><path d="M8 11V7a4 4 0 0 1 8 0v4"/></svg>;
}

export default function RoadmapTeaser({ api, auditId, lang = "en" }) {
  const [data, setData] = useState(null);
  const [open, setOpen] = useState(false);
  const [frameRequested, setFrameRequested] = useState(false);
  const section = useRef(null);
  const dialog = useRef(null);
  const cta = useRef(null);
  const closeButton = useRef(null);

  useEffect(() => {
    let live = true;
    getRoadmapTeaser(api, auditId, lang).then((payload) => live && setData(payload)).catch(() => live && setData(null));
    return () => { live = false; };
  }, [api, auditId, lang]);

  useEffect(() => {
    if (!data?.enabled || !section.current || !("IntersectionObserver" in window)) return undefined;
    const observer = new IntersectionObserver((entries) => {
      if (entries.some((entry) => entry.isIntersecting)) { track("roadmap_teaser_viewed"); observer.disconnect(); }
    }, { threshold: 0.4 });
    observer.observe(section.current);
    return () => observer.disconnect();
  }, [data]);

  useEffect(() => {
    const onMessage = (event) => {
      if (!CAL_ORIGIN.test(event.origin)) return;
      const type = String(event.data?.type || event.data?.action || event.data?.data?.type || "");
      if (type.includes("bookingSuccessful")) track("booking_completed");
    };
    window.addEventListener("message", onMessage);
    return () => window.removeEventListener("message", onMessage);
  }, []);

  useEffect(() => {
    const element = dialog.current;
    if (!element) return;
    if (open && !element.open) { element.showModal(); closeButton.current?.focus(); }
    if (!open && element.open) element.close();
  }, [open]);

  if (!data?.enabled) return null;
  const { copy, counts, expert } = data;
  const hasFindings = counts.quickWins + counts.structural > 0;
  const openBooking = (event) => {
    track("booking_cta_clicked");
    if (typeof dialog.current?.showModal !== "function") return; // fall back to the new-tab link
    event.preventDefault();
    setFrameRequested(true);
    setOpen(true);
  };

  return <section id="roadmap-teaser" className="rt" lang={data.lang} aria-labelledby="rt-heading" ref={section}>
    <div className="rt-card">
      <div className="rt-stage">
        <div className="rt-preview" aria-hidden="true"><div className="rt-rows">{BAR_WIDTHS.map((width, index) => <div className="rt-row" key={width}><span className={`rt-dot rt-dot-${index}`}/><span className="rt-bar" style={{ width: `${width}%` }}/><span className="rt-pill"/></div>)}</div></div>
        <div className="rt-lock"><span className="rt-lock-icon" aria-hidden="true"><LockIcon/></span><span>{copy.lockLabel}</span></div>
      </div>
      <div className="rt-content">
        <p className="rt-eyebrow">{copy.eyebrow}</p>
        <h2 id="rt-heading">{hasFindings ? copy.heading : copy.cleanHeading}</h2>
        <p className="rt-body">{hasFindings ? copy.body : copy.cleanBody}</p>
        {hasFindings && <ul className="rt-chips">{CHIPS.filter(([key]) => counts[key] > 0).map(([key, one]) => <li className="rt-chip" key={key}><strong>{counts[key]}</strong> {counts[key] === 1 ? copy[one] : copy[key]}</li>)}</ul>}
        <div className="rt-footer">
          <div className="rt-expert">
            {expert.photoUrl ? <img className="rt-avatar" src={expert.photoUrl} alt=""/> : <span className="rt-avatar" aria-hidden="true">{expert.initials}</span>}
            <div><p className="rt-name">{expert.name}</p><p className="rt-title">{expert.title}</p></div>
          </div>
          <a className="rt-cta" ref={cta} href={data.bookingUrl} target="_blank" rel="noopener" onClick={openBooking}>{copy.cta}<span className="rt-sr"> ({copy.newTab})</span><span aria-hidden="true" className="rt-arrow">→</span></a>
        </div>
      </div>
    </div>
    <dialog className="rt-dialog" ref={dialog} aria-labelledby="rt-dialog-title" onClose={() => { setOpen(false); cta.current?.focus(); }} onClick={(event) => { if (event.target === dialog.current) setOpen(false); }}>
      <div className="rt-dialog-head"><h2 id="rt-dialog-title">{copy.modalTitle}</h2><div className="rt-dialog-actions"><a className="rt-newtab" href={data.bookingUrl} target="_blank" rel="noopener">{copy.openNewTab}</a><button type="button" className="rt-close" ref={closeButton} onClick={() => setOpen(false)}>{copy.close}</button></div></div>
      {frameRequested && <iframe className="rt-frame" title={copy.modalTitle} src={data.embedUrl}/>}
    </dialog>
  </section>;
}
