import { useRef, useState } from 'react';
import { Box, Card, IconButton, Stack, TextField, Typography } from '@mui/material';
import SendRoundedIcon from '@mui/icons-material/SendRounded';
import { colors } from '../../theme/theme';
import { suggestedQuestions } from '../../data/mockCustomer';
import { askFutureYou } from '../../lib/api';
import type { SimulationResult } from '../../lib/financialTools';
import { ChatMessage, type Message } from './ChatMessage';
import { SuggestedQuestions } from './SuggestedQuestions';
import { ComparisonPanel } from '../Simulation/ComparisonPanel';

let idCounter = 0;
const nextId = () => `msg-${idCounter++}`;

export function AgentSection() {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: nextId(),
      role: 'agent',
      text: "Ask me anything about a purchase, a savings change, or a goal — I'll show you how it plays out.",
    },
  ]);
  const [input, setInput] = useState('');
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<SimulationResult | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);

  async function send(question: string) {
    const q = question.trim();
    if (!q || busy) return;

    const userMsg: Message = { id: nextId(), role: 'user', text: q };
    const pendingMsg: Message = { id: nextId(), role: 'agent', text: '', pending: true };
    setMessages((prev) => [...prev, userMsg, pendingMsg]);
    setInput('');
    setBusy(true);

    try {
      const response = await askFutureYou(q);
      setMessages((prev) =>
        prev.map((m) => (m.id === pendingMsg.id ? { ...m, text: response.explanation, pending: false } : m)),
      );
      setResult(response.simulation);
    } catch {
      setMessages((prev) =>
        prev.map((m) =>
          m.id === pendingMsg.id
            ? { ...m, text: "I couldn't reach the backend just now — please try again in a moment.", pending: false }
            : m,
        ),
      );
    } finally {
      setBusy(false);
      requestAnimationFrame(() => {
        scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: 'smooth' });
      });
    }
  }

  return (
    <Stack spacing={3}>
      <Stack spacing={0.5}>
        <Typography variant="h6" sx={{ color: colors.futureTeal }}>
          Ask Future You
        </Typography>
        <Typography variant="h4">What happens if…</Typography>
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

          <SuggestedQuestions questions={suggestedQuestions} onSelect={send} disabled={busy} />

          <Stack direction="row" spacing={1}>
            <TextField
              fullWidth
              size="small"
              placeholder="What happens if I buy a $2,000 laptop?"
              value={input}
              disabled={busy}
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
              disabled={busy || !input.trim()}
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
    </Stack>
  );
}
