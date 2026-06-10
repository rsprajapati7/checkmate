import React from 'react';
import { Box, Text } from 'ink';
import { marked } from 'marked';
import TerminalRenderer from 'marked-terminal';
import { theme } from '../theme.js';

// Setup marked terminal renderer once at module level
marked.setOptions({
  renderer: new TerminalRenderer({
    code:         theme.gold,
    blockquote:   theme.coral.italic,
    html:         theme.sand,
    heading:      theme.boldGold,
    firstHeading: theme.boldGold,
    strong:       theme.boldSand,
    em:           theme.sand.italic,
    codespan:     theme.coral,
    link:         theme.sage.underline,
    href:         theme.sage.underline,
  }),
});

interface ChatTurn {
  role: 'user' | 'assistant';
  content: string;
}

interface ChatPanelProps {
  messages: ChatTurn[];
  isGenerating: boolean;
}

function renderMarkdown(text: string): string {
  if (!text.trim()) return '';
  try {
    return marked(text).toString().trim();
  } catch {
    return text;
  }
}

export const ChatPanel: React.FC<ChatPanelProps> = ({ messages, isGenerating }) => {
  return (
    <Box flexDirection="column" paddingX={2} marginTop={1} marginBottom={1}>
      {messages.map((msg, idx) => {
        if (msg.role !== 'assistant') return null;

        const isLast     = idx === messages.length - 1;
        const isStreaming = isGenerating && isLast;
        const hasContent  = msg.content.trim().length > 0;

        return (
          <Box
            key={idx}
            flexDirection="column"
            borderStyle="single"
            borderColor={theme.colors.sage as any}
            paddingX={2}
            paddingY={1}
            marginBottom={1}
          >
            <Box marginBottom={1}>
              <Text bold color={theme.colors.gold as any}>-- Gemma Assistant</Text>
              {isStreaming && (
                <Text color="gray" dimColor> generating...</Text>
              )}
            </Box>

            {hasContent ? (
              isStreaming ? (
                <Text color="white">
                  {msg.content}
                  <Text color={theme.colors.sage as any}>{'▌'}</Text>
                </Text>
              ) : (
                <Text>{renderMarkdown(msg.content)}</Text>
              )
            ) : (
              <Text italic color="gray">Thinking...</Text>
            )}
          </Box>
        );
      })}

      {/* Standalone waiting box — before any chat log item exists */}
      {isGenerating && messages.length === 0 && (
        <Box
          borderStyle="single"
          borderColor={theme.colors.sage as any}
          paddingX={2}
          paddingY={1}
          marginBottom={1}
        >
          <Text bold color={theme.colors.gold as any}>-- Gemma Assistant  </Text>
          <Text italic color="gray">Thinking...</Text>
        </Box>
      )}
    </Box>
  );
};
