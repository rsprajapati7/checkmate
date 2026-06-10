import React, { useEffect, useCallback } from 'react';
import { Box, Text, useInput } from 'ink';
import { healthCheck, startServer, HealthResponse, API_URL } from '../api.js';
import { theme } from '../theme.js';
import { useSpinner, SYM } from '../utils.js';

interface StatusCheckProps {
  onComplete: (health: HealthResponse | null) => void;
}

type Status = 'checking' | 'starting' | 'error' | 'ready';

export const StatusCheck: React.FC<StatusCheckProps> = ({ onComplete }) => {
  const [status, setStatus] = React.useState<Status>('checking');
  const [logMessage, setLogMessage] = React.useState('Connecting to CheckMate backend...');
  const [health, setHealth] = React.useState<HealthResponse | null>(null);
  const [skipped, setSkipped] = React.useState(false);

  const isAnimating = status === 'checking' || status === 'starting';
  const spinner = useSpinner(isAnimating);

  // Allow user to skip server startup and enter offline/limited shell
  useInput((input, key) => {
    if ((key.escape || input === 's') && (status === 'starting' || status === 'error')) {
      setSkipped(true);
      onComplete(null);
    }
  });

  const runDiagnostics = useCallback(async () => {
    let isMounted = true;

    async function run() {
      try {
        const isLocal = API_URL.includes('localhost') || API_URL.includes('127.0.0.1');
        let currentHealth = await healthCheck();

        if (!currentHealth) {
          if (!isMounted) return;

          if (isLocal) {
            setStatus('starting');
            const started = await startServer((msg) => {
              if (isMounted) setLogMessage(msg);
            });

            if (started) {
              currentHealth = await healthCheck();
            }
          } else {
            // For remote backend, try connecting a few times with status messages
            for (let i = 1; i <= 3; i++) {
              if (!isMounted) return;
              setLogMessage(`Connecting to remote backend... (Attempt ${i}/3)`);
              await new Promise((resolve) => setTimeout(resolve, 1500));
              currentHealth = await healthCheck();
              if (currentHealth) break;
            }
          }
        }

        if (!isMounted) return;

        if (currentHealth) {
          setHealth(currentHealth);
          setStatus('ready');
          // Brief pause to show the ready state before launching shell
          setTimeout(() => {
            if (isMounted) onComplete(currentHealth!);
          }, 1200);
        } else {
          setStatus('error');
        }
      } catch (err: any) {
        if (isMounted) {
          setLogMessage(`Diagnostics error: ${err.message}`);
          setStatus('error');
        }
      }
    }

    run();
    return () => { isMounted = false; };
  }, [onComplete]);


  useEffect(() => {
    let mounted = true;
    let cleanupFn: (() => void) | undefined;

    runDiagnostics().then((fn) => {
      if (mounted) cleanupFn = fn;
    });

    return () => {
      mounted = false;
      cleanupFn?.();
    };
  }, [runDiagnostics]);

  return (
    <Box flexDirection="column" paddingX={2} marginBottom={1}>
      {/* Section header */}
      <Box marginBottom={1}>
        <Text bold color={theme.colors.gold as any}>-- SYSTEM DIAGNOSTICS</Text>
        <Text color="gray"> ────────────────────────</Text>
      </Box>

      {status === 'checking' && (
        <Box flexDirection="column">
          <Box>
            <Text color="yellow">{spinner} </Text>
            <Text color="gray">
              {API_URL.includes('localhost') || API_URL.includes('127.0.0.1')
                ? 'Verifying local FastAPI backend status...'
                : `Verifying remote CheckMate backend status at ${API_URL}...`}
            </Text>
          </Box>
          {!(API_URL.includes('localhost') || API_URL.includes('127.0.0.1')) && logMessage !== 'Connecting to CheckMate backend...' && (
            <Box marginTop={1} paddingLeft={2}>
              <Text color="yellow">{logMessage}</Text>
            </Box>
          )}
        </Box>
      )}


      {status === 'starting' && (
        <Box flexDirection="column">
          <Box>
            <Text color="yellow">{spinner} </Text>
            <Text color="yellow">{logMessage}</Text>
          </Box>
          <Box marginTop={1} paddingLeft={2}>
            <Text color="gray" italic>
              Press <Text bold color="white">S</Text> or <Text bold color="white">Esc</Text> to skip and enter offline shell.
            </Text>
          </Box>
        </Box>
      )}

      {status === 'error' && (
        <Box flexDirection="column">
          <Box>
            <Text bold color={theme.colors.crimson as any}>{SYM.CROSS} Connection Failed</Text>
          </Box>
          <Box marginTop={1} paddingLeft={2} flexDirection="column">
            <Text color="gray">Could not reach FastAPI server at {API_URL}.</Text>
            {API_URL.includes('localhost') || API_URL.includes('127.0.0.1') ? (
              <Text color="gray">
                Run manually:{' '}
                <Text bold color={theme.colors.gold as any}>uvicorn backend.main:app --reload</Text>
              </Text>
            ) : (
              <Text color="gray">
                Please verify your network connection and ensure your Railway deployment is active.
              </Text>
            )}
          </Box>
          <Box marginTop={1} paddingLeft={2}>
            <Text color="gray" italic>
              Press <Text bold color="white">S</Text> or <Text bold color="white">Esc</Text> to continue in offline mode.
            </Text>
          </Box>
        </Box>
      )}


      {status === 'ready' && health && (
        <Box flexDirection="column">
          <Box>
            <Text bold color={theme.colors.sage as any}>{SYM.CHECK}</Text>
            <Text bold color={theme.colors.sage as any}> Backend Server: </Text>
            <Text color="white">{health.version}</Text>
          </Box>
          <Box>
            <Text bold color={health.db === 'connected' ? theme.colors.sage : theme.colors.crimson as any}>
              {health.db === 'connected' ? SYM.CHECK : SYM.CROSS}
            </Text>
            <Text bold color={health.db === 'connected' ? theme.colors.sage : theme.colors.crimson as any}> Database: </Text>
            <Text color="white">{health.db}</Text>
          </Box>
          <Box>
            <Text bold color={health.llm.includes('ok') ? theme.colors.sage : theme.colors.coral as any}>
              {health.llm.includes('ok') ? SYM.CHECK : SYM.WARN}
            </Text>
            <Text bold color={health.llm.includes('ok') ? theme.colors.sage : theme.colors.coral as any}> Gemma LLM: </Text>
            <Text color="white">{health.llm}</Text>
          </Box>
          <Box marginTop={1}>
            <Text color={theme.colors.sage as any}>All checks passed — launching shell...</Text>
          </Box>
        </Box>
      )}
    </Box>
  );
};
