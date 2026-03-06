"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { formatCurrency, formatNumber } from "@/lib/utils";

interface RecentSalesProps {
  data: {
    id: number;
    order_number: string | null;
    product: string;
    quantity: number;
    total: number;
    payment_method: string | null;
    date: string;
  }[];
}

export function RecentSales({ data }: RecentSalesProps) {
  if (data.length === 0) {
    return (
      <Card className="shadow-sm">
        <CardHeader>
          <CardTitle className="text-lg font-medium">Recent Sales</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">No sales data available</p>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="col-span-full shadow-md border-muted">
      <CardHeader className="flex flex-row items-center justify-between">
        <CardTitle className="text-lg font-medium">Recent Sales</CardTitle>
        <span className="text-xs font-medium px-2.5 py-0.5 rounded-full bg-primary/10 text-primary">
          Latest {data.length} transactions
        </span>
      </CardHeader>
      <CardContent>
        <div className="overflow-x-auto">
          <Table>
            <TableHeader className="bg-muted/50">
              <TableRow>
                <TableHead className="font-bold">Order</TableHead>
                <TableHead className="font-bold">Product</TableHead>
                <TableHead className="font-bold">Qty</TableHead>
                <TableHead className="text-right font-bold">Amount</TableHead>
                <TableHead className="font-bold">Payment</TableHead>
                <TableHead className="font-bold">Time</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {data.map((sale) => (
                <TableRow key={sale.id} className="hover:bg-muted/30 transition-colors">
                  <TableCell className="font-mono text-xs text-muted-foreground">
                    #{sale.order_number || "-"}
                  </TableCell>
                  <TableCell className="max-w-[200px] truncate font-medium">
                    {sale.product}
                  </TableCell>
                  <TableCell>{formatNumber(sale.quantity)}</TableCell>
                  <TableCell className="text-right font-bold text-primary">
                    {formatCurrency(sale.total)}
                  </TableCell>
                  <TableCell>
                    <span className="text-xs px-2 py-0.5 rounded-md bg-secondary text-secondary-foreground font-medium">
                      {sale.payment_method || "N/A"}
                    </span>
                  </TableCell>
                  <TableCell className="text-sm text-muted-foreground whitespace-nowrap">
                    {new Date(sale.date).toLocaleTimeString("en-US", {
                      hour: "2-digit",
                      minute: "2-digit",
                      hour12: true,
                    })}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      </CardContent>
    </Card>
  );
}
