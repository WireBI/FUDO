"use client";

import { useState, useEffect } from "react";
import { Period, api } from "@/lib/api";
import { KPICards } from "@/components/kpi-cards";
import { SalesChart } from "@/components/sales-chart";
import { TopProducts } from "@/components/top-products";
import { SalesByCategory } from "@/components/sales-by-category";
import { HourlyDistribution } from "@/components/hourly-distribution";
import { RecentSales } from "@/components/recent-sales";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Loader2, AlertCircle } from "lucide-react";

export default function DashboardPage() {
  const [period, setPeriod] = useState<Period>("month");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [overview, setOverview] = useState<any>(null);
  const [salesTrend, setSalesTrend] = useState<any[]>([]);
  const [topProducts, setTopProducts] = useState<any[]>([]);
  const [categoryData, setCategoryData] = useState<any[]>([]);
  const [hourlyData, setHourlyData] = useState<any[]>([]);
  const [recentSalesData, setRecentSalesData] = useState<any[]>([]);

  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);
        setError(null);

        const [overview, trend, products, categories, hourly, recent] =
          await Promise.all([
            api.dashboard.overview(period),
            api.dashboard.salesTrend(period),
            api.dashboard.topProducts(period),
            api.dashboard.salesByCategory(period),
            api.dashboard.hourlyDistribution(period),
            api.dashboard.recentSales(20),
          ]);

        setOverview(overview);
        setSalesTrend(trend);
        setTopProducts(products);
        setCategoryData(categories);
        setHourlyData(hourly);
        setRecentSalesData(recent);
      } catch (err) {
        setError(
          err instanceof Error ? err.message : "Failed to load dashboard data"
        );
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [period]);

  if (error) {
    return (
      <div className="flex items-center gap-3 rounded-lg border border-red-200 bg-red-50 p-4 text-red-800">
        <AlertCircle className="h-5 w-5 flex-shrink-0" />
        <div>
          <p className="font-semibold">Error loading dashboard</p>
          <p className="text-sm">{error}</p>
          <p className="text-xs mt-2">
            Make sure the backend API is running and the database is initialized.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold tracking-tight">Dashboard</h1>
        <div className="w-[180px]">
          <Select value={period} onValueChange={(value) => setPeriod(value as Period)}>
            <SelectTrigger>
              <SelectValue placeholder="Select period" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="today">Today</SelectItem>
              <SelectItem value="week">This Week</SelectItem>
              <SelectItem value="month">This Month</SelectItem>
              <SelectItem value="year">This Year</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </div>

      {loading || !overview ? (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
        </div>
      ) : (
        <>
          <KPICards
            revenue={overview.revenue}
            revenueChange={overview.revenue_change}
            orders={overview.orders}
            ordersChange={overview.orders_change}
            avgTicket={overview.avg_ticket}
            itemsSold={overview.items_sold}
          />

          <div className="grid gap-4">
            <SalesChart data={salesTrend} />
          </div>

          <div className="grid gap-4 md:grid-cols-2">
            <TopProducts data={topProducts} />
            <SalesByCategory data={categoryData} />
          </div>

          <div className="grid gap-4">
            <HourlyDistribution data={hourlyData} />
          </div>

          <div className="grid gap-4">
            <RecentSales data={recentSalesData} />
          </div>
        </>
      )}
    </div>
  );
}
