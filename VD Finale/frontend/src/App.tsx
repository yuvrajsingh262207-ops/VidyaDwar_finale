import { Routes, Route } from "react-router-dom";
import Landing from "@/pages/Landing";
import Auth from "@/pages/Auth";
import { ActionPlanPage, ComparePage, ConflictPage, DocumentsPage, PublicInfoPage, ReadinessPage, SettingsPage, TrackingPage } from "@/pages/Workspace";
import ProfileEditor from "@/pages/ProfileEditor";
import ScholarshipDirectory, { ScholarshipRecordPage } from "@/pages/ScholarshipDirectory";
import StudentDashboard from "@/pages/StudentDashboard";

// One <Route> per page in src/pages; BrowserRouter already wraps this in main.tsx.
export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Landing />} />
      <Route path="/login" element={<Auth mode="login" />} />
      <Route path="/register" element={<Auth mode="register" />} />
      <Route path="/how-it-works" element={<PublicInfoPage kind="how-it-works" />} />
      <Route path="/privacy" element={<PublicInfoPage kind="privacy" />} />
      <Route path="/terms" element={<PublicInfoPage kind="terms" />} />
      <Route path="/dashboard" element={<StudentDashboard />} />
      <Route path="/scholarships" element={<ScholarshipDirectory />} />
      <Route path="/scholarships/:id" element={<ScholarshipRecordPage />} />
      <Route path="/compare" element={<ComparePage />} />
      <Route path="/conflicts" element={<ConflictPage />} />
      <Route path="/conflicts/:id" element={<ConflictPage />} />
      <Route path="/documents" element={<DocumentsPage />} />
      <Route path="/readiness" element={<ReadinessPage />} />
      <Route path="/action-plan" element={<ActionPlanPage />} />
      <Route path="/tracking" element={<TrackingPage />} />
      <Route path="/profile" element={<ProfileEditor />} />
      <Route path="/settings" element={<SettingsPage />} />
    </Routes>
  );
}
