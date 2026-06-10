import React, { useState, useCallback } from 'react';
import { Box } from 'ink';
import { Banner } from './Banner.js';
import { StatusCheck } from './StatusCheck.js';
import { Shell } from './Shell.js';
import { HealthResponse } from '../api.js';

export const App: React.FC = () => {
  // null  = not yet determined
  // false = diagnostics finished (health can be null if offline)
  const [diagDone, setDiagDone] = useState(false);
  const [health, setHealth] = useState<HealthResponse | null>(null);

  // Stable callback — won't cause StatusCheck useEffect to re-fire
  const handleDiagComplete = useCallback((h: HealthResponse | null) => {
    setHealth(h);
    setDiagDone(true);
  }, []);

  return (
    <Box flexDirection="column">
      {!diagDone ? (
        <Box flexDirection="column">
          <Banner />
          <StatusCheck onComplete={handleDiagComplete} />
        </Box>
      ) : (
        <Shell isOffline={health === null} />
      )}
    </Box>
  );
};
