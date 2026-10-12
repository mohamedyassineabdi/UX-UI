import { useEffect, useRef } from "react";

// The report cover's ring field (src/report/client/render.py::_dot_field), drawn live: rings fade outward from a clear
// zone kept for the headline. The hero drifts and parts around the mouse; the quiet variant is one static frame.
const PALETTE = ["#5B3FD9", "#9AA1B5", "#9AA1B5", "#E8C300"];
const RING_GAP = 26, DOT_GAP = 30, SQUASH = .86, MAX_DOTS = 1400, REACH = 140;

function rings(width, height, spread) {
  const cx = width / 2, cy = height / 2, far = Math.hypot(cx, cy / SQUASH);
  // On narrow screens the hero text fills the height, so the field becomes a frame above and below it.
  const rx = Math.min(width * .4, 540), ry = width < 720 ? height * .46 : Math.min(height * .37, 340);
  const shape = (x, y) => (((x - cx) / rx) ** 4 + ((y - cy) / ry) ** 4) ** .25; // 1 on the edge of the rounded clear zone
  const outer = Math.max(shape(0, 0), 1.5);
  const dots = [];
  for (let ring = 1; ring * RING_GAP * spread <= far + RING_GAP; ring += 1) {
    const radius = ring * RING_GAP * spread, count = Math.round(2 * Math.PI * radius / (DOT_GAP * spread));
    for (let step = 0; step < count; step += 1) {
      const angle = 2 * Math.PI * step / count + ring * .37;
      const x = cx + radius * Math.cos(angle), y = cy + radius * Math.sin(angle) * SQUASH;
      if (x < -4 || x > width + 4 || y < -4 || y > height + 4) continue;
      const zone = shape(x, y);
      if (zone <= 1) continue;
      // Strongest just outside the clear zone, fading towards the corners, with a soft inner edge.
      const fade = Math.max(0, 1 - (zone - 1) / (outer - 1)), edge = Math.min(1, (zone - 1) / .12);
      dots.push({ x, y, r: .9 + 1.7 * fade, color: PALETTE[(ring + step) % 4], alpha: (.16 + .6 * fade) * edge });
    }
  }
  return dots;
}

// Pure: the same size always gives the same field, never more than MAX_DOTS dots.
export function buildField(width, height) {
  if (!(width > 0 && height > 0)) return [];
  let spread = 1, dots = rings(width, height, spread);
  while (dots.length > MAX_DOTS && spread < 8) {
    spread *= Math.sqrt(dots.length / MAX_DOTS) * 1.02;
    dots = rings(width, height, spread);
  }
  return dots.slice(0, MAX_DOTS);
}

function reducedMotion() {
  try { return window.matchMedia("(prefers-reduced-motion: reduce)").matches; } catch { return false; }
}

export default function DotField({ variant = "hero" }) {
  const canvasRef = useRef(null);
  useEffect(() => {
    const canvas = canvasRef.current, context = canvas?.getContext("2d");
    if (!context) return undefined;
    const still = variant !== "hero" || reducedMotion(), strength = variant === "hero" ? 1 : .5;
    const pointer = { x: -1e4, y: -1e4 };
    let dots = [], width = 0, height = 0, ratio = 1, frame = 0, start = 0, visible = typeof IntersectionObserver === "undefined";

    const paint = time => {
      const elapsed = still ? Infinity : start ? time - start : 0; // before the loop starts, the fade-in has not begun
      context.setTransform(ratio, 0, 0, ratio, 0, 0);
      context.clearRect(0, 0, width, height);
      for (const dot of dots) {
        const appear = Math.min(1, Math.max(0, (elapsed - dot.order * 600) / 300)); // centre-out over ~900 ms
        if (!appear) continue;
        context.globalAlpha = dot.alpha * appear * strength;
        context.fillStyle = dot.color;
        context.beginPath();
        context.arc(dot.px, dot.py, dot.r, 0, 2 * Math.PI);
        context.fill();
      }
    };
    // Each dot drifts around its home, is pushed away inside REACH of the mouse, and springs back.
    const move = time => {
      for (const dot of dots) {
        let forceX = (dot.x + Math.sin(time * .0006 + dot.phase) * 3 - dot.px) * .06;
        let forceY = (dot.y + Math.cos(time * .0005 + dot.phase) * 3 - dot.py) * .06;
        const dx = dot.px - pointer.x, dy = dot.py - pointer.y, distance = Math.hypot(dx, dy);
        if (distance < REACH && distance > .1) {
          const push = (1 - distance / REACH) * 6;
          forceX += dx / distance * push; forceY += dy / distance * push;
        }
        dot.vx = (dot.vx + forceX) * .82; dot.vy = (dot.vy + forceY) * .82;
        dot.px += dot.vx; dot.py += dot.vy;
      }
    };
    const loop = time => {
      if (!start) start = time;
      move(time);
      paint(time);
      frame = requestAnimationFrame(loop);
    };
    // The loop runs only while the field is on screen and the tab is visible.
    const sync = () => {
      const run = !still && visible && document.visibilityState === "visible";
      if (run && !frame) frame = requestAnimationFrame(loop);
      if (!run && frame) { cancelAnimationFrame(frame); frame = 0; }
    };
    const resize = () => {
      width = canvas.clientWidth; height = canvas.clientHeight;
      ratio = Math.min(window.devicePixelRatio || 1, 2);
      canvas.width = Math.round(width * ratio); canvas.height = Math.round(height * ratio);
      const far = Math.hypot(width, height) / 2 || 1;
      dots = buildField(width, height).map((dot, index) => ({ ...dot, px: dot.x, py: dot.y, vx: 0, vy: 0, phase: index * 2.399, order: Math.hypot(dot.x - width / 2, dot.y - height / 2) / far }));
      canvas.dataset.dots = String(dots.length);
      if (!frame) paint(performance.now());
    };
    const onPointer = event => {
      if (event.pointerType !== "mouse") return;
      const box = canvas.getBoundingClientRect();
      pointer.x = event.clientX - box.left; pointer.y = event.clientY - box.top;
    };
    const onLeave = () => { pointer.x = -1e4; pointer.y = -1e4; };

    resize();
    const resizer = typeof ResizeObserver === "undefined" ? null : new ResizeObserver(resize);
    if (resizer) resizer.observe(canvas); else window.addEventListener("resize", resize);
    const observer = typeof IntersectionObserver === "undefined" ? null : new IntersectionObserver(([entry]) => { visible = entry.isIntersecting; sync(); });
    observer?.observe(canvas);
    document.addEventListener("visibilitychange", sync);
    if (!still) { window.addEventListener("pointermove", onPointer, { passive: true }); document.documentElement.addEventListener("pointerleave", onLeave); }
    sync();
    return () => {
      cancelAnimationFrame(frame); frame = 0;
      resizer?.disconnect(); window.removeEventListener("resize", resize);
      observer?.disconnect();
      document.removeEventListener("visibilitychange", sync);
      window.removeEventListener("pointermove", onPointer);
      document.documentElement.removeEventListener("pointerleave", onLeave);
    };
  }, [variant]);
  return <canvas ref={canvasRef} className={`lp-field is-${variant}`} aria-hidden="true"/>;
}
