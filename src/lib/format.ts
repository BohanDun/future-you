export function formatCurrency(value: number): string {
  const sign = value < 0 ? '-' : '';
  return `${sign}$${Math.abs(Math.round(value)).toLocaleString('en-NZ')}`;
}

export function formatMonths(value: number): string {
  if (value === Infinity) return '—';
  if (value === 0) return 'Reached';
  return `${value} month${value === 1 ? '' : 's'}`;
}
