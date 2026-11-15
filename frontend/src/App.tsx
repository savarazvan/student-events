import { AuthProvider } from './context/AuthContext';
import AppRouter from './routes/AppRouter';
import ThemeWrapper from './theme/ThemeWrapper';

export default function App() {
  return (
    <ThemeWrapper>
      <AuthProvider>
        <AppRouter />
      </AuthProvider>
    </ThemeWrapper>
  );
}
