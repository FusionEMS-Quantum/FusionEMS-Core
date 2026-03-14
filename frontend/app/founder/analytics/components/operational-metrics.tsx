'use client';

import { useEffect, useState } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/Button';
import { Calendar, Download, TrendingUp, TrendingDown } from 'lucide-react';
import { getAnalyticsOperationalMetrics } from '@/services/api';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  BarChart,
  Bar,
} from 'recharts';

type FailureEvent = {
  id: string;
  severity: string;
  source: string;
  what_is_wrong: string;
  created_at: string;
};

export function AnalyticsOperationalMetrics() {
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

        const result = await getAnalyticsOperationalMetrics(
          'founder',
          startDate.toISOString(),
          endDate.toISOString()
        );
        setData(result);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load operational metrics');
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
          <CardTitle>Operational Metrics</CardTitle>
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
          <CardTitle>Operational Metrics</CardTitle>
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

  const operational = data?.operational_snapshot || {};
  const recentFailures = data?.recent_failure_events || [];

  // Mock chart data - replace with actual time series data
  const requestVolumeData = [
    { day: 'Mon', volume: 120 },
    { day: 'Tue', volume: 150 },
    { day: 'Wed', volume: 180 },
    { day: 'Thu', volume: 160 },
    { day: 'Fri', volume: 200 },
    { day: 'Sat', volume: 140 },
    { day: 'Sun', volume: 110 },
  ];

  const failureData = [
    { category: 'Deployment', count: operational.deployment_failures || 0 },
    { category: 'Delivery', count: operational.failed_deliveries || 0 },
    { category: 'Escalations', count: operational.active_alerts || 0 },
  ];

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h2 className="text-2xl font-bold">Operational Intelligence</h2>
          <p className="text-muted-foreground">
            Real-time deployment, delivery, and escalation metrics
          </p>
        </div>
        <div className="flex gap-2">
          <Button
            variant={timeRange === '7d' ? 'primary' : 'secondary'}
            size="sm"
            onClick={() => setTimeRange('7d')}
          >
            7D
          </Button>
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
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">Request Volume</CardTitle>
            <CardDescription>Last 30 days</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{operational.request_volume || 0}</div>
            <div className="flex items-center text-sm">
              <TrendingUp className="h-4 w-4 text-green-500 mr-1" />
              <span className="text-green-500">+12% from last period</span>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">Escalation Rate</CardTitle>
            <CardDescription>Response escalations</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{operational.escalation_rate_pct || 0}%</div>
            <div className="flex items-center text-sm">
              <TrendingDown className="h-4 w-4 text-red-500 mr-1" />
              <span className="text-red-500">-3% from last period</span>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">Failed Deliveries</CardTitle>
            <CardDescription>Messages & exports</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{operational.failed_deliveries || 0}</div>
            <div className="flex items-center text-sm">
              <TrendingUp className="h-4 w-4 text-orange-500 mr-1" />
              <span className="text-orange-500">+5 from last period</span>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">Active Alerts</CardTitle>
            <CardDescription>Requiring attention</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{operational.active_alerts || 0}</div>
            <div className="flex items-center text-sm">
              <TrendingDown className="h-4 w-4 text-green-500 mr-1" />
              <span className="text-green-500">-2 from last period</span>
            </div>
          </CardContent>
        </Card>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card>
          <CardHeader>
            <CardTitle>Request Volume Trend</CardTitle>
            <CardDescription>Daily request patterns</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={requestVolumeData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                  <XAxis dataKey="day" stroke="#9ca3af" />
                  <YAxis stroke="#9ca3af" />
                  <Tooltip
                    contentStyle={{ backgroundColor: '#1f2937', borderColor: '#374151' }}
                    labelStyle={{ color: '#f3f4f6' }}
                  />
                  <Line
                    type="monotone"
                    dataKey="volume"
                    stroke="#3b82f6"
                    strokeWidth={2}
                    dot={{ r: 4 }}
                    activeDot={{ r: 6 }}
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Failure Distribution</CardTitle>
            <CardDescription>By failure category</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={failureData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                  <XAxis dataKey="category" stroke="#9ca3af" />
                  <YAxis stroke="#9ca3af" />
                  <Tooltip
                    contentStyle={{ backgroundColor: '#1f2937', borderColor: '#374151' }}
                    labelStyle={{ color: '#f3f4f6' }}
                  />
                  <Bar dataKey="count" fill="#ef4444" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Recent Failure Events</CardTitle>
          <CardDescription>Last 20 failure events requiring attention</CardDescription>
        </CardHeader>
        <CardContent>
          {recentFailures.length > 0 ? (
            <div className="space-y-4">
              {recentFailures.map((event: FailureEvent) => (
                <div key={event.id} className="flex items-start justify-between p-4 border rounded-lg">
                  <div className="space-y-1">
                    <div className="flex items-center gap-2">
                      <Badge
                        variant=
                        {event.severity === 'CRITICAL' ? 'destructive' :
                          event.severity === 'HIGH' ? 'destructive' :
                            event.severity === 'MEDIUM' ? 'secondary' : 'outline'}
                      >
                        {event.severity}
                      </Badge>
                      <span className="text-sm font-medium">{event.source}</span>
                    </div>
                    <p className="font-medium">{event.what_is_wrong}</p>
                    <p className="text-sm text-muted-foreground">
                      {new Date(event.created_at).toLocaleString()}
                    </p>
                  </div>
                  <Button variant="ghost">
                    Investigate
                  </Button>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-center py-8 text-muted-foreground">
              No recent failure events. All systems operating normally.
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}