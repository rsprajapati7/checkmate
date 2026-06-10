import React, { useState } from 'react';
import { Box, Text, useInput, useApp } from 'ink';
import TextInput from 'ink-text-input';
import fs from 'fs';
import path from 'path';
import { Banner } from './Banner.js';
import { HelpMenu } from './HelpMenu.js';
import { StatusCheck } from './StatusCheck.js';
import { PipelineProgress } from './PipelineProgress.js';
import { DiagnosticTable } from './DiagnosticTable.js';
import { ChatPanel } from './ChatPanel.js';
import { scanDocument, chatWithGemma, generateReport, ScanResponse } from '../api.js';
import { theme } from '../theme.js';
import { SYM } from '../utils.js';

// ── Types ──────────────────────────────────────────────────────────────────

interface TextLog {
  id: string;
  type: 'text';
  content: string;       // plain text, NO chalk pre-applied
  style?: 'normal' | 'success' | 'warn' | 'muted';
}
interface ErrorLog  { id: string; type: 'error';  content: string; }
interface BannerLog { id: string; type: 'banner'; }
interface HelpLog   { id: string; type: 'help'; }
interface StatusLog { id: string; type: 'status'; }
interface ScanLog   { id: string; type: 'scan';  filePath: string; isApiDone: boolean; results?: ScanResponse; }
interface TableLog  { id: string; type: 'table'; results: ScanResponse; }
interface ChatLog   { id: string; type: 'chat';  messages: { role: 'user' | 'assistant'; content: string }[]; }

type LogItem = TextLog | ErrorLog | BannerLog | HelpLog | StatusLog | ScanLog | TableLog | ChatLog;

interface ShellProps {
  isOffline?: boolean;
}

// ── Component ──────────────────────────────────────────────────────────────

export const Shell: React.FC<ShellProps> = ({ isOffline = false }) => {
  const { exit } = useApp();
  const [inputValue, setInputValue] = useState('');
  const [activeDoc, setActiveDoc]   = useState<ScanResponse | null>(null);
  const [chatHistory, setChatHistory] = useState<{ role: 'user' | 'assistant'; content: string }[]>([]);
  const [isGeneratingChat, setIsGeneratingChat] = useState(false);
  const [cmdHistory, setCmdHistory]   = useState<string[]>([]);
  const [cmdHistoryIdx, setCmdHistoryIdx] = useState(-1);

  const [logs, setLogs] = useState<LogItem[]>([
    { id: 'banner-init', type: 'banner' },
    { id: 'help-init',   type: 'help' },
    ...(isOffline ? [{
      id: 'offline-warn',
      type: 'text' as const,
      content: 'Running in offline mode — backend unavailable. Scan and chat commands are disabled.',
      style: 'warn' as const,
    }] : []),
  ]);

  // ── Key handling ────────────────────────────────────────────────────────

  const isScanRunning = logs.some((item) => item.type === 'scan' && !(item as ScanLog).isApiDone);
  const isBusy        = isGeneratingChat || isScanRunning;

  useInput((input, key) => {
    // Block all input when busy except Ctrl+C
    if (isBusy) return;

    if (key.upArrow && cmdHistory.length > 0) {
      const newIdx = cmdHistoryIdx === -1 ? cmdHistory.length - 1 : Math.max(0, cmdHistoryIdx - 1);
      setCmdHistoryIdx(newIdx);
      setInputValue(cmdHistory[newIdx]);
    }

    if (key.downArrow && cmdHistoryIdx !== -1) {
      const newIdx = cmdHistoryIdx + 1;
      if (newIdx >= cmdHistory.length) {
        setCmdHistoryIdx(-1);
        setInputValue('');
      } else {
        setCmdHistoryIdx(newIdx);
        setInputValue(cmdHistory[newIdx]);
      }
    }

    if (key.tab) {
      const slashCommands = ['/analyze', '/view', '/report', '/reset', '/status', '/clear', '/exit'];
      const matching = slashCommands.filter((c) => c.startsWith(inputValue));
      if (matching.length === 1) setInputValue(matching[0] + ' ');
    }
  });

  // ── Log helpers ──────────────────────────────────────────────────────────

  const makeId = (type: string) =>
    `${type}-${Date.now()}-${Math.random().toString(36).substr(2, 5)}`;

  const appendLog = (log: Omit<TextLog, 'id'> | Omit<ErrorLog, 'id'> | Omit<BannerLog, 'id'> | Omit<HelpLog, 'id'> | Omit<StatusLog, 'id'> | Omit<ScanLog, 'id'> | Omit<TableLog, 'id'> | Omit<ChatLog, 'id'>): string => {
    const id = makeId(log.type);
    setLogs((prev) => [...prev, { ...log, id } as LogItem]);
    return id;
  };

  // ── Command router ───────────────────────────────────────────────────────

  const handleSubmit = async (input: string) => {
    const trimmed = input.trim();
    if (!trimmed) return;

    setInputValue('');
    setCmdHistory((prev) => [...prev, trimmed]);
    setCmdHistoryIdx(-1);

    if (trimmed.startsWith('/')) {
      const parts = trimmed.split(/\s+/);
      const cmd   = parts[0].toLowerCase();
      const arg   = parts.slice(1).join(' ').trim();

      switch (cmd) {
        // ── Exit ──────────────────────────────────────────────
        case '/exit':
        case '/quit':
        case '/q':
        case '/e':
          appendLog({ type: 'text', content: 'Closing CheckMate session. Goodbye.', style: 'muted' });
          setTimeout(() => exit(), 400);
          break;

        // ── Clear ─────────────────────────────────────────────
        case '/clear':
        case '/c':
          setLogs([{ id: makeId('banner'), type: 'banner' }]);
          break;

        // ── Help ──────────────────────────────────────────────
        case '/help':
        case '/h':
          appendLog({ type: 'help' });
          break;

        // ── Status ────────────────────────────────────────────
        case '/status':
        case '/s':
          appendLog({ type: 'status' });
          break;

        // ── Reset chat history ────────────────────────────────
        case '/reset':
        case '/rt':
          setChatHistory([]);
          appendLog({ type: 'text', content: 'Chat memory cleared.', style: 'success' });
          break;

        // ── Analyze ───────────────────────────────────────────
        case '/analyze':
        case '/a': {
          if (isOffline) {
            appendLog({ type: 'error', content: 'Backend unavailable. Start the server and restart the CLI.' });
            break;
          }
          if (!arg) {
            appendLog({ type: 'error', content: 'Usage: /analyze <file_path>' });
            break;
          }
          const fullPath = path.resolve(arg);
          if (!fs.existsSync(fullPath)) {
            appendLog({ type: 'error', content: `File not found: "${fullPath}"` });
            break;
          }

          const scanId = makeId('scan');
          setLogs((prev) => [
            ...prev,
            { id: scanId, type: 'scan', filePath: path.basename(fullPath), isApiDone: false },
          ]);

          try {
            const results = await scanDocument(fullPath);
            setActiveDoc(results);
            setLogs((prev) =>
              prev.map((item) =>
                item.id === scanId ? { ...item, isApiDone: true, results } : item
              )
            );
          } catch (err: any) {
            setLogs((prev) =>
              prev.map((item) =>
                item.id === scanId
                  ? { id: scanId, type: 'error', content: `Scan failed: ${err.message}` }
                  : item
              )
            );
          }
          break;
        }

        // ── View engine JSON ──────────────────────────────────
        case '/view':
        case '/v': {
          if (!activeDoc) {
            appendLog({ type: 'error', content: 'No active document. Run /analyze <path> first.' });
            break;
          }
          const validEngines = ['ela', 'metadata', 'meta', 'seal', 'nlp'];
          const engine = arg.toLowerCase();
          if (!validEngines.includes(engine)) {
            appendLog({ type: 'error', content: 'Usage: /view <ela | metadata | seal | nlp>' });
            break;
          }
          const key = engine === 'meta' ? 'metadata' : engine;
          const engineData = activeDoc.pipelines[key as keyof typeof activeDoc.pipelines];
          if (!engineData) {
            appendLog({ type: 'error', content: `No results found for engine: ${engine}` });
            break;
          }
          appendLog({
            type: 'text',
            content: `[Raw Engine Output: ${engine.toUpperCase()}]\n${JSON.stringify(engineData, null, 2)}`,
            style: 'muted',
          });
          break;
        }

        // ── Report ────────────────────────────────────────────
        case '/report':
        case '/r': {
          if (isOffline) {
            appendLog({ type: 'error', content: 'Backend unavailable. Cannot generate report.' });
            break;
          }
          if (!activeDoc) {
            appendLog({ type: 'error', content: 'No active document. Run /analyze <path> first.' });
            break;
          }
          if (!arg) {
            appendLog({ type: 'error', content: 'Usage: /report <output_path.pdf|output_path.html>' });
            break;
          }

          appendLog({ type: 'text', content: 'Requesting report from backend...', style: 'muted' });

          try {
            const { data, isPdf } = await generateReport(activeDoc);
            let finalPath = path.resolve(arg);
            if (isPdf && !finalPath.endsWith('.pdf'))   finalPath += '.pdf';
            if (!isPdf && !finalPath.endsWith('.html')) finalPath += '.html';
            fs.writeFileSync(finalPath, data);
            appendLog({
              type: 'text',
              content: `Report saved: ${finalPath} (${isPdf ? 'PDF' : 'HTML'})`,
              style: 'success',
            });
          } catch (err: any) {
            appendLog({ type: 'error', content: `Report failed: ${err.message}` });
          }
          break;
        }

        default:
          appendLog({ type: 'error', content: `Unknown command: "${trimmed}". Type /help for the command index.` });
      }
    } else {
      // ── Natural language → Gemma ───────────────────────────
      if (isOffline) {
        appendLog({ type: 'error', content: 'Backend unavailable. Cannot reach Gemma.' });
        return;
      }

      appendLog({ type: 'text', content: `You: ${trimmed}`, style: 'normal' });
      setIsGeneratingChat(true);

      const updatedHistory = [...chatHistory, { role: 'user' as const, content: trimmed }];
      setChatHistory(updatedHistory);

      let accumulated = '';
      const logId = appendLog({
        type: 'chat',
        messages: [...updatedHistory, { role: 'assistant', content: '' }],
      });

      try {
        await chatWithGemma(trimmed, activeDoc, updatedHistory, (chunk) => {
          accumulated += chunk;
          setLogs((prev) =>
            prev.map((item) =>
              item.id === logId
                ? {
                    ...item,
                    messages: [
                      ...updatedHistory,
                      { role: 'assistant', content: accumulated },
                    ],
                  }
                : item
            )
          );
        });
        setChatHistory((prev) => [...prev, { role: 'assistant', content: accumulated }]);
      } catch (err: any) {
        setLogs((prev) =>
          prev.map((item) =>
            item.id === logId
              ? { id: logId, type: 'error', content: `Gemma error: ${err.message}` }
              : item
          )
        );
      } finally {
        setIsGeneratingChat(false);
      }
    }
  };

  const handleScanComplete = (logId: string, results: ScanResponse) => {
    setLogs((prev) =>
      prev.map((item) =>
        item.id === logId ? ({ id: logId, type: 'table', results } as TableLog) : item
      )
    );
  };

  // ── Prompt label ─────────────────────────────────────────────────────────

  const promptLabel = activeDoc
    ? `CheckMate [${path.basename(activeDoc.filename)}] >> `
    : 'CheckMate >> ';

  const promptLabelColor = activeDoc ? theme.colors.coral : theme.colors.gold;

  // ── Render ────────────────────────────────────────────────────────────────

  return (
    <Box flexDirection="column" paddingBottom={1}>
      {/* Output scroll */}
      {logs.map((item) => {
        if (item.type === 'banner') {
          return <Banner key={item.id} />;
        }
        if (item.type === 'help') {
          return <HelpMenu key={item.id} />;
        }
        if (item.type === 'status') {
          return <StatusCheck key={item.id} onComplete={() => {}} />;
        }
        if (item.type === 'scan') {
          const scanItem = item as ScanLog;
          return (
            <PipelineProgress
              key={item.id}
              isApiDone={scanItem.isApiDone}
              onComplete={() => handleScanComplete(item.id, scanItem.results!)}
            />
          );
        }
        if (item.type === 'table') {
          return <DiagnosticTable key={item.id} results={(item as TableLog).results} />;
        }
        if (item.type === 'chat') {
          const chatItem = item as ChatLog;
          const assistantTurn = chatItem.messages[chatItem.messages.length - 1];
          // isGenerating only applies to the very last chat log (the live one)
          const isLiveItem = item.id === logs[logs.length - 1]?.id || 
            logs.slice(logs.indexOf(item) + 1).every(l => l.type !== 'chat');
          return (
            <ChatPanel
              key={item.id}
              messages={[assistantTurn]}
              isGenerating={isGeneratingChat && isLiveItem}
            />
          );
        }
        if (item.type === 'error') {
          return (
            <Box key={item.id} paddingX={2} marginTop={1}>
              <Text bold color={theme.colors.crimson as any}>{SYM.CROSS} </Text>
              <Text color={theme.colors.crimson as any}>{(item as ErrorLog).content}</Text>
            </Box>
          );
        }
        if (item.type === 'text') {
          const textItem = item as TextLog;
          const color =
            textItem.style === 'success' ? theme.colors.sage    :
            textItem.style === 'warn'    ? theme.colors.coral   :
            textItem.style === 'muted'   ? theme.colors.slate   :
            'white';
          return (
            <Box key={item.id} paddingX={2} marginTop={1}>
              <Text color={color as any}>{textItem.content}</Text>
            </Box>
          );
        }
        return null;
      })}

      {/* Generating indicator rendered inside the live chat log item above */}

      {/* ── Command prompt — ALWAYS visible ─────────────────── */}
      <Box paddingX={2} marginTop={1}>
        {isBusy ? (
          /* Show a disabled/waiting prompt when busy so the user always sees it */
          <Box>
            <Text bold color={promptLabelColor as any}>{promptLabel}</Text>
            <Text color="gray" italic>
              {isScanRunning ? 'scanning...' : 'generating...'}
            </Text>
          </Box>
        ) : (
          <Box>
            <Text bold color={promptLabelColor as any}>{promptLabel}</Text>
            <TextInput
              value={inputValue}
              onChange={setInputValue}
              onSubmit={handleSubmit}
            />
          </Box>
        )}
      </Box>
    </Box>
  );
};
