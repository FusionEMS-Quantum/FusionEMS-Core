#!/usr/bin/env node

import fs from 'node:fs';
import path from 'node:path';

const projectRoot = process.cwd();
const appDir = path.join(projectRoot, 'app');

if (!fs.existsSync(appDir)) {
  console.error('[route-audit] app/ directory not found. Run this script from frontend workspace root.');
  process.exit(1);
}

const IGNORED_DIRS = new Set(['node_modules', '.next', '.git']);
const PAGE_FILE_RE = /^page\.(tsx|ts|jsx|js)$/;
const CODE_FILE_RE = /\.(tsx|ts|jsx|js)$/;

const ALLOWED_NON_PAGE_PREFIXES = ['/api/', '/track/'];
const ALLOWED_NON_PAGE_EXACT = new Set(['/health', '/healthz', '/favicon.ico', '/robots.txt', '/sitemap.xml']);

function walk(dir) {
  const out = [];
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    if (entry.isDirectory()) {
      if (IGNORED_DIRS.has(entry.name)) continue;
      out.push(...walk(path.join(dir, entry.name)));
      continue;
    }
    out.push(path.join(dir, entry.name));
  }
  return out;
}

function normalizeSlash(p) {
  if (!p) return '/';
  const stripped = p.replace(/\/+$/, '');
  return stripped === '' ? '/' : stripped;
}

function stripQueryAndHash(p) {
  const noQuery = p.split('?')[0] ?? p;
  return (noQuery.split('#')[0] ?? noQuery) || '/';
}

function routeSegments(routePath) {
  if (routePath === '/') return [];
  return routePath.split('/').filter(Boolean);
}

function isDynamicSegment(seg) {
  return seg.startsWith('[') && seg.endsWith(']');
}

function isCatchAllSegment(seg) {
  return seg.startsWith('[...') && seg.endsWith(']');
}

function isOptionalCatchAllSegment(seg) {
  return seg.startsWith('[[...') && seg.endsWith(']]');
}

function urlPathFromPageFile(filePath) {
  const rel = path.relative(appDir, path.dirname(filePath));
  if (!rel || rel === '.') return '/';

  const segments = rel
    .split(path.sep)
    .filter(Boolean)
    .filter((seg) => {
      if (seg.startsWith('(') && seg.endsWith(')')) return false; // route groups
      if (seg.startsWith('@')) return false; // parallel route slots
      return true;
    });

  return normalizeSlash('/' + segments.join('/'));
}

function collectRoutePatterns() {
  const files = walk(appDir);
  const pageFiles = files.filter((f) => PAGE_FILE_RE.test(path.basename(f)));
  const patterns = pageFiles.map((f) => urlPathFromPageFile(f));

  return {
    patterns: Array.from(new Set(patterns)).sort(),
    pageFiles,
  };
}

function matchesRoutePattern(routePattern, concretePath) {
  const patternSegs = routeSegments(routePattern);
  const pathSegs = routeSegments(concretePath);

  let i = 0;
  let j = 0;

  while (i < patternSegs.length && j < pathSegs.length) {
    const p = patternSegs[i];

    if (isOptionalCatchAllSegment(p)) {
      return true;
    }

    if (isCatchAllSegment(p)) {
      return j < pathSegs.length;
    }

    if (isDynamicSegment(p)) {
      i += 1;
      j += 1;
      continue;
    }

    if (p !== pathSegs[j]) {
      return false;
    }

    i += 1;
    j += 1;
  }

  if (i === patternSegs.length && j === pathSegs.length) {
    return true;
  }

  if (i === patternSegs.length - 1) {
    const last = patternSegs[i];
    if (isOptionalCatchAllSegment(last)) return true;
    if (isCatchAllSegment(last)) return j < pathSegs.length;
  }

  return false;
}

function isAllowedNonPagePath(candidatePath) {
  if (ALLOWED_NON_PAGE_EXACT.has(candidatePath)) return true;
  return ALLOWED_NON_PAGE_PREFIXES.some((prefix) => candidatePath.startsWith(prefix));
}

function pathExistsAsRoute(candidatePath, routePatterns) {
  if (isAllowedNonPagePath(candidatePath)) return true;
  return routePatterns.some((pattern) => matchesRoutePattern(pattern, candidatePath));
}

function indexToLine(content, index) {
  let line = 1;
  for (let i = 0; i < index; i += 1) {
    if (content.charCodeAt(i) === 10) line += 1;
  }
  return line;
}

function extractPathRefs(content) {
  const refs = [];
  const regexes = [
    /href\s*=\s*['"`](\/[^'"`]+)['"`]/g,
    /href\s*:\s*['"`](\/[^'"`]+)['"`]/g,
    /router\.(?:push|replace|prefetch)\(\s*['"`](\/[^'"`]+)['"`]/g,
    /(?:redirect|permanentRedirect)\(\s*['"`](\/[^'"`]+)['"`]/g,
  ];

  for (const re of regexes) {
    let m;
    while ((m = re.exec(content)) !== null) {
      const raw = m[1];
      if (!raw) continue;
      if (raw.startsWith('http://') || raw.startsWith('https://')) continue;
      if (raw.startsWith('mailto:') || raw.startsWith('tel:')) continue;
      if (raw.startsWith('#')) continue;
      if (raw.includes('${')) continue;

      const normalized = normalizeSlash(stripQueryAndHash(raw));
      refs.push({ raw, normalized, index: m.index });
    }
  }

  return refs;
}

function collectCodeFiles() {
  return walk(appDir).filter((f) => CODE_FILE_RE.test(path.basename(f)));
}

function audit() {
  const { patterns: routePatterns, pageFiles } = collectRoutePatterns();
  const codeFiles = collectCodeFiles();

  const failures = [];
  let checkedRefs = 0;

  for (const filePath of codeFiles) {
    const content = fs.readFileSync(filePath, 'utf8');
    const refs = extractPathRefs(content);
    for (const ref of refs) {
      checkedRefs += 1;
      if (!pathExistsAsRoute(ref.normalized, routePatterns)) {
        failures.push({
          file: path.relative(projectRoot, filePath),
          line: indexToLine(content, ref.index),
          raw: ref.raw,
          normalized: ref.normalized,
        });
      }
    }
  }

  console.log(`[route-audit] pages=${pageFiles.length} route-patterns=${routePatterns.length} refs-checked=${checkedRefs}`);

  if (failures.length > 0) {
    console.error(`[route-audit] FAIL unresolved route references=${failures.length}`);
    for (const f of failures) {
      console.error(` - ${f.file}:${f.line} -> ${f.raw} (normalized: ${f.normalized})`);
    }
    process.exit(1);
  }

  console.log('[route-audit] PASS all static internal route references resolve to a page route or approved non-page endpoint');
}

audit();
