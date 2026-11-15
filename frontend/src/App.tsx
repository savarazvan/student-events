import { AuthProvider } from './context/AuthContext';
import { NotificationsProvider } from './context/NotificationsContext';
import AppRouter from './routes/AppRouter';
import ThemeWrapper from './theme/ThemeWrapper';

export default function App() {
  return (
    <ThemeWrapper>
      <AuthProvider>
        <NotificationsProvider>
          <AppRouter />
        </NotificationsProvider>
      </AuthProvider>
    </ThemeWrapper>
  );
}
