import React, { memo } from 'react';
import { Box, Text } from 'ink';
import gradient from 'gradient-string';

// Clean ANSI-safe banner — tested to render correctly in 80-col terminals.
// Uses simple block-letter style instead of complex serif strokes.
const BANNER_ART = [
  '   _____ _               _   __  __       _       ',
  '  / ____| |             | | |  \\/  |     | |      ',
  ' | |    | |__   ___  ___| | | \\  / | __ _| |_ ___ ',
  " | |    | '_ \\ / _ \\/ __| | | |\\/| |/ _` | __/ _ \\",
  ' | |____| | | |  __/ (__| | | |  | | (_| | ||  __/',
  '  \\_____|_| |_|\\___|\\___|_| |_|  |_|\\__,_|\\__\\___|',
].join('\n');

const goldToCoral = gradient(['#D4AF37', '#D1855C']);

export const Banner: React.FC = memo(() => {
  return (
    <Box flexDirection="column" marginBottom={1} paddingLeft={2}>
      <Text>{goldToCoral(BANNER_ART)}</Text>
      <Box paddingLeft={1} marginTop={1}>
        <Text color="gray">{'─'.repeat(4)} </Text>
        <Text bold color="white">CheckMate / Suraksha 2.0 </Text>
        <Text color="gray">{'─'.repeat(2)} </Text>
        <Text italic color="yellow">AI Document Forensic Toolkit</Text>
        <Text color="gray"> {'─'.repeat(4)}</Text>
      </Box>
    </Box>
  );
});

Banner.displayName = 'Banner';
