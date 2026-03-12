'use client';

import { useEffect, useState } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/Button';
import { Download, FileText, AlertTriangle, RefreshCw } from 'lucide-react';
import { listAnalyticsReports, generateAnalyticsReport } from '@/services/api';

type Report = {
    id: string;
    name: string;
    status: string;
    report_type: string;
    generated_at?: string;
    download_url?: string;
};

type ReportDefinition = {
    id: string;
    name: string;
    description: string;
};

export function AnalyticsReports() {
    const [loading, setLoading] = useState(true);
    const [reports, setReports] = useState<Report[]>([]);
    const [definitions, setDefinitions] = useState<ReportDefinition[]>([]);
    const [generating, setGenerating] = useState<string | null>(null);
    const [error, setError] = useState<string | null>(null);

    async function loadReports() {
        try {
            setLoading(true);
            const result = await listAnalyticsReports('founder');
            const data = result as Record<string, unknown>;
            const items = Array.isArray(data?.reports)
                ? (data.reports as Report[])
                : Array.isArray(result)
                    ? (result as unknown as Report[])
                    : [];
            setReports(items);
            const defs = Array.isArray(data?.definitions)
                ? (data.definitions as ReportDefinition[])
                : [];
            setDefinitions(defs);
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Failed to load reports');
        } finally {
            setLoading(false);
        }
    }

    useEffect(() => {
        loadReports();
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, []);

    async function handleGenerate(definitionId: string) {
        setGenerating(definitionId);
        try {
            await generateAnalyticsReport('founder', definitionId);
            await loadReports();
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Failed to generate report');
        } finally {
            setGenerating(null);
        }
    }

    if (loading) {
        return (
            <Card>
                <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                        <FileText className="h-5 w-5" />
                        Reports
                    </CardTitle>
                    <CardDescription>Loading report history...</CardDescription>
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
                        Reports
                    </CardTitle>
                    <CardDescription className="text-destructive">{error}</CardDescription>
                </CardHeader>
                <CardContent>
                    <Button variant="ghost" onClick={loadReports}>
                        <RefreshCw className="mr-2 h-4 w-4" />
                        Retry
                    </Button>
                </CardContent>
            </Card>
        );
    }

    return (
        <div className="space-y-4">
            {definitions.length > 0 && (
                <Card>
                    <CardHeader>
                        <CardTitle>Generate Report</CardTitle>
                        <CardDescription>Create a new on-demand analytics report</CardDescription>
                    </CardHeader>
                    <CardContent>
                        <div className="space-y-2">
                            {definitions.map((def) => (
                                <div key={def.id} className="flex items-center justify-between rounded border p-3">
                                    <div>
                                        <p className="font-medium">{def.name}</p>
                                        <p className="text-sm text-muted-foreground">{def.description}</p>
                                    </div>
                                    <Button
                                        variant="secondary"
                                        disabled={generating === def.id}
                                        onClick={() => handleGenerate(def.id)}
                                    >
                                        {generating === def.id ? (
                                            <RefreshCw className="mr-2 h-4 w-4 animate-spin" />
                                        ) : (
                                            <Download className="mr-2 h-4 w-4" />
                                        )}
                                        Generate
                                    </Button>
                                </div>
                            ))}
                        </div>
                    </CardContent>
                </Card>
            )}

            <Card>
                <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                        <FileText className="h-5 w-5" />
                        Report History
                        <Button variant="ghost" className="ml-auto" onClick={loadReports}>
                            <RefreshCw className="mr-2 h-4 w-4" />
                            Refresh
                        </Button>
                    </CardTitle>
                    <CardDescription>Previously generated reports</CardDescription>
                </CardHeader>
                <CardContent>
                    {reports.length === 0 ? (
                        <p className="text-sm text-muted-foreground">No reports generated yet.</p>
                    ) : (
                        <div className="space-y-2">
                            {reports.map((report) => (
                                <div key={report.id} className="flex items-center justify-between rounded border p-3">
                                    <div>
                                        <p className="font-medium">{report.name}</p>
                                        <p className="text-sm text-muted-foreground">
                                            {report.report_type}
                                            {report.generated_at
                                                ? ` — ${new Date(report.generated_at).toLocaleString()}`
                                                : ''}
                                        </p>
                                    </div>
                                    <div className="flex items-center gap-2">
                                        <Badge
                                            variant={
                                                report.status === 'completed'
                                                    ? 'success'
                                                    : report.status === 'failed'
                                                        ? 'destructive'
                                                        : 'secondary'
                                            }
                                        >
                                            {report.status}
                                        </Badge>
                                        {report.download_url && report.status === 'completed' && (
                                            <a href={report.download_url} download>
                                                <Button variant="ghost">
                                                    <Download className="h-4 w-4" />
                                                </Button>
                                            </a>
                                        )}
                                    </div>
                                </div>
                            ))}
                        </div>
                    )}
                </CardContent>
            </Card>
        </div>
    );
}
