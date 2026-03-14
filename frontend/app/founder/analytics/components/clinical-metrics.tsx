'use client';

import { useEffect, useState } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Stethoscope, TrendingUp, TrendingDown, AlertTriangle } from 'lucide-react';
import { getAnalyticsClinicalMetrics } from '@/services/api';

export function AnalyticsClinicalMetrics() {
    const [loading, setLoading] = useState(true);
    const [data, setData] = useState<Record<string, unknown> | null>(null);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        async function loadData() {
            try {
                const endDate = new Date();
                const startDate = new Date();
                startDate.setDate(startDate.getDate() - 30);
                const result = await getAnalyticsClinicalMetrics(
                    'founder',
                    startDate.toISOString(),
                    endDate.toISOString()
                );
                setData(result);
            } catch (err) {
                setError(err instanceof Error ? err.message : 'Failed to load clinical metrics');
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
                    <CardTitle className="flex items-center gap-2">
                        <Stethoscope className="h-5 w-5" />
                        Clinical Metrics
                    </CardTitle>
                    <CardDescription>Loading clinical performance data...</CardDescription>
                </CardHeader>
                <CardContent>
                    <div className="h-48 flex items-center justify-center">
                        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
                    </div>
                </CardContent>
            </Card>
        );
    }

    if (error) {
        return (
            <Card>
                <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                        <AlertTriangle className="h-5 w-5 text-destructive" />
                        Clinical Metrics
                    </CardTitle>
                    <CardDescription className="text-destructive">{error}</CardDescription>
                </CardHeader>
            </Card>
        );
    }

    const summary = (data?.summary as Record<string, unknown>) ?? {};
    const scores = (data?.scores as Record<string, unknown>[]) ?? [];

    return (
        <div className="space-y-4">
            <Card>
                <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                        <Stethoscope className="h-5 w-5" />
                        Clinical Performance Overview
                    </CardTitle>
                    <CardDescription>30-day clinical outcome and quality metrics</CardDescription>
                </CardHeader>
                <CardContent>
                    <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
                        {[
                            { label: 'Protocol Compliance', key: 'protocol_compliance_pct' },
                            { label: 'ROSC Rate', key: 'rosc_rate_pct' },
                            { label: 'Scene Time (avg)', key: 'avg_scene_time_min' },
                            { label: 'Outcome Score', key: 'outcome_score' },
                        ].map(({ label, key }) => {
                            const val = summary[key];
                            return (
                                <div key={key} className="rounded-lg border p-4 text-center space-y-1">
                                    <p className="text-xs text-muted-foreground uppercase tracking-wide">{label}</p>
                                    <p className="text-2xl font-bold">
                                        {val !== undefined ? String(val) : '—'}
                                    </p>
                                </div>
                            );
                        })}
                    </div>
                </CardContent>
            </Card>

            {scores.length > 0 && (
                <Card>
                    <CardHeader>
                        <CardTitle>Clinical Quality Scores</CardTitle>
                    </CardHeader>
                    <CardContent>
                        <div className="space-y-3">
                            {scores.map((score, idx) => {
                                const trend = String(score.trend ?? 'neutral');
                                return (
                                    <div key={idx} className="flex items-center justify-between rounded border p-3">
                                        <div>
                                            <p className="font-medium">{String(score.metric ?? 'Metric')}</p>
                                            <p className="text-sm text-muted-foreground">{String(score.description ?? '')}</p>
                                        </div>
                                        <div className="flex items-center gap-2">
                                            <Badge variant={trend === 'up' ? 'success' : trend === 'down' ? 'destructive' : 'secondary'}>
                                                {trend === 'up' ? (
                                                    <TrendingUp className="h-3 w-3 mr-1" />
                                                ) : trend === 'down' ? (
                                                    <TrendingDown className="h-3 w-3 mr-1" />
                                                ) : null}
                                                {String(score.value ?? '—')}
                                            </Badge>
                                        </div>
                                    </div>
                                );
                            })}
                        </div>
                    </CardContent>
                </Card>
            )}
        </div>
    );
}
