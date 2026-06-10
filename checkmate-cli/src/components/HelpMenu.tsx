import React from 'react';
import { Box, Text } from 'ink';
import { theme } from '../theme.js';

interface CommandHelp {
  command: string;
  alias: string;
  args?: string;
  desc: string;
}

const COMMANDS: CommandHelp[] = [
  { command: '/analyze', alias: '/a', args: '<file_path>',              desc: 'Upload document and run all forensic pipelines' },
  { command: '/view',    alias: '/v', args: '<ela|metadata|seal|nlp>',  desc: 'Dump raw JSON output of a specific engine' },
  { command: '/report',  alias: '/r', args: '<output_path.pdf>',        desc: 'Generate a polished PDF/HTML forensic report' },
  { command: '/reset',   alias: '/rt',                                  desc: 'Clear chat memory and reset conversation history' },
  { command: '/status',  alias: '/s',                                   desc: 'Run backend server health diagnostics' },
  { command: '/clear',   alias: '/c',                                   desc: 'Clear terminal and redraw banner' },
  { command: '/exit',    alias: '/q',                                   desc: 'Exit the CheckMate interactive shell' },
];

export const HelpMenu: React.FC = () => {
  return (
    <Box flexDirection="column" paddingX={2} marginTop={1} marginBottom={1}>
      <Box borderStyle="single" borderColor={theme.colors.gold as any} flexDirection="column" paddingX={2} paddingY={1}>

        {/* Header */}
        <Box marginBottom={1}>
          <Text bold color={theme.colors.gold as any}>-- COMMAND INDEX</Text>
          <Text color="gray">  (tab-completion supported)</Text>
        </Box>

        {/* Command rows — stacked vertical layout for narrow terminal safety */}
        {COMMANDS.map((cmd, idx) => (
          <Box key={idx} flexDirection="column" marginBottom={1}>
            <Box>
              <Text bold color={theme.colors.gold as any}>{cmd.command}</Text>
              <Text color="gray">  {cmd.alias}</Text>
              {cmd.args && <Text color={theme.colors.sage as any}>  {cmd.args}</Text>}
            </Box>
            <Box paddingLeft={4}>
              <Text color="gray">{cmd.desc}</Text>
            </Box>
          </Box>
        ))}

        {/* Hint */}
        <Box marginTop={1} borderStyle="single" borderColor="gray" paddingX={2} paddingY={1}>
          <Text color="gray" italic>
            Any input not starting with{' '}
            <Text bold color={theme.colors.gold as any}>/</Text>
            {' '}is routed to{' '}
            <Text bold color={theme.colors.gold as any}>Gemma</Text>
            {' '}as a natural language prompt. If a document is active, Gemma receives its full forensic context.
          </Text>
        </Box>
      </Box>
    </Box>
  );
};
