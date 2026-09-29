// Theme storage key and the pre-paint script (app/layout.tsx). A plain module, so the server layout gets the
// string itself; components/theme-toggle.tsx is the client side.
export const THEME_KEY = "edgememory-theme";

/** Runs before first paint, so the page never flashes the wrong theme. */
export const THEME_SCRIPT = `(function(){try{var c=localStorage.getItem("${THEME_KEY}");var d=c==="dark"||(c!=="light"&&matchMedia("(prefers-color-scheme: dark)").matches);document.documentElement.dataset.theme=d?"dark":"light";}catch(e){}})();`;
