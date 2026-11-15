import { useNavigate } from 'react-router';

import Box from '@mui/material/Box';
import Button from '@mui/material/Button';
import Typography from '@mui/material/Typography';
import EventIcon from '@mui/icons-material/Event';

export default function HomePage() {
  const navigate = useNavigate();

  return (
    <Box
      display="flex"
      flexDirection="column"
      alignItems="center"
      justifyContent="center"
      minHeight="60vh"
      textAlign="center"
    >
      <EventIcon sx={{ fontSize: 80, color: 'primary.main', mb: 2 }} />
      <Typography variant="h3" gutterBottom>
        UBB Student Events
      </Typography>
      <Typography variant="h6" color="text.secondary" paragraph>
        Discover, register, and attend student organization events.
      </Typography>
      <Button
        variant="contained"
        size="large"
        onClick={() => navigate('/events')}
      >
        Browse Events
      </Button>
    </Box>
  );
}
