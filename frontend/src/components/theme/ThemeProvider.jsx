import { createContext, useContext, useEffect, useMemo, useState } from "react";


const ThemeContext = createContext(null);
const STORAGE_KEY = "field-quality-workspace-theme";

export const THEMES = [
  { id: "default", label: "Default", description: "Nature green light mode" },
  { id: "dark", label: "Dark", description: "Deep forest dark mode" },
  { id: "tomboy", label: "Tomboy", description: "Slate navy + hot pink" },
  { id: "gold", label: "Gold", description: "Black & gold luxury" },
  { id: "noir", label: "Noir", description: "Dark charcoal + crimson" },
  { id: "neon", label: "Neon", description: "Deep green + lime glow" },
];

const THEME_SWATCHES = {
  default: ["#f6f6f2", "#243e36", "#edf0e7", "#5f7464"],
  dark: ["#0d120e", "#1a211b", "#243e36", "#a3b39e"],
  tomboy: ["#192731", "#2a3843", "#ff096c", "#4f6172"],
  gold: ["#19171b", "#2f2921", "#9e8123", "#563a17"],
  noir: ["#252B2B", "#380F17", "#DC2011", "#EFDFC5"],
  neon: ["#032820", "#08652C", "#80A416", "#C5C764"],
};

export { THEME_SWATCHES };


export function ThemeProvider({ children }) {
  const [theme, setTheme] = useState(() => {
    const stored = localStorage.getItem(STORAGE_KEY) || "default";
    if (THEMES.some((t) => t.id === stored)) return stored;
    return "default";
  });

  useEffect(() => {
    localStorage.setItem(STORAGE_KEY, theme);
  }, [theme]);

  const value = useMemo(
    () => ({
      theme,
      setTheme,
      isDark: theme !== "default",
    }),
    [theme],
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
