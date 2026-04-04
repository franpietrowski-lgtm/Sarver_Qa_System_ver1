import { createContext, useContext, useEffect, useMemo, useState } from "react";


const ThemeContext = createContext(null);
const THEME_STORAGE_KEY = "field-quality-workspace-theme";
const FONT_STORAGE_KEY = "field-quality-workspace-font";

export const THEMES = [
  { id: "default", label: "Default", description: "Nature green light mode" },
  { id: "dark", label: "Dark", description: "Deep forest dark mode" },
  { id: "tomboy", label: "Tomboy", description: "Slate navy + hot pink" },
  { id: "gold", label: "Gold", description: "Black & gold luxury" },
  { id: "noir", label: "Noir", description: "Dark charcoal + crimson" },
  { id: "neon", label: "Neon", description: "Deep green + lime glow" },
  { id: "breakfast", label: "Breakfast", description: "Warm waffle + maple honey" },
  { id: "cafe", label: "Cafe", description: "Coffee + matcha + caramel" },
];

const THEME_SWATCHES = {
  default: ["#f6f6f2", "#243e36", "#edf0e7", "#5f7464"],
  dark: ["#0d120e", "#1a211b", "#243e36", "#a3b39e"],
  tomboy: ["#192731", "#2a3843", "#ff096c", "#4f6172"],
  gold: ["#19171b", "#2f2921", "#9e8123", "#563a17"],
  noir: ["#252B2B", "#380F17", "#DC2011", "#EFDFC5"],
  neon: ["#032820", "#08652C", "#80A416", "#C5C764"],
  breakfast: ["#382615", "#4a3520", "#F4C07D", "#B78F64"],
  cafe: ["#3F1D0E", "#4a2816", "#ABBF9B", "#A2663C"],
};

export { THEME_SWATCHES };

export const FONT_PACKAGES = [
  { id: "brand", label: "Brand", description: "Cabinet Grotesk + Manrope", sample: "Cabinet Grotesk", family: "'Cabinet Grotesk', sans-serif" },
  { id: "duckfake", label: "Duckfake", description: "Grungy hand-painted", sample: "Permanent Marker", family: "'Permanent Marker', cursive" },
  { id: "kindergarten", label: "Kid-Ergarten", description: "Childlike handwriting", sample: "Patrick Hand", family: "'Patrick Hand', cursive" },
  { id: "hikaru", label: "Hikaru", description: "Chunky cute rounded", sample: "Fredoka", family: "'Fredoka', sans-serif" },
];


export function ThemeProvider({ children }) {
  const [theme, setTheme] = useState(() => {
    const stored = localStorage.getItem(THEME_STORAGE_KEY) || "default";
    if (THEMES.some((t) => t.id === stored)) return stored;
    return "default";
  });

  const [fontPkg, setFontPkg] = useState(() => {
    const stored = localStorage.getItem(FONT_STORAGE_KEY) || "brand";
    if (FONT_PACKAGES.some((f) => f.id === stored)) return stored;
    return "brand";
  });

  useEffect(() => {
    localStorage.setItem(THEME_STORAGE_KEY, theme);
  }, [theme]);

  useEffect(() => {
    localStorage.setItem(FONT_STORAGE_KEY, fontPkg);
  }, [fontPkg]);

  const value = useMemo(
    () => ({
      theme,
      setTheme,
      isDark: theme !== "default",
      fontPkg,
      setFontPkg,
    }),
    [theme, fontPkg],
  );

  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>;
}


export function useTheme() {
  const context = useContext(ThemeContext);
  if (!context) {
    throw new Error("useTheme must be used inside ThemeProvider");
  }
  return context;
}
