"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ArrowUp, ArrowDown, TrendingUp } from "lucide-react";
import { formatCurrency, formatNumber } from "@/lib/utils";

interface KPICardsProps {
  revenue: number;
  revenueChange: number;
  orders: number;
  ordersChange: number;
  avgTicket: number;
  itemsSold: number;
}

export function KPICards({
  revenue,
  revenueChange,
  orders,
  ordersChange,
  avgTicket,
  itemsSold,
}: KPICardsProps) {
  return (
    <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
      <Card className="border-t-4 border-t-chart-1">
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium">Total Revenue</CardTitle>
          <TrendingUp className="h-4 w-4 text-muted-foreground" />
        </CardHeader>
        <CardContent>
          <div className="text-2xl font-bold">{formatCurrency(revenue)}</div>
          <p className={`text-xs ${revenueChange >= 0 ? "text-green-600" : "text-red-600"}`}>
            {revenueChange >= 0 ? "+" : ""}{revenueChange.toFixed(1)}% from last period
          </p>
        </CardContent>
      </Card>

      <Card className="border-t-4 border-t-chart-2">
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium">Orders</CardTitle>
          <TrendingUp className="h-4 w-4 text-muted-foreground" />
        </CardHeader>
        <CardContent>
          <div className="text-2xl font-bold">{formatNumber(orders)}</div>
          <p className={`text-xs ${ordersChange >= 0 ? "text-green-600" : "text-red-600"}`}>
            {ordersChange >= 0 ? "+" : ""}{ordersChange.toFixed(1)}% from last period
          </p>
        </CardContent>
      </Card>

      <Card className="border-t-4 border-t-chart-3">
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium">Avg Ticket</CardTitle>
          <TrendingUp className="h-4 w-4 text-muted-foreground" />
        </CardHeader>
        <CardContent>
          <div className="text-2xl font-bold">{formatCurrency(avgTicket)}</div>
          <p className="text-xs text-muted-foreground">Average order value</p>
        </CardContent>
      </Card>

      <Card className="border-t-4 border-t-chart-4">
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium">Items Sold</CardTitle>
          <TrendingUp className="h-4 w-4 text-muted-foreground" />
        </CardHeader>
        <CardContent>
          <div className="text-2xl font-bold">{formatNumber(itemsSold)}</div>
          <p className="text-xs text-muted-foreground">Total units sold</p>
        </CardContent>
      </Card>
    </div>
  );
}
