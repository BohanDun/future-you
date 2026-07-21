import { FormEvent, useState } from 'react';
import AddIcon from '@mui/icons-material/Add';
import DeleteOutlineIcon from '@mui/icons-material/DeleteOutline';
import EditOutlinedIcon from '@mui/icons-material/EditOutlined';
import {
  Alert,
  Button,
  Card,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  IconButton,
  Stack,
  TextField,
  Typography,
} from '@mui/material';
import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { colors, numericFont } from '../../theme/theme';
import { diningInsight, type CustomerProfile } from '../../data/mockCustomer';
import { formatCurrency } from '../../lib/format';

interface CategoryRow {
  id: string;
  name: string;
  amount: string;
}

let categoryRowId = 0;
const newRowId = () => `spending-category-${categoryRowId++}`;

interface Props {
  profile: CustomerProfile;
  onSaveSpending?: (categories: Record<string, number>) => Promise<void>;
}

function initialRows(profile: CustomerProfile): CategoryRow[] {
  const rows = profile.spendingCategories.map((item) => ({
    id: newRowId(),
    name: item.category,
    amount: String(item.amount),
  }));
  return rows.length ? rows : [{ id: newRowId(), name: '', amount: '' }];
}

export function SpendingChart({ profile, onSaveSpending }: Props) {
  const [open, setOpen] = useState(false);
  const [rows, setRows] = useState<CategoryRow[]>(() => initialRows(profile));
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const categoryTotal = rows.reduce((total, row) => {
    const amount = Number.parseFloat(row.amount);
    return total + (Number.isFinite(amount) ? amount : 0);
  }, 0);
  const resultingSavings = profile.monthlyIncome - categoryTotal;

  function openEditor() {
    setRows(initialRows(profile));
    setError(null);
    setOpen(true);
  }

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (!onSaveSpending) return;
    const cleanedRows = rows.map((row) => ({
      name: row.name.trim().replace(/\s+/g, ' '),
      amount: Number.parseFloat(row.amount),
    }));
    if (cleanedRows.some((row) => !row.name || row.name.length > 40)) {
      setError('Enter a category name between 1 and 40 characters.');
      return;
    }
    if (cleanedRows.some((row) => !Number.isFinite(row.amount) || row.amount < 0)) {
      setError('Enter a non-negative amount for every category.');
      return;
    }
    const uniqueNames = new Set(cleanedRows.map((row) => row.name.toLocaleLowerCase()));
    if (uniqueNames.size !== cleanedRows.length) {
      setError('Each category needs a unique name.');
      return;
    }
    const categories = Object.fromEntries(
      cleanedRows.map((row) => [row.name, row.amount]),
    );
    setBusy(true);
    setError(null);
    try {
      await onSaveSpending(categories);
      setOpen(false);
    } catch (saveError) {
      setError(saveError instanceof Error ? saveError.message : 'Could not save spending.');
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <Card sx={{ p: 2.5, height: '100%' }}>
        <Stack spacing={2} sx={{ height: '100%' }}>
          <Stack spacing={0.5}>
            <Stack direction="row" alignItems="center" justifyContent="space-between">
              <Typography variant="h6" sx={{ color: colors.inkSoft }}>
                Spending by category
              </Typography>
              {onSaveSpending && (
                <Button size="small" startIcon={<EditOutlinedIcon />} onClick={openEditor}>
                  Manage spending
                </Button>
              )}
            </Stack>
            <Stack spacing={0.5}>
              {(profile.insights.length
                ? profile.insights
                : profile.spendingCategories.length
                  ? [diningInsight(profile)]
                  : []).map((insight) => (
                <Stack key={insight} direction="row" spacing={1} alignItems="flex-start">
                  <Typography aria-hidden sx={{ color: colors.futureTeal, lineHeight: 1.5 }}>
                    •
                  </Typography>
                  <Typography variant="body2" sx={{ color: colors.inkSoft }}>
                    {insight}
                  </Typography>
                </Stack>
              ))}
            </Stack>
          </Stack>

          <div style={{ width: '100%', height: 220 }}>
            {profile.spendingCategories.length ? (
              <ResponsiveContainer>
                <BarChart data={profile.spendingCategories} margin={{ top: 4, right: 8, left: -16, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke={colors.line} vertical={false} />
                  <XAxis dataKey="category" tick={{ fill: colors.inkSoft, fontSize: 12 }} axisLine={{ stroke: colors.line }} tickLine={false} />
                  <YAxis tick={{ fill: colors.inkSoft, fontSize: 12 }} axisLine={false} tickLine={false} width={56} />
                  <Tooltip formatter={(value: number) => formatCurrency(value)} contentStyle={{ fontFamily: numericFont, border: `1px solid ${colors.line}`, borderRadius: 8 }} />
                  <Bar dataKey="amount" fill={colors.horizonGold} radius={[6, 6, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <Stack justifyContent="center" alignItems="center" sx={{ height: '100%', px: 3 }}>
                <Typography color="text.secondary" textAlign="center">
                  Add your monthly spending categories to see the breakdown here.
                </Typography>
              </Stack>
            )}
          </div>
        </Stack>
      </Card>
      <Dialog open={open} onClose={() => !busy && setOpen(false)} fullWidth maxWidth="sm">
        <form onSubmit={submit}>
          <DialogTitle>Monthly spending by category</DialogTitle>
          <DialogContent>
            <Stack spacing={2} sx={{ pt: 1 }}>
              <Typography variant="body2" color="text.secondary">
                Add your monthly spending breakdown. Its total becomes your monthly expenses,
                and monthly savings updates automatically.
              </Typography>
              {error && <Alert severity="error">{error}</Alert>}
              <Stack spacing={1.5}>
                {rows.map((row, index) => (
                  <Stack direction="row" spacing={1} alignItems="center" key={row.id}>
                    <TextField
                      fullWidth
                      required
                      label="Category name"
                      inputProps={{ maxLength: 40 }}
                      value={row.name}
                      onChange={(event) => setRows((current) => current.map((item, itemIndex) => (
                        itemIndex === index ? { ...item, name: event.target.value } : item
                      )))}
                    />
                    <TextField
                      required
                      type="number"
                      label="Monthly amount"
                      inputProps={{ min: 0, step: 0.01 }}
                      value={row.amount}
                      onChange={(event) => setRows((current) => current.map((item, itemIndex) => (
                        itemIndex === index ? { ...item, amount: event.target.value } : item
                      )))}
                      sx={{ width: 190, flexShrink: 0 }}
                    />
                    <IconButton
                      aria-label={`Remove ${row.name || 'category'}`}
                      disabled={busy}
                      onClick={() => setRows((current) => current.filter((_, itemIndex) => itemIndex !== index))}
                    >
                      <DeleteOutlineIcon />
                    </IconButton>
                  </Stack>
                ))}
                <Button
                  startIcon={<AddIcon />}
                  disabled={busy || rows.length >= 12}
                  onClick={() => setRows((current) => [
                    ...current,
                    { id: newRowId(), name: '', amount: '' },
                  ])}
                  sx={{ alignSelf: 'flex-start' }}
                >
                  Add category
                </Button>
                {rows.length >= 12 && (
                  <Typography variant="caption" color="text.secondary">
                    You can have up to 12 spending categories.
                  </Typography>
                )}
              </Stack>
              <Stack
                direction={{ xs: 'column', sm: 'row' }}
                justifyContent="space-between"
                spacing={0.5}
                sx={{ p: 1.5, borderRadius: 2, bgcolor: colors.surface }}
              >
                <Typography variant="body2">
                  Monthly expenses: {formatCurrency(categoryTotal)}
                </Typography>
                <Typography variant="body2" color={resultingSavings < 0 ? 'error' : 'text.secondary'}>
                  Monthly savings: {formatCurrency(resultingSavings)}
                </Typography>
              </Stack>
            </Stack>
          </DialogContent>
          <DialogActions sx={{ px: 3, pb: 3 }}>
            <Button color="inherit" disabled={busy} onClick={() => setOpen(false)}>
              Cancel
            </Button>
            <Button type="submit" variant="contained" disabled={busy}>
              {busy ? 'Saving…' : 'Save spending'}
            </Button>
          </DialogActions>
        </form>
      </Dialog>
    </>
  );
}
