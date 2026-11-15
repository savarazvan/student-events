import { BrowserRouter, Route, Routes } from 'react-router';

import AppLayout from '../components/common/AppLayout';
import ProtectedRoute from '../components/common/ProtectedRoute';
import AdminPage from '../pages/AdminPage';
import EventCreatePage from '../pages/EventCreatePage';
import EventDetailPage from '../pages/EventDetailPage';
import EventEditPage from '../pages/EventEditPage';
import EventListPage from '../pages/EventListPage';
import HomePage from '../pages/HomePage';
import LoginPage from '../pages/LoginPage';
import MySchedulePage from '../pages/MySchedulePage';
import RegisterPage from '../pages/RegisterPage';
import TicketPage from '../pages/TicketPage';

export default function AppRouter() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<AppLayout />}>
          {/* Public routes */}
          <Route path="/" element={<HomePage />} />
          <Route path="/login" element={<LoginPage />} />
          <Route path="/register" element={<RegisterPage />} />
          <Route path="/events" element={<EventListPage />} />
          <Route path="/events/:eventId" element={<EventDetailPage />} />

          {/* Authenticated routes */}
          <Route element={<ProtectedRoute />}>
            <Route path="/my-schedule" element={<MySchedulePage />} />
            <Route path="/tickets/:ticketId" element={<TicketPage />} />
            <Route path="/events/new" element={<EventCreatePage />} />
            <Route path="/events/:eventId/edit" element={<EventEditPage />} />
          </Route>

          {/* Super Admin routes */}
          <Route element={<ProtectedRoute requiredRole="SUPER_ADMIN" />}>
            <Route path="/admin" element={<AdminPage />} />
          </Route>
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
