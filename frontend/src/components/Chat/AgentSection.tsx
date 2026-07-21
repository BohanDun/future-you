import { useRef, useState } from 'react';
import {
  Box,
  Button,
  Card,
  IconButton,
  Stack,
  TextField,
  ToggleButton,
  ToggleButtonGroup,
  Typography,
} from '@mui/material';
import SendRoundedIcon from '@mui/icons-material/SendRounded';
import { colors } from '../../theme/theme';
import { suggestedQuestions } from '../../data/mockCustomer';
import {
  applyAgentChanges,
  askFutureYou,
  planAgentChanges,
  type ConversationMessage,
  type ManageAgentResponse,
} from '../../lib/api';
import type { SimulationResult } from '../../lib/financialTools';
import type { CustomerProfile } from '../../data/mockCustomer';
import { ChatMessage, type Message } from './ChatMessage';
import { SuggestedQuestions } from './SuggestedQuestions';
import { ComparisonPanel } from '../Simulation/ComparisonPanel';
import { ActionProposal } from './ActionProposal';

let idCounter = 0;
const nextId = () => `msg-${idCounter++}`;

type AgentMode = 'advice' | 'manage';

const welcomeMessage = (mode: AgentMode): Message => ({
  id: nextId(),
  role: 'agent',
  text: mode === 'advice'
    ? "Ask me for guidance or run a what-if. Advice mode can read your plan, but it cannot change it."
    : "What would you like to work on? I can draft updates to your profile or goals, and you’ll review everything before it’s saved.",
});

const manageSuggestions = [
  'Create a $5,000 emergency goal with $250 monthly contributions.',
  'Change my monthly income to $5,500.',
  'Update how much I have saved toward one of my goals.',
];

interface Props {
  onProfileUpdated: (profile: CustomerProfile) => void;
}

export function AgentSection({ onProfileUpdated }: Props) {
  const [mode, setMode] = useState<AgentMode>('advice');
  const [messages, setMessages] = useState<Message[]>([welcomeMessage('advice')]);
  const [input, setInput] = useState('');
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<SimulationResult | null>(null);
  const [proposal, setProposal] = useState<ManageAgentResponse | null>(null);
  const [applying, setApplying] = useState(false);
  const [proposalError, setProposalError] = useState<string | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);

  async function send(question: string) {
    const q = question.trim();
    if (!q || busy) return;

    const userMsg: Message = { id: nextId(), role: 'user', text: q };
    const pendingMsg: Message = { id: nextId(), role: 'agent', text: '', pending: true };
    setMessages((prev) => [...prev, userMsg, pendingMsg]);
    setInput('');
    setBusy(true);

    const history: ConversationMessage[] = messages
      .filter((message) => !message.pending && message.text.trim())
      .slice(-20)
      .map((message) => ({
        role: message.role === 'agent' ? 'assistant' : 'user',
        content: message.text.slice(0, 2000),
      }));

    try {
      if (mode === 'advice') {
        const response = await askFutureYou(q, history);
        setMessages((prev) => prev.map((message) => (
          message.id === pendingMsg.id
            ? { ...message, text: response.explanation, pending: false }
            : message
        )));
        setResult(response.simulation);
      } else {
        const manageResponse = await planAgentChanges(q, history);
        setMessages((prev) => prev.map((message) => (
          message.id === pendingMsg.id
            ? { ...message, text: manageResponse.message, pending: false }
            : message
        )));
        setProposal(
          manageResponse.operations.length && manageResponse.proposalToken
            ? manageResponse
            : null,
        );
        setProposalError(null);
      }
    } catch (err) {
      const message =
        err instanceof Error && err.message
          ? err.message
          : "I couldn't reach the backend just now — please try again in a moment.";
      setMessages((prev) =>
        prev.map((m) =>
          m.id === pendingMsg.id ? { ...m, text: message, pending: false } : m,
        ),
      );
    } finally {
      setBusy(false);
      requestAnimationFrame(() => {
        scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: 'smooth' });
      });
    }
  }

  function changeMode(nextMode: AgentMode | null) {
    if (!nextMode || nextMode === mode || busy || applying) return;
    setMode(nextMode);
    setMessages([welcomeMessage(nextMode)]);
    setInput('');
    setResult(null);
    setProposal(null);
    setProposalError(null);
  }

  function resetConversation() {
    if (busy || applying) return;
    setMessages([welcomeMessage(mode)]);
    setInput('');
    setResult(null);
    setProposal(null);
    setProposalError(null);
  }

  async function applyProposal() {
    if (!proposal || applying) return;
    setApplying(true);
    setProposalError(null);
    try {
      if (!proposal.proposalToken) {
        throw new Error('This preview cannot be confirmed. Please prepare it again.');
      }
      const updated = await applyAgentChanges(proposal.proposalToken);
      onProfileUpdated(updated);
      setProposal(null);
      setMessages((previous) => [
        ...previous,
        { id: nextId(), role: 'agent', text: 'All done — your changes are saved and the dashboard is up to date.' },
      ]);
    } catch (error) {
      setProposalError(error instanceof Error ? error.message : 'Could not apply the changes.');
    } finally {
      setApplying(false);
    }
  }

  return (
    <Stack spacing={3}>
      <Stack spacing={0.5}>
        <Typography variant="h6" sx={{ color: colors.futureTeal }}>
          Ask Future You
        </Typography>
        <Typography variant="h4">What happens if…</Typography>
        <Stack direction="row" spacing={1.5} alignItems="center" sx={{ pt: 1 }}>
          <ToggleButtonGroup
            exclusive
            size="small"
            value={mode}
            onChange={(_, nextMode: AgentMode | null) => changeMode(nextMode)}
            disabled={busy || applying}
          >
            <ToggleButton value="advice">Advice</ToggleButton>
            <ToggleButton value="manage">Manage</ToggleButton>
          </ToggleButtonGroup>
          <Button
            size="small"
            color="inherit"
            onClick={resetConversation}
            disabled={busy || applying}
          >
            New chat
          </Button>
        </Stack>
      </Stack>

      <Card sx={{ p: { xs: 2, sm: 2.5 } }}>
        <Stack spacing={2}>
          <Box
            ref={scrollRef}
            sx={{
              maxHeight: 320,
              overflowY: 'auto',
              pr: 0.5,
            }}
          >
            <Stack spacing={1.5}>
              {messages.map((m) => (
                <ChatMessage key={m.id} message={m} />
              ))}
            </Stack>
          </Box>

          <SuggestedQuestions
            questions={mode === 'advice' ? suggestedQuestions : manageSuggestions}
            onSelect={send}
            disabled={busy || Boolean(proposal)}
          />

          <Stack direction="row" spacing={1}>
            <TextField
              fullWidth
              size="small"
              placeholder={mode === 'advice'
                ? 'Ask for advice or try a what-if…'
                : 'Describe the goal or financial detail to update…'}
              value={input}
              disabled={busy || Boolean(proposal)}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter') send(input);
              }}
              sx={{
                '& .MuiOutlinedInput-root': {
                  borderRadius: '10px',
                  bgcolor: colors.paper,
                },
              }}
            />
            <IconButton
              onClick={() => send(input)}
              disabled={busy || Boolean(proposal) || !input.trim()}
              sx={{
                bgcolor: colors.ink,
                color: '#fff',
                borderRadius: '10px',
                '&:hover': { bgcolor: colors.ink },
                '&.Mui-disabled': { bgcolor: colors.line, color: colors.inkSoft },
              }}
            >
              <SendRoundedIcon fontSize="small" />
            </IconButton>
          </Stack>
        </Stack>
      </Card>

      {result && <ComparisonPanel result={result} />}
      {proposal && (
        <ActionProposal
          changes={proposal.preview}
          applying={applying}
          error={proposalError}
          onApply={() => void applyProposal()}
          onCancel={() => {
            setProposal(null);
            setProposalError(null);
            setMessages((previous) => [
              ...previous,
              { id: nextId(), role: 'agent', text: 'No problem — nothing was saved. Tell me what you’d like to adjust.' },
            ]);
          }}
        />
      )}
    </Stack>
  );
}
