/**
 * Formats a number with thousands separators and no decimal places.
 * Example: 1234.56 -> 1,235
 */
export function formatNumber(value: number | string | undefined | null): string {
  if (value === undefined || value === null) return "0";
  const num = typeof value === "string" ? parseFloat(value) : value;
  if (isNaN(num)) return "0";

  return new Intl.NumberFormat("en-US", {
    style: "decimal",
    maximumFractionDigits: 0,
    minimumFractionDigits: 0,
  }).format(num);
}

/**
 * Formats a currency value with thousands separators, no decimal places, and a dollar sign.
 * Example: 1234.56 -> $1,235
 */
export function formatCurrency(value: number | string | undefined | null): string {
  if (value === undefined || value === null) return "$0";
  const num = typeof value === "string" ? parseFloat(value) : value;
  if (isNaN(num)) return "$0";

  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 0,
    minimumFractionDigits: 0,
  }).format(num);
}
