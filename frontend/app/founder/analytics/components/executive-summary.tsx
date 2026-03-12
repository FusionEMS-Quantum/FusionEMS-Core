'use client';

import { useEffect, useState } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Progress } from '@/components/ui/progress';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/Button';
import { TrendingUp, TrendingDown, AlertTriangle, CheckCircle } from 'lucide-react';
import { getAnalyticsExecutiveSummary } from '@/services/api';

type ScoreCard = {
  title: string;
  value: number;
  trend: 'up' | 'down' | 'neutral';
  change: number;
  description: string;
};

type TopAction = {
  domain: string;
  severity: 'BLOCKING' | 'HIGH' | 'MEDIUM' | 'LOW' | 'INFORMATIONAL';
  summary: string;
  recommended_action: string;
};

export function AnalyticsExecutiveSummary() {
  const [loading, setLoading] = useState(true);
  const [data, setData] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function loadData() {
      try {
        // TODO: Replace with actual agency ID
        const result = await getAnalyticsExecutiveSummary('founder');
        setData(result);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load executive summary');
      } finally {
        setLoading(false);
      }
    }
    loadData();
  }, []);

  if (loading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Executive Summary</CardTitle>
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
          <CardTitle>Executive Summary</CardTitle>
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

  const scores = data?.scores || {};
  const topActions = data?.top_actions || [];

  const scoreCards: ScoreCard[] = [
    {
      title: 'Revenue Score',
      value: scores.revenue_score || 0,
      trend: scores.revenue_score > 80 ? 'up' : scores.revenue_score < 60 ? 'down' : 'neutral',
      change: 2.5,
      description: 'Billing health & collections',
    },
    {
      title: 'Ops Score',
      value: scores.ops_score || 0,
      trend: scores.ops_score > 80 ? 'up' : scores.ops_score < 60 ? 'down' : 'neutral',
      change: -1.2,
      description: 'Deployment & claims pipeline',
    },
    {
      title: 'Clinical Score',
      value: scores.clinical_score || 0,
      trend: scores.clinical_score > 80 ? 'up' : scores.clinical_score < 60 ? 'down' : 'neutral',
      change: 0.8,
      description: 'Record quality & compliance',
    },
    {
      title: 'Workforce Score',
      value: scores.workforce_score || 0,
      trend: scores.workforce_score > 80 ? 'up' : scores.workforce_score < 60 ? 'down' : 'neutral',
      change: 3.1,
      description: 'Readiness & staffing',
    },
    {
      title: 'Compliance Score',
      value: scores.compliance_score || 0,
      trend: scores.compliance_score > 80 ? 'up' : scores.compliance_score < 60 ? 'down' : 'neutral',
      change: -0.5,
      description: 'Regulatory adherence',
    },
  ];

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle>Executive Health Scores</CardTitle>
          <CardDescription>
            Overall platform health across five critical domains
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4">
            {scoreCards.map((card) => (
              <Card key={card.title} className="relative">
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm font-medium">{card.title}</CardTitle>
                  <CardDescription className="text-xs">{card.description}</CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="flex items-baseline justify-between">
                    <div className="text-2xl font-bold">{card.value.toFixed(1)}</div>
                    <div className="flex items-center text-xs">
                      {card.trend === 'up' && (
                        <>
                          <TrendingUp className="h-3 w-3 text-green-500 mr-1" />
                          <span className="text-green-500">+{card.change}%</span>
                        </>
                      )}
                      {card.trend === 'down' && (
                        <>
                          <TrendingDown className="h-3 w-3 text-red-500 mr-1" />
                          <span className="text-red-500">{card.change}%</span>
                        </>
                      )}
                      {card.trend === 'neutral' && (
                        <span className="text-muted-foreground">0.0%</span>
                      )}
                    </div>
                  </div>
                  <Progress value={card.value} className="mt-2" />
                  <div className="text-xs text-muted-foreground mt-1">
                    {card.value >= 90 ? 'Excellent' :
                      card.value >= 80 ? 'Good' :
                        card.value >= 70 ? 'Fair' :
                          card.value >= 60 ? 'Needs Attention' : 'Critical'}
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Top Priority Actions</CardTitle>
          <CardDescription>
            Highest impact interventions recommended by the system
          </CardDescription>
        </CardHeader>
        <CardContent>
          {topActions.length > 0 ? (
            <div className="space-y-4">
              {topActions.slice(0, 5).map((action: TopAction, index: number) => (
                <div key={index} className="flex items-start gap-4 p-4 border rounded-lg">
                  <div>
                    {action.severity === 'BLOCKING' && (
                      <AlertTriangle className="h-5 w-5 text-red-500" />
                    )}
                    {action.severity === 'HIGH' && (
                      <AlertTriangle className="h-5 w-5 text-orange-500" />
                    )}
                    {action.severity === 'MEDIUM' && (
                      <AlertTriangle className="h-5 w-5 text-yellow-500" />
                    )}
                    {action.severity === 'LOW' && (
                      <CheckCircle className="h-5 w-5 text-blue-500" />
                    )}
                    {action.severity === 'INFORMATIONAL' && (
                      <CheckCircle className="h-5 w-5 text-green-500" />
                    )}
                  </div>
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-1">
                      <Badge variant={action.severity === 'BLOCKING' ? 'destructive' : 'secondary'}>
                        {action.severity}
                      </Badge>
                      <span className="text-sm font-medium">{action.domain}</span>
                    </div>
                    <p className="font-medium">{action.summary}</p>
                    <p className="text-sm text-muted-foreground mt-1">
                      {action.recommended_action}
                    </p>
                  </div>
                  <Button variant="ghost">
                    Take Action
                  </Button>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-center py-8 text-muted-foreground">
              No priority actions identified. All systems operating normally.
            </div>
          )}
        </CardContent>
      </Card>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card>
          <CardHeader>
            <CardTitle>Financial Snapshot</CardTitle>
            <CardDescription>Revenue & billing overview</CardDescription>
          </CardHeader>
          <CardContent>
            {data?.financial ? (
              <div className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <div className="text-sm text-muted-foreground">MRR</div>
                    <div className="text-2xl font-bold">
                      ${((data.financial.mrr_cents || 0) / 100).toLocaleString()}
                    </div>
                  </div>
                  <div>
                    <div className="text-sm text-muted-foreground">ARR</div>
                    <div className="text-2xl font-bold">
                      ${((data.financial.arr_cents || 0) / 100).toLocaleString()}
                    </div>
                  </div>
                </div>
                <div className="text-sm text-muted-foreground">
                  As of {new Date(data.snapshot_time || Date.now()).toLocaleDateString()}
                </div>
              </div>
            ) : (
              <div className="text-center py-8 text-muted-foreground">
                Financial data not available
              </div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Operational Health</CardTitle>
            <CardDescription>Deployment & claims status</CardDescription>
          </CardHeader>
          <CardContent>
            {data?.ops ? (
              <div className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <div className="text-sm text-muted-foreground">Failed Deployments</div>
                    <div className="text-2xl font-bold text-red-500">
                      {data.ops.deployment_issues?.failed_deployments || 0}
                    </div>
                  </div>
                  <div>
                    <div className="text-sm text-muted-foreground">Blocking Issues</div>
                    <div className="text-2xl font-bold text-orange-500">
                      {data.ops.claims_pipeline?.blocking_issues || 0}
                    </div>
                  </div>
                </div>
                <div className="text-sm">
                  <span className="text-muted-foreground">CrewLink escalations:</span>{' '}
                  <span className="font-medium">
                    {data.ops.crewlink_health?.escalations_last_24h || 0} last 24h
                  </span>
                </div>
              </div>
            ) : (
              <div className="text-center py-8 text-muted-foreground">
                Operational data not available
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}