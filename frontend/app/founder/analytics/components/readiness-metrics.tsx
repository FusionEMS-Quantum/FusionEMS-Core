'use client';

import { useEffect, useState } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { Users, AlertTriangle, CheckCircle } from 'lucide-react';
import { getAnalyticsReadinessMetrics } from '@/services/api';

export function AnalyticsReadinessMetrics() {
    const [loading, setLoading] = useState(true);
    const [data, setData] = useState<Record<string, unknown> | null>(null);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        async function loadData() {
            try {
                const endDate = new Date();
                const startDate = new Date();
                startDate.setDate(startDate.getDate() - 30);
                const result = await getAnalyticsReadinessMetrics(
                    'founder',
                    startDate.toISOString(),
                    endDate.toISOString()
                );
                setData(result);
            } catch (err) {
                setError(err instanceof Error ? err.message : 'Failed to load readiness metrics');
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
                        <Users className="h-5 w-5" />
                        Workforce &amp; Fleet Readiness
                    </CardTitle>
                    <CardDescription>Loading readiness data...</CardDescription>
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
                        Workforce &amp; Fleet Readiness
                    </CardTitle>
                    <CardDescription className="text-destructive">{error}</CardDescription>
                </CardHeader>
            </Card>
        );
    }

    const summary = (data?.summary as Record<string, unknown>) ?? {};
    const units = (data?.units as Record<string, unknown>[]) ?? [];
    const staff = (data?.staff as Record<string, unknown>[]) ?? [];

    const readinessPct = typeof summary.overall_readiness_pct === 'number'
        ? summary.overall_readiness_pct
        : 0;

    return (
        <div className="space-y-4">
            <Card>
                <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                        <Users className="h-5 w-5" />
                        Workforce &amp; Fleet Readiness
                    </CardTitle>
                    <CardDescription>Operational readiness posture — 30-day window</CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                    <div>
                        <div className="flex justify-between mb-2">
                            <span className="text-sm font-medium">Overall Readiness</span>
                            <span className="text-sm text-muted-foreground">{readinessPct}%</span>
                        </div>
                        <Progress value={readinessPct} className="h-3" />
                    </div>
                    <div className="grid grid-cols-2 gap-4 md:grid-cols-3">
                        {[
                            { label: 'Staffed Units', key: 'staffed_units' },
                            { label: 'Cert Compliance', key: 'cert_compliance_pct' },
                            { label: 'Fleet Available', key: 'fleet_available_pct' },
                        ].map(({ label, key }) => (
                            <div key={key} className="rounded-lg border p-4 text-center space-y-1">
                                <p className="text-xs text-muted-foreground uppercase tracking-wide">{label}</p>
                                <p className="text-2xl font-bold">
                                    {summary[key] !== undefined ? String(summary[key]) : '—'}
                                </p>
                            </div>
                        ))}
                    </div>
                </CardContent>
            </Card>

            {units.length > 0 && (
                <Card>
                    <CardHeader>
                        <CardTitle>Unit Status</CardTitle>
                    </CardHeader>
                    <CardContent>
                        <div className="space-y-2">
                            {units.map((unit, idx) => {
                                const status = String(unit.status ?? 'unknown');
                                return (
                                    <div key={idx} className="flex items-center justify-between rounded border p-3">
                                        <div>
                                            <p className="font-medium">{String(unit.unit_id ?? `Unit ${idx + 1}`)}</p>
                                            <p className="text-sm text-muted-foreground">{String(unit.type ?? '')}</p>
                                        </div>
                                        <Badge variant={status === 'available' ? 'success' : status === 'unavailable' ? 'destructive' : 'secondary'}>
                                            {status === 'available' ? (
                                                <CheckCircle className="h-3 w-3 mr-1" />
                                            ) : (
                                                <AlertTriangle className="h-3 w-3 mr-1" />
                                            )}
                                            {status}
                                        </Badge>
                                    </div>
                                );
                            })}
                        </div>
                    </CardContent>
                </Card>
            )}

            {staff.length > 0 && (
                <Card>
                    <CardHeader>
                        <CardTitle>Certification Compliance</CardTitle>
                    </CardHeader>
                    <CardContent>
                        <div className="space-y-2">
                            {staff.map((member, idx) => (
                                <div key={idx} className="flex items-center justify-between rounded border p-3">
                                    <div>
                                        <p className="font-medium">{String(member.name ?? `Staff ${idx + 1}`)}</p>
                                        <p className="text-sm text-muted-foreground">{String(member.role ?? '')}</p>
                                    </div>
                                    <Badge variant={member.compliant ? 'success' : 'destructive'}>
                                        {member.compliant ? 'Compliant' : 'Non-Compliant'}
                                    </Badge>
                                </div>
                            ))}
                        </div>
                    </CardContent>
                </Card>
            )}
        </div>
    );
}
