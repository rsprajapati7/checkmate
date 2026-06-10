import React from 'react';
import { Box, Text } from 'ink';
import { ScanResponse, PipelineResult } from '../api.js';
import { theme } from '../theme.js';
import { buildBar } from '../utils.js';

interface DiagnosticTableProps {
  results: ScanResponse;
}

export const DiagnosticTable: React.FC<DiagnosticTableProps> = ({ results }) => {
  const { filename, file_type, page_count, is_scanned, risk_tier, final_score, pipelines, pdf_metadata, qr_codes } = results;

  // Risk tier colors
  let tierColor = theme.colors.sage;
  let tierLabel = 'LOW RISK';

  if (risk_tier === 'RED' || risk_tier === 'HIGH') {
    tierColor = theme.colors.crimson;
    tierLabel = 'CRITICAL RISK';
  } else if (risk_tier === 'ORANGE' || risk_tier === 'MEDIUM') {
    tierColor = theme.colors.coral;
    tierLabel = 'SUSPICIOUS';
  } else if (risk_tier === 'GREEN' || risk_tier === 'LOW') {
    tierColor = theme.colors.sage;
    tierLabel = 'VERIFIED SAFE';
  }

  // Score bar
  const renderBar = (score: number) => {
    const { filled, empty } = buildBar(score);
    const barColor = score >= 70 ? theme.colors.crimson : score >= 30 ? theme.colors.coral : theme.colors.sage;
    return (
      <Box>
        <Text color={barColor as any}>{'█'.repeat(filled)}</Text>
        <Text color="gray">{'░'.repeat(empty)}</Text>
      </Box>
    );
  };

  // Generic pipeline row
  const renderPipelineRow = (name: string, data: PipelineResult) => {
    const score = data.score;
    const scoreColor = score >= 70 ? theme.colors.crimson : score >= 30 ? theme.colors.coral : theme.colors.sage;

    return (
      <Box flexDirection="column" marginBottom={1} borderStyle="round" borderColor="gray" paddingX={1}>
        <Box justifyContent="space-between">
          <Text bold color="white">{name}</Text>
          <Box>
            <Text color="gray">[ </Text>
            {renderBar(score)}
            <Text color="gray"> ] </Text>
            <Text bold color={scoreColor as any}>{score.toFixed(1)}/100</Text>
          </Box>
        </Box>

        {data.flags && data.flags.length > 0 ? (
          <Box flexDirection="column" marginTop={1} paddingLeft={2}>
            {data.flags.map((flag, idx) => (
              <Text key={idx} color={score >= 50 ? 'yellow' : 'gray'}>
                {'  >'} {flag}
              </Text>
            ))}
          </Box>
        ) : (
          <Box marginTop={1} paddingLeft={2}>
            <Text italic color="gray">No anomalies detected.</Text>
          </Box>
        )}
      </Box>
    );
  };

  return (
    <Box flexDirection="column" paddingX={2} marginTop={1} marginBottom={1}>

      {/* ── Risk Summary ─────────────────────────────────────── */}
      <Box
        borderStyle="double"
        borderColor={theme.colors.gold as any}
        flexDirection="column"
        paddingX={2}
        paddingY={1}
        marginBottom={1}
      >
        <Box justifyContent="space-between" marginBottom={1}>
          <Text bold color="white">-- DOCUMENT SCAN REPORT</Text>
          <Box>
            <Text color="gray">Risk: </Text>
            <Text bold color={tierColor as any}>[{tierLabel}]</Text>
          </Box>
        </Box>

        <Box flexDirection="column">
          <Text>File Name:      <Text color={theme.colors.gold as any}>{filename}</Text></Text>
          <Text>File Type:      <Text color={theme.colors.sand as any}>{file_type}</Text> ({page_count} {page_count === 1 ? 'page' : 'pages'})</Text>
          <Text>Classification: <Text color={theme.colors.sand as any}>{is_scanned ? 'Scanned Document (Image-only)' : 'Digital Native PDF'}</Text></Text>

          <Box marginTop={1} justifyContent="space-between">
            <Text bold>FORENSIC THREAT INDEX:</Text>
            <Text bold color={tierColor as any}>{final_score.toFixed(1)} / 100</Text>
          </Box>
        </Box>
      </Box>

      {/* ── Engine Diagnostics ───────────────────────────────── */}
      <Box marginBottom={1}>
        <Text bold color={theme.colors.gold as any}>-- FORENSIC ENGINE DIAGNOSTICS</Text>
      </Box>

      {renderPipelineRow('Error Level Analysis (ELA)', pipelines.ela)}
      {renderPipelineRow('Metadata Forensics',         pipelines.metadata)}

      {/* Seal detection — has extra fields */}
      <Box flexDirection="column" marginBottom={1} borderStyle="round" borderColor="gray" paddingX={1}>
        <Box justifyContent="space-between">
          <Text bold color="white">Seal & Signature Detection</Text>
          <Box>
            <Text color="gray">[ </Text>
            {renderBar(pipelines.seal.score)}
            <Text color="gray"> ] </Text>
            <Text
              bold
              color={(pipelines.seal.score >= 70 ? theme.colors.crimson : pipelines.seal.score >= 30 ? theme.colors.coral : theme.colors.sage) as any}
            >
              {pipelines.seal.score.toFixed(1)}/100
            </Text>
          </Box>
        </Box>
        <Box justifyContent="space-between" marginTop={1} paddingLeft={2}>
          <Text color="gray">Official Seals: <Text color="white">{String(pipelines.seal.seals_found)}</Text></Text>
          <Text color="gray">Suspicious:     <Text color={pipelines.seal.suspicious > 0 ? theme.colors.coral as any : theme.colors.sage as any}>{String(pipelines.seal.suspicious)}</Text></Text>
        </Box>
        {pipelines.seal.flags && pipelines.seal.flags.length > 0 && (
          <Box flexDirection="column" marginTop={1} paddingLeft={2}>
            {pipelines.seal.flags.map((flag, idx) => (
              <Text key={idx} color="yellow">{'  >'} {flag}</Text>
            ))}
          </Box>
        )}
      </Box>

      {renderPipelineRow('NLP Logical Scrutiny', pipelines.nlp)}

      {/* ── Embedded Assets ──────────────────────────────────── */}
      <Box flexDirection="column" marginTop={1}>
        <Box marginBottom={1}>
          <Text bold color={theme.colors.gold as any}>-- EMBEDDED ASSETS & METADATA</Text>
        </Box>

        <Box flexDirection="column" paddingLeft={2}>
          <Box>
            <Text bold color="gray">QR Codes: </Text>
            {qr_codes && qr_codes.length > 0 ? (
              <Box flexDirection="column">
                {qr_codes.map((qr, idx) => (
                  <Text key={idx} color="cyan">  [{idx + 1}] {qr}</Text>
                ))}
              </Box>
            ) : (
              <Text italic color="gray">none extracted</Text>
            )}
          </Box>

          {pdf_metadata && Object.keys(pdf_metadata).length > 0 && (
            <Box marginTop={1} flexDirection="column">
              <Text bold color="gray">PDF Core Properties:</Text>
              {Object.entries(pdf_metadata).slice(0, 5).map(([key, val]) => (
                <Text key={key} color="gray">  {'>'} {key}: <Text color="white">{String(val)}</Text></Text>
              ))}
            </Box>
          )}
        </Box>
      </Box>
    </Box>
  );
};
