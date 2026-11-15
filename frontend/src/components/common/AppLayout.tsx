import Box from '@mui/material/Box';
import Container from '@mui/material/Container';
import { Outlet } from 'react-router';

import Navbar from './Navbar';

export default function AppLayout() {
  return (
    <Box sx={{ minHeight: '100vh', display: 'flex', flexDirection: 'column' }}>
      <Navbar />
      <Container maxWidth="lg" sx={{ py: 3, flex: 1 }}>
        <Outlet />
      </Container>
    </Box>
  );
}
