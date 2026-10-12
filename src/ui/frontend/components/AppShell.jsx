import { useEffect, useState } from "react";
import GlassSurface from "./GlassSurface.jsx";
import logo from "../assets/ey-studio-plus.png";
export default function AppShell({ children, job, view, onView }) {
  const [scrolled, setScrolled] = useState(false);
  useEffect(() => {
    const update = () => setScrolled(window.scrollY > 12);
    update(); window.addEventListener("scroll", update, { passive: true });
    return () => window.removeEventListener("scroll", update);
  }, []);
  return <><a className="skip-link" href="#main-content">Skip to content</a><header className={`topbar ${scrolled ? "is-scrolled" : ""}`}><GlassSurface className="app-chrome"><a className="brand" href="/" aria-label="EY Studio Plus home"><img className="brand-logo" src={logo} alt="" width="1000" height="390"/></a><nav aria-label="Workspace"><button className={`nav-item ${view === "setup" ? "is-active" : ""}`} aria-current={view === "setup" ? "page" : undefined} onClick={() => onView("setup")}>New audit</button>{job && <button className={`nav-item ${view === "workspace" ? "is-active" : ""}`} aria-current={view === "workspace" ? "page" : undefined} onClick={() => onView("workspace")}>Current audit</button>}</nav></GlassSurface></header><main id="main-content" tabIndex={-1}>{children}</main><footer className="app-footer"><span>Built around evidence. Refined by human judgment.</span><span>EY Studio +</span></footer></>;
}
