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
  const [startDate, setStartDate] = useState<string>("");
  const [endDate, setEndDate] = useState<string>("");
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

        // Map "month" to current month range if needed, or just let backend handle it
        // If "custom" and dates are missing, fallback or wait
        if (period === "custom" && (!startDate || !endDate)) {
          setLoading(false);
          return;
        }

        const [ov, trend, products, categories, hourly, recent] =
          await Promise.all([
            api.dashboard.overview(period, startDate, endDate),
            api.dashboard.salesTrend(period, startDate, endDate),
            api.dashboard.topProducts(period, 10, startDate, endDate),
            api.dashboard.salesByCategory(period, startDate, endDate),
            api.dashboard.hourlyDistribution(period, startDate, endDate),
            api.dashboard.recentSales(20),
          ]);

        setOverview(ov);
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
  }, [period, startDate, endDate]);

  if (error) {
    return (
      <div className="flex items-center gap-3 rounded-xl border border-red-200 bg-red-50 p-6 text-red-800 shadow-sm transition-all animate-in fade-in zoom-in duration-300">
        <AlertCircle className="h-6 w-6 flex-shrink-0" />
        <div>
          <p className="font-bold text-lg">Error loading dashboard</p>
          <p className="text-sm opacity-90">{error}</p>
          <p className="text-xs mt-3 font-medium px-2 py-1 bg-red-100 rounded-md w-fit">
            Ensure backend is running and database is connected.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-8 animate-in fade-in duration-700">
      <div className="flex flex-col gap-6 md:flex-row md:items-center md:justify-between bg-card p-6 rounded-2xl shadow-sm border border-border/50">
        <div>
          <h1 className="text-4xl font-extrabold tracking-tight bg-gradient-to-r from-primary to-primary/60 bg-clip-text text-transparent">
            Dashboard
          </h1>
          <p className="text-muted-foreground mt-1 font-medium">
            Real-time insights for Alex Coffee
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          {period === "custom" && (
            <div className="flex items-center gap-2 animate-in slide-in-from-right-4 duration-300">
              <input
                type="date"
                value={startDate}
                onChange={(e) => setStartDate(e.target.value)}
                className="h-9 px-3 rounded-md border border-input bg-transparent text-sm focus:outline-none focus:ring-2 focus:ring-ring"
              />
              <span className="text-muted-foreground font-medium">to</span>
              <input
                type="date"
                value={endDate}
                onChange={(e) => setEndDate(e.target.value)}
                className="h-9 px-3 rounded-md border border-input bg-transparent text-sm focus:outline-none focus:ring-2 focus:ring-ring"
              />
            </div>
          )}

          <div className="w-[160px]">
            <Select value={period} onValueChange={(value) => setPeriod(value as Period)}>
              <SelectTrigger className="h-9 font-medium">
                <SelectValue placeholder="Period" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="today">Today</SelectItem>
                <SelectItem value="week">This Week</SelectItem>
                <SelectItem value="month">This Month</SelectItem>
                <SelectItem value="year">This Year</SelectItem>
                <SelectItem value="custom">Custom Range</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </div>
      </div>

      {loading && !overview ? (
        <div className="flex flex-col items-center justify-center py-32 space-y-4">
          <Loader2 className="h-10 w-10 animate-spin text-primary" />
          <p className="text-sm font-medium text-muted-foreground animate-pulse">
            Fetching latest analytics...
          </p>
        </div>
      ) : (
        <div className="space-y-8 pb-12">
          <KPICards
            revenue={overview?.revenue || 0}
            revenueChange={overview?.revenue_change || 0}
            orders={overview?.orders || 0}
            ordersChange={overview?.orders_change || 0}
            avgTicket={overview?.avg_ticket || 0}
            itemsSold={overview?.items_sold || 0}
          />

          <div className="grid gap-4">
            <SalesChart data={salesTrend} />
          </div>

          <div className="grid gap-6 md:grid-cols-2">
            <TopProducts data={topProducts} />
            <SalesByCategory data={categoryData} />
          </div>

          <div className="grid gap-6">
            <HourlyDistribution data={hourlyData} />
          </div>

          <div className="grid gap-6">
            <RecentSales data={recentSalesData} />
          </div>
        </div>
      )}
    </div>
  );
}
