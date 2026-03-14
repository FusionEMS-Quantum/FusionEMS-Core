import { Suspense } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Skeleton } from '@/components/ui/skeleton';
import { Button } from '@/components/ui/Button';
import { Calendar, Download, TrendingUp, AlertTriangle, DollarSign, Stethoscope, Users } from 'lucide-react';
import { AnalyticsExecutiveSummary } from './components/executive-summary';
import { AnalyticsOperationalMetrics } from './components/operational-metrics';
import { AnalyticsFinancialMetrics } from './components/financial-metrics';
import { AnalyticsClinicalMetrics } from './components/clinical-metrics';
import { AnalyticsReadinessMetrics } from './components/readiness-metrics';
import { AnalyticsAlerts } from './components/alerts';
import { AnalyticsReports } from './components/reports';

export default function AnalyticsDashboard() {
  return (
    <div className="container mx-auto p-6 space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Analytics Command Center</h1>
          <p className="text-muted-foreground">
            Real-time operational, financial, clinical, and workforce intelligence
          </p>
        </div>
        <div className="flex gap-2">
          <Button variant="ghost">
            <Calendar className="mr-2 h-4 w-4" />
            Date Range
          </Button>
          <Button variant="ghost">
            <Download className="mr-2 h-4 w-4" />
            Export
          </Button>
        </div>
      </div>

      <Tabs defaultValue="executive" className="space-y-4">
        <TabsList>
          <TabsTrigger value="executive">
            <TrendingUp className="mr-2 h-4 w-4" />
            Executive Summary
          </TabsTrigger>
          <TabsTrigger value="operational">
            <AlertTriangle className="mr-2 h-4 w-4" />
            Operational
          </TabsTrigger>
          <TabsTrigger value="financial">
            <DollarSign className="mr-2 h-4 w-4" />
            Financial
          </TabsTrigger>
          <TabsTrigger value="clinical">
            <Stethoscope className="mr-2 h-4 w-4" />
            Clinical
          </TabsTrigger>
          <TabsTrigger value="readiness">
            <Users className="mr-2 h-4 w-4" />
            Readiness
          </TabsTrigger>
          <TabsTrigger value="alerts">
            <AlertTriangle className="mr-2 h-4 w-4" />
            Alerts
          </TabsTrigger>
          <TabsTrigger value="reports">
            <Download className="mr-2 h-4 w-4" />
            Reports
          </TabsTrigger>
        </TabsList>

        <Suspense fallback={<AnalyticsSkeleton />}>
          <TabsContent value="executive" className="space-y-4">
            <AnalyticsExecutiveSummary />
          </TabsContent>

          <TabsContent value="operational" className="space-y-4">
            <AnalyticsOperationalMetrics />
          </TabsContent>

          <TabsContent value="financial" className="space-y-4">
            <AnalyticsFinancialMetrics />
          </TabsContent>

          <TabsContent value="clinical" className="space-y-4">
            <AnalyticsClinicalMetrics />
          </TabsContent>

          <TabsContent value="readiness" className="space-y-4">
            <AnalyticsReadinessMetrics />
          </TabsContent>

          <TabsContent value="alerts" className="space-y-4">
            <AnalyticsAlerts />
          </TabsContent>

          <TabsContent value="reports" className="space-y-4">
            <AnalyticsReports />
          </TabsContent>
        </Suspense>
      </Tabs>
    </div>
  );
}

function AnalyticsSkeleton() {
  return (
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <Skeleton className="h-6 w-1/4" />
          <Skeleton className="h-4 w-1/2" />
        </CardHeader>
        <CardContent className="space-y-4">
          <Skeleton className="h-32 w-full" />
          <div className="grid grid-cols-4 gap-4">
            <Skeleton className="h-24" />
            <Skeleton className="h-24" />
            <Skeleton className="h-24" />
            <Skeleton className="h-24" />
          </div>
        </CardContent>
      </Card>
    </div>
  );
}