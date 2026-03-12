'use client';

import { useEffect, useState } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { AlertTriangle, Bell, CheckCircle, XCircle } from 'lucide-react';
import { getAnalyticsAlerts } from '@/services/api';

type AlertEntry = {
    id: string;
    severity: string;
    domain: string;
    summary: string;
    created_at: string;
    resolved: boolean;
};

const SEVERITY_VARIANT: Record<string, 'destructive' | 'warning' | 'secondary' | 'default'> = {
    BLOCKING: 'destructive',
    HIGH: 'destructive',
    MEDIUM: 'warning',
    LOW: 'secondary',
    INFORMATIONAL: 'default',
};

export function AnalyticsAlerts() {
    const [loading, setLoading] = useState(true);
    const [alerts, setAlerts] = useState<AlertEntry[]>([]);
    const [error, setError] = useState<string | null>(null);
    const [filter, setFilter] = useState<string>('');

    useEffect(() => {
        async function loadData() {
            try {
                const result = await getAnalyticsAlerts('founder', filter || undefined);
                const items = Array.isArray(result?.alerts)
                    ? (result.alerts as AlertEntry[])
                    : Array.isArray(result)
                        ? (result as AlertEntry[])
                        : [];
                setAlerts(items);
            } catch (err) {
                setError(err instanceof Error ? err.message : 'Failed to load alerts');
            } finally {
                setLoading(false);
            }
        }
        loadData();
    }, [filter]);

    if (loading) {
        return (
            <Card>
                <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                        <Bell className="h-5 w-5" />
                        Platform Alerts
                    </CardTitle>
                    <CardDescription>Loading alert data...</CardDescription>
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
                        Platform Alerts
                    </CardTitle>
                    <CardDescription className="text-destructive">{error}</CardDescription>
                </CardHeader>
            </Card>
        );
    }

    const open = alerts.filter((a) => !a.resolved);
    const resolved = alerts.filter((a) => a.resolved);

    return (
        <div className="space-y-4">
            <div className="grid grid-cols-3 gap-4">
                {['ALL', 'BLOCKING', 'HIGH', 'MEDIUM', 'LOW'].map((sev) => (
                    <button
                        key={sev}
                        onClick={() => setFilter(sev === 'ALL' ? '' : sev)}
                        className={`rounded border px-3 py-1 text-xs font-medium transition-colors ${(filter === '' && sev === 'ALL') || filter === sev
                                ? 'bg-primary text-primary-foreground'
                                : 'bg-background hover:bg-muted'
                            }`}
                    >
                        {sev}
                    </button>
                ))}
            </div>

            <Card>
                <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                        <AlertTriangle className="h-5 w-5" />
                        Active Alerts
                        <Badge variant="destructive" className="ml-auto">
                            {open.length}
                        </Badge>
                    </CardTitle>
                    <CardDescription>Unresolved platform and operational alerts</CardDescription>
                </CardHeader>
                <CardContent>
                    {open.length === 0 ? (
                        <div className="flex items-center gap-2 text-sm text-muted-foreground">
                            <CheckCircle className="h-4 w-4 text-green-500" />
                            No active alerts
                        </div>
                    ) : (
                        <div className="space-y-2">
                            {open.map((alert) => (
                                <div key={alert.id} className="rounded border p-3 space-y-1">
                                    <div className="flex items-center justify-between">
                                        <Badge variant={SEVERITY_VARIANT[alert.severity] ?? 'secondary'}>
                                            {alert.severity}
                                        </Badge>
                                        <span className="text-xs text-muted-foreground">
                                            {new Date(alert.created_at).toLocaleString()}
                                        </span>
                                    </div>
                                    <p className="text-sm font-medium">{alert.domain}</p>
                                    <p className="text-sm text-muted-foreground">{alert.summary}</p>
                                </div>
                            ))}
                        </div>
                    )}
                </CardContent>
            </Card>

            {resolved.length > 0 && (
                <Card>
                    <CardHeader>
                        <CardTitle className="flex items-center gap-2">
                            <XCircle className="h-5 w-5" />
                            Recently Resolved
                            <Badge variant="secondary" className="ml-auto">
                                {resolved.length}
                            </Badge>
                        </CardTitle>
                    </CardHeader>
                    <CardContent>
                        <div className="space-y-2">
                            {resolved.slice(0, 5).map((alert) => (
                                <div key={alert.id} className="rounded border p-3 opacity-60 space-y-1">
                                    <div className="flex items-center justify-between">
                                        <Badge variant="secondary">{alert.severity}</Badge>
                                        <span className="text-xs text-muted-foreground">
                                            {new Date(alert.created_at).toLocaleString()}
                                        </span>
                                    </div>
                                    <p className="text-sm">{alert.summary}</p>
                                </div>
                            ))}
                        </div>
                    </CardContent>
                </Card>
            )}
        </div>
    );
}
