'use client';

import { useEffect, useState } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/Button';
import { Calendar, Download, TrendingUp, TrendingDown, DollarSign } from 'lucide-react';
import { getAnalyticsFinancialMetrics } from '@/services/api';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
} from 'recharts';

type PayerPerformance = {
  payer: string;
  submitted_cents: number;
  paid_cents: number;
  denial_rate: number;
  avg_days_to_pay: number;
};

export function AnalyticsFinancialMetrics() {
  const [loading, setLoading] = useState(true);
  const [data, setData] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);
  const [timeRange, setTimeRange] = useState('30d');

  useEffect(() => {
    async function loadData() {
      try {
        const endDate = new Date();
        const startDate = new Date();
        startDate.setDate(startDate.getDate() - 30);
        
        const result = await getAnalyticsFinancialMetrics(
          'founder',
          startDate.toISOString(),
          endDate.toISOString()
        );
        setData(result);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load financial metrics');
      } finally {
        setLoading(false);
      }
    }
    loadData();
  }, [timeRange]);

  if (loading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Financial Metrics</CardTitle>
          <CardDescription>Loading...</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="h-64 flex items-center justify-center">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
          </div>
        </CardContent>
      </Card>
    );
  }

  if (error) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Financial Metrics</CardTitle>
          <CardDescription>Error loading data</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="text-destructive p-4 border border-destructive/50 rounded-md">
            {error}
          </div>
        </CardContent>
      </Card>
    );
  }

  const financial = data?.financial_snapshot || {};
  const payerPerformance = data?.payer_performance || [];
  const revenueLeakage = data?.revenue_leakage || {};

  // Mock chart data
  const revenueData = [
    { month: 'Jan', revenue: 45000 },
    { month: 'Feb', revenue: 52000 },
    { month: 'Mar', revenue: 48000 },
    { month: 'Apr', revenue: 61000 },
    { month: 'May', revenue: 55000 },
    { month: 'Jun', revenue: 72000 },
  ];

  const payerData = payerPerformance.map((payer: PayerPerformance) => ({
    name: payer.payer,
    value: payer.paid_cents / 100,
  }));

  const COLORS = ['#0088FE', '#00C49F', '#FFBB28', '#FF8042', '#8884D8'];

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h2 className="text-2xl font-bold">Financial Intelligence</h2>
          <p className="text-muted-foreground">
            Revenue, collections, denial patterns, and payer performance
          </p>
        </div>
        <div className="flex gap-2">
          <Button
            variant={timeRange === '30d' ? 'primary' : 'secondary'}
            size="sm"
            onClick={() => setTimeRange('30d')}
          >
            30D
          </Button>
          <Button
            variant={timeRange === '90d' ? 'primary' : 'secondary'}
            size="sm"
            onClick={() => setTimeRange('90d')}
          >
            90D
          </Button>
          <Button
            variant={timeRange === '1y' ? 'primary' : 'secondary'}
            size="sm"
            onClick={() => setTimeRange('1y')}
          >
            1Y
          </Button>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">Total Revenue</CardTitle>
            <CardDescription>Last 30 days</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              ${((financial.total_revenue_cents || 0) / 100).toLocaleString()}
            </div>
            <div className="flex items-center text-sm">
              <TrendingUp className="h-4 w-4 text-green-500 mr-1" />
              <span className="text-green-500">+8.5% from last period</span>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">Net Collection Rate</CardTitle>
            <CardDescription>Overall collections</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{financial.net_collection_rate || 0}%</div>
            <div className="flex items-center text-sm">
              <TrendingDown className="h-4 w-4 text-red-500 mr-1" />
              <span className="text-red-500">-1.2% from last period</span>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">Denial Rate</CardTitle>
            <CardDescription>Claims denied</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{financial.denial_rate || 0}%</div>
            <div className="flex items-center text-sm">
              <TrendingUp className="h-4 w-4 text-orange-500 mr-1" />
              <span className="text-orange-500">+0.8% from last period</span>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">Avg Days in AR</CardTitle>
            <CardDescription>Accounts receivable</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{financial.avg_days_in_ar || 0} days</div>
            <div className="flex items-center text-sm">
              <TrendingDown className="h-4 w-4 text-green-500 mr-1" />
              <span className="text-green-500">-3 days from last period</span>
            </div>
          </CardContent>
        </Card>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card>
          <CardHeader>
            <CardTitle>Revenue Trend</CardTitle>
            <CardDescription>Monthly revenue performance</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={revenueData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                  <XAxis dataKey="month" stroke="#9ca3af" />
                  <YAxis stroke="#9ca3af" />
                  <Tooltip
                    contentStyle={{ backgroundColor: '#1f2937', borderColor: '#374151' }}
                    labelStyle={{ color: '#f3f4f6' }}
                    formatter={(value) => [`$${value}`, 'Revenue']}
                  />
                  <Bar dataKey="revenue" fill="#10b981" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Payer Mix</CardTitle>
            <CardDescription>Revenue distribution by payer</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={payerData}
                    cx="50%"
                    cy="50%"
                    labelLine={false}
                    label={(entry) => `${entry.name}: $${entry.value.toLocaleString()}`}
                    outerRadius={80}
                    fill="#8884d8"
                    dataKey="value"
                  >
                    {payerData.map((entry: { name: string; value: number }, index: number) => (
                      <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip
                    contentStyle={{ backgroundColor: '#1f2937', borderColor: '#374151' }}
                    labelStyle={{ color: '#f3f4f6' }}
                    formatter={(value: number | string) => [`$${value}`, 'Revenue']}
                  />
                </PieChart>
              </ResponsiveContainer>
            </div>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Payer Performance</CardTitle>
          <CardDescription>Detailed performance by payer class</CardDescription>
        </CardHeader>
        <CardContent>
          {payerPerformance.length > 0 ? (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b">
                    <th className="text-left py-3 px-4 font-medium">Payer</th>
                    <th className="text-left py-3 px-4 font-medium">Submitted</th>
                    <th className="text-left py-3 px-4 font-medium">Paid</th>
                    <th className="text-left py-3 px-4 font-medium">Denial Rate</th>
                    <th className="text-left py-3 px-4 font-medium">Avg Days to Pay</th>
                    <th className="text-left py-3 px-4 font-medium">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {payerPerformance.map((payer: PayerPerformance) => (
                    <tr key={payer.payer} className="border-b hover:bg-muted/50">
                      <td className="py-3 px-4">
                        <div className="font-medium">{payer.payer}</div>
                      </td>
                      <td className="py-3 px-4">
                        ${(payer.submitted_cents / 100).toLocaleString()}
                      </td>
                      <td className="py-3 px-4">
                        ${(payer.paid_cents / 100).toLocaleString()}
                      </td>
                      <td className="py-3 px-4">
                        <Badge
                          variant=
                            {payer.denial_rate > 20 ? 'destructive' :
                             payer.denial_rate > 10 ? 'secondary' : 'outline'}
                        >
                          {payer.denial_rate.toFixed(1)}%
                        </Badge>
                      </td>
                      <td className="py-3 px-4">
                        <Badge
                          variant=
                            {payer.avg_days_to_pay > 60 ? 'destructive' :
                             payer.avg_days_to_pay > 45 ? 'secondary' : 'outline'}
                        >
                          {payer.avg_days_to_pay} days
                        </Badge>
                      </td>
                      <td className="py-3 px-4">
                        <Button variant="ghost" size="sm">
                          Details
                        </Button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="text-center py-8 text-muted-foreground">
              No payer performance data available
            </div>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Revenue Leakage Analysis</CardTitle>
          <CardDescription>Identified opportunities for revenue recovery</CardDescription>
        </CardHeader>
        <CardContent>
          {revenueLeakage ? (
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="space-y-2">
                <div className="text-sm text-muted-foreground">Under-Coded Claims</div>
                <div className="text-2xl font-bold">
                  ${((revenueLeakage.under_coded_cents || 0) / 100).toLocaleString()}
                </div>
                <div className="text-sm">
                  {revenueLeakage.under_coded_count || 0} claims identified
                </div>
              </div>
              <div className="space-y-2">
                <div className="text-sm text-muted-foreground">Missing Documentation</div>
                <div className="text-2xl font-bold">
                  ${((revenueLeakage.missing_doc_cents || 0) / 100).toLocaleString()}
                </div>
                <div className="text-sm">
                  {revenueLeakage.missing_doc_count || 0} claims affected
                </div>
              </div>
              <div className="space-y-2">
                <div className="text-sm text-muted-foreground">Timely Filing Risk</div>
                <div className="text-2xl font-bold">
                  ${((revenueLeakage.timely_filing_cents || 0) / 100).toLocaleString()}
                </div>
                <div className="text-sm">
                  {revenueLeakage.timely_filing_count || 0} claims at risk
                </div>
              </div>
            </div>
          ) : (
            <div className="text-center py-8 text-muted-foreground">
              No revenue leakage analysis available
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}