import { useLayoutEffect, useRef, useState } from "react";

// Container width for SVG charts so one viewBox unit is one CSS pixel and
// text stays at a readable size on every screen.
export function useWidth<T extends HTMLElement>(fallback = 360) {
  const ref = useRef<T>(null);
  const [width, setWidth] = useState(fallback);
  useLayoutEffect(() => {
    const el = ref.current;
    if (!el) return;
    const update = () => setWidth(Math.max(240, Math.round(el.getBoundingClientRect().width)));
    update();
    const ro = new ResizeObserver(update);
    ro.observe(el);
    return () => ro.disconnect();
  }, []);
  return [ref, width] as const;
}
