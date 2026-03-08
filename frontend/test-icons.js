const icons = require('./node_modules/lucide-react');
const toCheck = ['ArrowRight', 'ShieldCheck', 'Activity', 'Database', 'ShieldAlert', 'Network', 'TerminalSquare', 'Users', 'Eye', 'LockKeyhole', 'Server', 'Cpu', 'ScanLine', 'Key', 'ChevronRight', 'Target', 'RadioTower', 'Box', 'AlertTriangle', 'PhoneCall', 'Workflow', 'ClipboardList', 'TrendingUp', 'Navigation', 'PenTool', 'CheckCircle', 'Shield', 'Flag', 'Calculator', 'Crosshair', 'ArrowUpRight', 'Zap'];
toCheck.forEach(i => { if(!icons[i]) console.log('MISSING:', i); });
