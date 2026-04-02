import { useCallback, useEffect, useMemo, useState } from "react";
import "@/App.css";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { Toaster, toast } from "sonner";

import AppShell from "@/components/layout/AppShell";
import { ThemeProvider } from "@/components/theme/ThemeProvider";
import { authGet, getStoredToken, loginRequest, logoutRequest, setStoredToken, setSessionExpiredHandler } from "@/lib/api";
import { useIdleTimeout } from "@/hooks/useIdleTimeout";
import AnalyticsPage from "@/pages/AnalyticsPage";
import CrewCapturePage from "@/pages/CrewCapturePage";
import ExportsPage from "@/pages/ExportsPage";
import JobsPage from "@/pages/JobsPage";
import LoginPage from "@/pages/LoginPage";
import OverviewPage from "@/pages/OverviewPage";
import OwnerPage from "@/pages/OwnerPage";
import RapidReviewPage from "@/pages/RapidReviewPage";
import RepeatOffendersPage from "@/pages/RepeatOffendersPage";
import ReviewerPerformancePage from "@/pages/ReviewerPerformancePage";
import ReviewPage from "@/pages/ReviewPage";
import RubricEditorPage from "@/pages/RubricEditorPage";
import SettingsPage from "@/pages/SettingsPage";
import StandardsLibraryPage from "@/pages/StandardsLibraryPage";
import TrainingModePage from "@/pages/TrainingModePage";


function ProtectedRoute({ authState, allowedRoles, onLogout, shell = true, children }) {
  if (authState.loading) {
    return <div className="flex min-h-screen items-center justify-center bg-[#f6f6f2] text-lg font-semibold text-[#243e36]" data-testid="app-loading-state">Loading workspace...</div>;
  }
  if (!authState.user) {
    return <Navigate to="/login" replace />;
  }
  if (allowedRoles && !allowedRoles.includes(authState.user.role)) {
    return <Navigate to="/dashboard" replace />;
  }
  if (!shell) {
    return children;
  }
  return <AppShell user={authState.user} onLogout={onLogout}>{children}</AppShell>;
}


function App() {
  const [authState, setAuthState] = useState({ token: getStoredToken(), user: null, loading: true });

  useEffect(() => {
    const restoreSession = async () => {
      const token = getStoredToken();
      if (!token) {
        setAuthState({ token: null, user: null, loading: false });
        return;
      }

      try {
        setStoredToken(token);
        const user = await authGet("/auth/me");
        setAuthState({ token, user, loading: false });
      } catch {
        logoutRequest();
        setAuthState({ token: null, user: null, loading: false });
      }
    };

    restoreSession();
  }, []);

  const handleLogin = async (email, password) => {
    const result = await loginRequest(email, password);
    setAuthState({ token: result.token, user: result.user, loading: false });
    return result;
  };

  const handleLogout = () => {
    logoutRequest();
    setAuthState({ token: null, user: null, loading: false });
    toast.success("You've been signed out.");
  };

  const handleIdleLogout = useCallback(() => {
    logoutRequest();
    setAuthState({ token: null, user: null, loading: false });
    toast.warning("Session expired due to inactivity. Please sign in again.");
  }, []);

  // 401 interceptor handler
  useEffect(() => {
    setSessionExpiredHandler(() => {
      setAuthState({ token: null, user: null, loading: false });
      toast.warning("Session expired. Please sign in again.");
    });
  }, []);

  // 5-minute idle timeout (only when logged in)
  useIdleTimeout(handleIdleLogout, !!authState.user);

  const pageProps = useMemo(
    () => ({ user: authState.user }),
    [authState.user],
  );

  return (
    <div className="App">
      <ThemeProvider>
        <BrowserRouter>
          <Routes>
            <Route path="/" element={<Navigate to={authState.user ? "/dashboard" : "/login"} replace />} />
            <Route path="/login" element={<LoginPage onLogin={handleLogin} authUser={authState.user} />} />
            <Route path="/crew/:code" element={<CrewCapturePage />} />
            <Route path="/training/:code" element={<TrainingModePage />} />
            <Route path="/dashboard" element={<ProtectedRoute authState={authState} onLogout={handleLogout}><OverviewPage {...pageProps} /></ProtectedRoute>} />
            <Route path="/jobs" element={<ProtectedRoute authState={authState} onLogout={handleLogout} allowedRoles={["management"]}><JobsPage {...pageProps} /></ProtectedRoute>} />
            <Route path="/review" element={<ProtectedRoute authState={authState} onLogout={handleLogout} allowedRoles={["management"]}><ReviewPage {...pageProps} /></ProtectedRoute>} />
            <Route path="/rapid-review" element={<Navigate to="/rapid-review/mobile" replace />} />
            <Route path="/rapid-review/mobile" element={<ProtectedRoute authState={authState} onLogout={handleLogout} allowedRoles={["management", "owner"]} shell={false}><RapidReviewPage {...pageProps} /></ProtectedRoute>} />
            <Route path="/owner" element={<ProtectedRoute authState={authState} onLogout={handleLogout} allowedRoles={["owner"]}><OwnerPage {...pageProps} /></ProtectedRoute>} />
            <Route path="/analytics" element={<ProtectedRoute authState={authState} onLogout={handleLogout} allowedRoles={["owner"]}><AnalyticsPage {...pageProps} /></ProtectedRoute>} />
            <Route path="/standards" element={<ProtectedRoute authState={authState} onLogout={handleLogout}><StandardsLibraryPage {...pageProps} /></ProtectedRoute>} />
            <Route path="/repeat-offenders" element={<ProtectedRoute authState={authState} onLogout={handleLogout}><RepeatOffendersPage {...pageProps} /></ProtectedRoute>} />
            <Route path="/reviewer-performance" element={<ProtectedRoute authState={authState} onLogout={handleLogout} allowedRoles={["owner"]}><ReviewerPerformancePage {...pageProps} /></ProtectedRoute>} />
            <Route path="/exports" element={<ProtectedRoute authState={authState} onLogout={handleLogout} allowedRoles={["owner"]}><ExportsPage {...pageProps} /></ProtectedRoute>} />
            <Route path="/rubric-editor" element={<ProtectedRoute authState={authState} onLogout={handleLogout} allowedRoles={["management", "owner"]}><RubricEditorPage {...pageProps} /></ProtectedRoute>} />
            <Route path="/settings" element={<ProtectedRoute authState={authState} onLogout={handleLogout}><SettingsPage {...pageProps} /></ProtectedRoute>} />
          </Routes>
        </BrowserRouter>
      </ThemeProvider>
      <Toaster richColors position="top-right" />
    </div>
  );
}

export default App;
