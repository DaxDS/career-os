import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { AuthProvider } from "./context/AuthContext";
import { ProtectedRoute } from "./components/AppShell";
import { LandingPage } from "./pages/Landing";
import { LoginPage } from "./pages/Login";
import { RegisterPage } from "./pages/Register";
import { DashboardPage } from "./pages/Dashboard";
import { ResumesPage } from "./pages/Resumes";
import { JobsPage } from "./pages/Jobs";
import { ReviewPage } from "./pages/Review";
import { LinkedInPage } from "./pages/LinkedIn";
import { InterviewPrepPage } from "./pages/InterviewPrep";
import { PipelinePage } from "./pages/Pipeline";
import { ApplicationsPage } from "./pages/Applications";
import { PlanPage } from "./pages/Plan";
import { PricingPage, PublicPricingPage } from "./pages/Pricing";

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<LandingPage />} />
          <Route path="/login" element={<LoginPage />} />
          <Route path="/register" element={<RegisterPage />} />
          <Route path="/pricing" element={<PublicPricingPage />} />
          <Route path="/app" element={<ProtectedRoute />}>
            <Route index element={<DashboardPage />} />
            <Route path="resumes" element={<ResumesPage />} />
            <Route path="jobs" element={<JobsPage />} />
            <Route path="review" element={<ReviewPage />} />
            <Route path="linkedin" element={<LinkedInPage />} />
            <Route path="apply" element={<ApplicationsPage />} />
            <Route path="interview" element={<InterviewPrepPage />} />
            <Route path="pipeline" element={<PipelinePage />} />
            <Route path="plan" element={<PlanPage />} />
            <Route path="pricing" element={<PricingPage />} />
          </Route>
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
}
