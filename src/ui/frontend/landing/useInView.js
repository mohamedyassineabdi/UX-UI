import { useEffect, useRef, useState } from "react";

// One IntersectionObserver per element. Browsers without it treat everything as in view.
export default function useInView({ threshold = 0, rootMargin = "0px", once = false } = {}) {
  const ref = useRef(null);
  const [inView, setInView] = useState(() => typeof IntersectionObserver === "undefined");
  useEffect(() => {
    const node = ref.current;
    if (!node || typeof IntersectionObserver === "undefined") return undefined;
    const observer = new IntersectionObserver(([entry]) => {
      setInView(entry.isIntersecting);
      if (entry.isIntersecting && once) observer.disconnect();
    }, { threshold, rootMargin });
    observer.observe(node);
    return () => observer.disconnect();
  }, [threshold, rootMargin, once]);
  return [ref, inView];
}
