import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';

interface Props {
  message?: string;
}

export default function EmptyState({ message = 'Nothing to show.' }: Props) {
  return (
    <Box textAlign="center" py={6}>
      <Typography variant="h6" color="text.secondary">
        {message}
      </Typography>
    </Box>
  );
}
