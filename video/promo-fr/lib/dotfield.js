// The landing's ring dot field (src/ui/frontend/landing/DotField.jsx), redrawn as a pure function of time so
// every seek paints the same frame. The only randomness is a seeded PRNG.
(function () {
  const PALETTE = ["#5B3FD9", "#9AA1B5", "#9AA1B5", "#E8C300"];
  const LOGO_COLORS = ["#FFE600", "#5B3FD9", "#2E2E38"];
  const RING_GAP = 26, DOT_GAP = 30, SQUASH = .86, MAX_DOTS = 1400;

  function mulberry32(seed) {
    let a = seed >>> 0;
    return function () {
      a = (a + 0x6D2B79F5) >>> 0;
      let t = Math.imul(a ^ (a >>> 15), 1 | a);
      t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
      return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
  }

  const clamp = (v) => Math.min(1, Math.max(0, v));
  const span = (t, t0, t1) => clamp((t - t0) / (t1 - t0));
  const easeOut = (p) => 1 - Math.pow(1 - p, 3);
  const easeInOut = (p) => (p < .5 ? 4 * p * p * p : 1 - Math.pow(-2 * p + 2, 3) / 2);
  const mix = (a, b, p) => a + (b - a) * p;

  function hex(color) {
    const n = parseInt(color.slice(1), 16);
    return [n >> 16, (n >> 8) & 255, n & 255];
  }

  // Concentric rings, strongest just outside an elliptical clear zone kept for the headline.
  function rings(width, height, clear) {
    const cx = width / 2, cy = height / 2, far = Math.hypot(cx, cy / SQUASH);
    const shape = (x, y) => (((x - cx) / clear[0]) ** 4 + ((y - cy) / clear[1]) ** 4) ** .25;
    const outer = Math.max(shape(0, 0), 1.5), dots = [];
    for (let ring = 1; ring * RING_GAP <= far + RING_GAP; ring += 1) {
      const radius = ring * RING_GAP, count = Math.round(2 * Math.PI * radius / DOT_GAP);
      for (let step = 0; step < count; step += 1) {
        const angle = 2 * Math.PI * step / count + ring * .37;
        const x = cx + radius * Math.cos(angle), y = cy + radius * Math.sin(angle) * SQUASH;
        if (x < -4 || x > width + 4 || y < -4 || y > height + 4) continue;
        const zone = shape(x, y);
        if (zone <= 1) continue;
        const fade = Math.max(0, 1 - (zone - 1) / (outer - 1)), edge = Math.min(1, (zone - 1) / .12);
        dots.push({ x, y, r: 1.5 + 2.2 * fade, color: hex(PALETTE[(ring + step) % 4]),
          alpha: (.2 + .62 * fade) * edge, order: radius / far });
      }
    }
    return dots.slice(0, MAX_DOTS);
  }

  // options: seed, clear [rx, ry] of the empty zone, offset (seconds added to t for drift continuity across beats),
  // strength (overall opacity).
  function createDotField(canvas, options) {
    const opts = Object.assign({ seed: 7, clear: [560, 250], offset: 0, strength: 1 }, options);
    const ctx = canvas.getContext("2d"), width = canvas.width, height = canvas.height;
    const dots = rings(width, height, opts.clear), rand = mulberry32(opts.seed);
    for (const dot of dots) { dot.phase = rand() * Math.PI * 2; dot.pick = rand(); dot.slot = rand(); }
    const fx = { appear: null, falls: [], gather: null, fade: null };

    function place(dot, t) {
      const time = t + opts.offset;
      let x = dot.x + Math.sin(time * .55 + dot.phase) * 3.2, y = dot.y + Math.cos(time * .45 + dot.phase) * 3.2;
      let alpha = dot.alpha * opts.strength, r = dot.r, color = dot.color;
      if (fx.appear) alpha *= span(t, fx.appear[0] + dot.order * (fx.appear[1] - fx.appear[0]) * .7,
        fx.appear[0] + dot.order * (fx.appear[1] - fx.appear[0]) * .7 + (fx.appear[1] - fx.appear[0]) * .3);
      for (const fall of fx.falls) {
        if (dot.pick >= fall.fraction) continue;
        const p = span(t, fall.t0 + dot.slot * .35 * (fall.t1 - fall.t0), fall.t1);
        y += p * p * 460;
        alpha *= 1 - easeOut(p);
      }
      const g = fx.gather;
      if (g) {
        const p = easeInOut(span(t, g.t0 + dot.slot * .25 * (g.t1 - g.t0), g.t1));
        const target = g.targets.get(dot);
        if (target) {
          x = mix(x, target[0], p); y = mix(y, target[1], p);
          r = mix(r, 2.7, p);
          color = color.map((c, i) => mix(c, target[3][i], p));
          alpha = mix(alpha, 1, p);
        } else {
          alpha *= 1 - p;
        }
      }
      if (fx.fade) alpha *= 1 - span(t, fx.fade[0], fx.fade[1]);
      return { x, y, r, color, alpha };
    }

    return {
      appear(t0, t1) { fx.appear = [t0, t1]; return this; },
      fall(fraction, t0, t1) { fx.falls.push({ fraction, t0, t1 }); return this; },
      // Sends the dots that survived every fall to points [[x, y, colourIndex]], in a seeded order.
      gatherTo(points, t0, t1) {
        const alive = dots.filter((dot) => fx.falls.every((fall) => dot.pick >= fall.fraction));
        const order = alive.map((dot) => [rand(), dot]).sort((a, b) => a[0] - b[0]).map((pair) => pair[1]);
        const targets = new Map();
        points.forEach((point, i) => {
          if (i < order.length) targets.set(order[i], [point[0], point[1], point[2], hex(LOGO_COLORS[point[2]])]);
        });
        fx.gather = { targets, t0, t1 };
        return this;
      },
      fadeOut(t0, t1) { fx.fade = [t0, t1]; return this; },
      drawAt(t) {
        ctx.clearRect(0, 0, width, height);
        for (const dot of dots) {
          const d = place(dot, t);
          if (d.alpha <= .004) continue;
          ctx.fillStyle = `rgba(${d.color[0] | 0},${d.color[1] | 0},${d.color[2] | 0},${d.alpha.toFixed(3)})`;
          ctx.beginPath();
          ctx.arc(d.x, d.y, d.r, 0, Math.PI * 2);
          ctx.fill();
        }
      },
      count: dots.length,
    };
  }

  // Drives a field from a GSAP timeline: every seek of the timeline repaints the field at that local time.
  function bindDotField(tl, field, duration) {
    const clock = { t: 0 };
    tl.fromTo(clock, { t: 0 }, { t: duration, duration, ease: "none", onUpdate: () => field.drawAt(clock.t) }, 0);
    field.drawAt(0);
  }

  window.createDotField = createDotField;
  window.bindDotField = bindDotField;
})();
