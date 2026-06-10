import React, { useEffect, useState } from 'react';
import { Box, Text } from 'ink';
import { theme } from '../theme.js';
import { useSpinner, SYM } from '../utils.js';

interface PipelineProgressProps {
  onComplete: () => void;
  isApiDone:  boolean;
}

interface Stage {
  id:          string;
  name:        string;
  desc:        string;
  minDuration: number; // ms
}

const STAGES: Stage[] = [
  { id: 'ingest',  name: 'Document Ingestion',    desc: 'Parsing structure and extracting pages',              minDuration: 1000 },
  { id: 'ela',     name: 'Error Level Analysis',   desc: 'Scanning compression and local noise differences',    minDuration: 1200 },
  { id: 'meta',    name: 'Metadata Forensics',     desc: 'Analyzing PDF revision history and author tags',      minDuration: 800  },
  { id: 'seal',    name: 'Seal Detection',         desc: 'Running YOLO seal and signature detection',           minDuration: 1500 },
  { id: 'nlp',     name: 'NLP Cross-Doc Scrutiny', desc: 'Checking logical flow and text consistency',          minDuration: 1000 },
  { id: 'fusion',  name: 'Score Fusion',           desc: 'Fusing scores and determining risk tier',             minDuration: 600  },
];

export const PipelineProgress: React.FC<PipelineProgressProps> = ({ onComplete, isApiDone }) => {
  const [currentStageIdx,  setCurrentStageIdx]  = useState(0);
  const [completedStages,  setCompletedStages]  = useState<Record<string, boolean>>({});

  const isRunning = currentStageIdx < STAGES.length;
  const spinner   = useSpinner(isRunning);

  // Stage transitions
  useEffect(() => {
    let active = true;
    const currentStage = STAGES[currentStageIdx];

    if (!currentStage) {
      if (isApiDone) onComplete();
      return;
    }

    const timer = setTimeout(() => {
      if (!active) return;

      const isLastStage = currentStageIdx === STAGES.length - 1;

      if (!isLastStage) {
        setCompletedStages((prev) => ({ ...prev, [currentStage.id]: true }));
        setCurrentStageIdx((prev) => prev + 1);
      } else if (isApiDone) {
        setCompletedStages((prev) => ({ ...prev, [currentStage.id]: true }));
        setCurrentStageIdx((prev) => prev + 1);
      }
    }, currentStage.minDuration);

    return () => {
      active = false;
      clearTimeout(timer);
    };
  }, [currentStageIdx, isApiDone, onComplete]);

  // Speed-complete if API is already done
  useEffect(() => {
    if (isApiDone && currentStageIdx < STAGES.length) {
      if (currentStageIdx === STAGES.length - 1) {
        setCompletedStages((prev) => ({ ...prev, [STAGES[currentStageIdx].id]: true }));
        setCurrentStageIdx((prev) => prev + 1);
      }
    }
  }, [isApiDone, currentStageIdx]);

  return (
    <Box flexDirection="column" paddingX={2} marginTop={1} marginBottom={1}>
      {/* Header */}
      <Box marginBottom={1}>
        <Text bold color={theme.colors.gold as any}>-- RUNNING FORENSIC PIPELINES</Text>
      </Box>

      <Box flexDirection="column">
        {STAGES.map((stage, idx) => {
          const isCompleted = completedStages[stage.id];
          const isActive    = idx === currentStageIdx;

          const nameColor: string = isCompleted ? theme.colors.sage : isActive ? theme.colors.gold : theme.colors.slate;

          return (
            <Box key={stage.id} flexDirection="column" marginBottom={1}>
              <Box>
                {isCompleted ? (
                  <Text color={theme.colors.sage as any}>{SYM.CHECK} </Text>
                ) : isActive ? (
                  <Text color={theme.colors.gold as any}>{spinner}  </Text>
                ) : (
                  <Text color="gray">  ...  </Text>
                )}
                <Text bold={isActive} color={nameColor as any}>{stage.name}</Text>
              </Box>
              <Box paddingLeft={7}>
                <Text italic={isActive} color={isActive ? 'white' : 'gray'}>{stage.desc}</Text>
              </Box>
            </Box>
          );
        })}
      </Box>
    </Box>
  );
};
