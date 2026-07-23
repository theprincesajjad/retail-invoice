import { useEffect, useState } from "react";

/** Compact UI when the usable window height is tight (common laptop fullscreen chrome). */
export function useViewportDensity() {
  const [height, setHeight] = useState(() =>
    typeof window === "undefined" ? 900 : window.innerHeight,
  );
  const [width, setWidth] = useState(() =>
    typeof window === "undefined" ? 1280 : window.innerWidth,
  );

  useEffect(() => {
    const sync = () => {
      setHeight(window.innerHeight);
      setWidth(window.innerWidth);
    };
    sync();
    window.addEventListener("resize", sync);
    return () => window.removeEventListener("resize", sync);
  }, []);

  const compact = height < 820;
  const ultraCompact = height < 700;
  const narrow = width < 1100;

  return { height, width, compact, ultraCompact, narrow };
}
