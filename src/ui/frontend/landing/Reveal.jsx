import { useState } from "react";
import useInView from "./useInView.js";

function motionAllowed() {
  try { return !window.matchMedia("(prefers-reduced-motion: reduce)").matches; } catch { return true; }
}

// Fades its element in once it scrolls into view. Content stays visible unless the observer and motion are both available.
export default function Reveal({ as: Tag = "div", className = "", children, ...rest }) {
  const [ref, inView] = useInView({ rootMargin: "0px 0px -10% 0px", once: true });
  const [armed] = useState(() => typeof IntersectionObserver !== "undefined" && motionAllowed());
  return <Tag ref={ref} className={`lp-reveal ${armed && !inView ? "is-pending" : ""} ${className}`.trim()} {...rest}>{children}</Tag>;
}
