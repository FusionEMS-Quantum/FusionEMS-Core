'use client';

import { useEffect, useMemo, useRef } from 'react';
import { cn } from '@/lib/utils';

type QuantumCanvasBackdropMode = 'global' | 'auth' | 'landing';

interface QuantumCanvasBackdropProps {
  readonly className?: string;
  readonly mode?: QuantumCanvasBackdropMode;
  readonly intensity?: number;
}

interface NodePoint {
  x: number;
  y: number;
  vx: number;
  vy: number;
  radius: number;
  alpha: number;
  tier: 'primary' | 'secondary';
}

const MODE_SPEC: Record<QuantumCanvasBackdropMode, {
  readonly connectionDistance: number;
  readonly nodeCount: number;
  readonly sweepAlpha: number;
}> = {
  global: {
    connectionDistance: 168,
    nodeCount: 22,
    sweepAlpha: 0.12,
  },
  auth: {
    connectionDistance: 154,
    nodeCount: 18,
    sweepAlpha: 0.16,
  },
  landing: {
    connectionDistance: 188,
    nodeCount: 28,
    sweepAlpha: 0.2,
  },
};

function buildNodes(width: number, height: number, mode: QuantumCanvasBackdropMode, intensity: number): NodePoint[] {
  const { nodeCount } = MODE_SPEC[mode];
  const areaScale = Math.max(1, Math.min(1.8, (width * height) / 1_300_000));
  const total = Math.round(nodeCount * areaScale * intensity);

  return Array.from({ length: total }, (_, index) => ({
    x: Math.random() * width,
    y: Math.random() * height,
    vx: (Math.random() - 0.5) * 0.12,
    vy: (Math.random() - 0.5) * 0.12,
    radius: index % 5 === 0 ? 1.9 : 1.15,
    alpha: index % 4 === 0 ? 0.75 : 0.38,
    tier: index % 5 === 0 ? 'primary' : 'secondary',
  }));
}

export default function QuantumCanvasBackdrop({
  className,
  mode = 'global',
  intensity = 1,
}: QuantumCanvasBackdropProps) {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const frameRef = useRef<number | null>(null);
  const nodesRef = useRef<NodePoint[]>([]);
  const spec = useMemo(() => MODE_SPEC[mode], [mode]);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) {
      return undefined;
    }

    const mediaQuery = window.matchMedia('(prefers-reduced-motion: reduce)');
    const ctx = canvas.getContext('2d');
    if (!ctx) {
      return undefined;
    }

    let width = 0;
    let height = 0;
    let dpr = Math.min(window.devicePixelRatio || 1, 2);
    let sweep = 0;

    const setCanvasSize = () => {
      width = window.innerWidth;
      height = window.innerHeight;
      dpr = Math.min(window.devicePixelRatio || 1, 2);

      canvas.width = Math.floor(width * dpr);
      canvas.height = Math.floor(height * dpr);
      canvas.style.width = `${width}px`;
      canvas.style.height = `${height}px`;

      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      nodesRef.current = buildNodes(width, height, mode, intensity);
    };

    const drawGrid = () => {
      const major = mode === 'landing' ? 80 : 96;
      const minor = major / 2;

      ctx.save();
      ctx.strokeStyle = 'rgba(255,255,255,0.028)';
      ctx.lineWidth = 1;
      for (let x = 0; x <= width; x += major) {
        ctx.beginPath();
        ctx.moveTo(x, 0);
        ctx.lineTo(x, height);
        ctx.stroke();
      }
      for (let y = 0; y <= height; y += major) {
        ctx.beginPath();
        ctx.moveTo(0, y);
        ctx.lineTo(width, y);
        ctx.stroke();
      }

      ctx.strokeStyle = 'rgba(255,255,255,0.012)';
      for (let x = 0; x <= width; x += minor) {
        ctx.beginPath();
        ctx.moveTo(x, 0);
        ctx.lineTo(x, height);
        ctx.stroke();
      }
      for (let y = 0; y <= height; y += minor) {
        ctx.beginPath();
        ctx.moveTo(0, y);
        ctx.lineTo(width, y);
        ctx.stroke();
      }
      ctx.restore();
    };

    const drawNodes = (reducedMotion: boolean) => {
      const nodes = nodesRef.current;

      for (let index = 0; index < nodes.length; index += 1) {
        const node = nodes[index];

        if (!reducedMotion) {
          node.x += node.vx;
          node.y += node.vy;

          if (node.x <= -20 || node.x >= width + 20) {
            node.vx *= -1;
          }
          if (node.y <= -20 || node.y >= height + 20) {
            node.vy *= -1;
          }
        }

        ctx.beginPath();
        ctx.fillStyle = node.tier === 'primary'
          ? `rgba(255, 116, 24, ${node.alpha})`
          : `rgba(173, 181, 189, ${node.alpha * 0.4})`;
        ctx.arc(node.x, node.y, node.radius, 0, Math.PI * 2);
        ctx.fill();

        if (node.tier === 'primary') {
          ctx.beginPath();
          ctx.strokeStyle = 'rgba(255, 116, 24, 0.18)';
          ctx.lineWidth = 1;
          ctx.arc(node.x, node.y, node.radius * 6, 0, Math.PI * 2);
          ctx.stroke();
        }
      }

      for (let a = 0; a < nodes.length; a += 1) {
        const nodeA = nodes[a];
        for (let b = a + 1; b < nodes.length; b += 1) {
          const nodeB = nodes[b];
          const dx = nodeA.x - nodeB.x;
          const dy = nodeA.y - nodeB.y;
          const distance = Math.sqrt(dx * dx + dy * dy);
          if (distance > spec.connectionDistance) {
            continue;
          }

          const alpha = (1 - distance / spec.connectionDistance) * (nodeA.tier === 'primary' || nodeB.tier === 'primary' ? 0.12 : 0.06);
          ctx.beginPath();
          ctx.strokeStyle = `rgba(255, 122, 47, ${alpha})`;
          ctx.lineWidth = 1;
          ctx.moveTo(nodeA.x, nodeA.y);
          ctx.lineTo(nodeB.x, nodeB.y);
          ctx.stroke();
        }
      }
    };

    const drawSweep = (reducedMotion: boolean) => {
      if (!reducedMotion) {
        sweep = (sweep + 0.0018) % 1;
      }

      const sweepX = width * sweep;
      const gradient = ctx.createLinearGradient(sweepX - 200, 0, sweepX + 140, height);
      gradient.addColorStop(0, 'rgba(255,116,24,0)');
      gradient.addColorStop(0.48, `rgba(255,116,24,${spec.sweepAlpha})`);
      gradient.addColorStop(0.52, 'rgba(255,255,255,0.04)');
      gradient.addColorStop(1, 'rgba(255,116,24,0)');

      ctx.save();
      ctx.globalCompositeOperation = 'screen';
      ctx.fillStyle = gradient;
      ctx.fillRect(0, 0, width, height);
      ctx.restore();
    };

    const drawCornerBloom = () => {
      const bloom = ctx.createRadialGradient(width * 0.82, height * 0.08, 0, width * 0.82, height * 0.08, width * 0.35);
      bloom.addColorStop(0, 'rgba(255, 116, 24, 0.16)');
      bloom.addColorStop(0.38, 'rgba(255, 116, 24, 0.08)');
      bloom.addColorStop(1, 'rgba(255, 116, 24, 0)');
      ctx.fillStyle = bloom;
      ctx.fillRect(0, 0, width, height);

      const lowerBloom = ctx.createRadialGradient(width * 0.18, height * 0.9, 0, width * 0.18, height * 0.9, width * 0.28);
      lowerBloom.addColorStop(0, 'rgba(255, 69, 0, 0.12)');
      lowerBloom.addColorStop(0.35, 'rgba(255, 69, 0, 0.04)');
      lowerBloom.addColorStop(1, 'rgba(255, 69, 0, 0)');
      ctx.fillStyle = lowerBloom;
      ctx.fillRect(0, 0, width, height);
    };

    const render = () => {
      const reducedMotion = mediaQuery.matches;

      ctx.clearRect(0, 0, width, height);
      drawCornerBloom();
      drawGrid();
      drawNodes(reducedMotion);
      drawSweep(reducedMotion);

      frameRef.current = window.requestAnimationFrame(render);
    };

    setCanvasSize();
    render();

    const handleResize = () => setCanvasSize();
    window.addEventListener('resize', handleResize);
    mediaQuery.addEventListener?.('change', handleResize);

    return () => {
      window.removeEventListener('resize', handleResize);
      mediaQuery.removeEventListener?.('change', handleResize);
      if (frameRef.current !== null) {
        window.cancelAnimationFrame(frameRef.current);
      }
    };
  }, [intensity, mode, spec.connectionDistance, spec.sweepAlpha]);

  return (
    <div className={cn('absolute inset-0 overflow-hidden pointer-events-none', className)} aria-hidden="true">
      <canvas
        ref={canvasRef}
        className="absolute inset-0 h-full w-full opacity-[0.9]"
      />
      <div className="absolute inset-0 bg-[radial-gradient(circle_at_top,rgba(255,133,51,0.08),transparent_30%),linear-gradient(180deg,rgba(4,6,10,0.08),rgba(4,6,10,0.4))]" />
      <div className="absolute inset-0 bg-[repeating-linear-gradient(180deg,rgba(255,255,255,0.015)_0px,rgba(255,255,255,0.015)_1px,transparent_1px,transparent_6px)] opacity-[0.22]" />
      <div className="absolute inset-x-0 top-0 h-px bg-[linear-gradient(90deg,transparent,rgba(255,122,47,0.45),transparent)]" />
      <div className="absolute inset-y-0 right-0 w-px bg-[linear-gradient(180deg,transparent,rgba(255,122,47,0.2),transparent)]" />
    </div>
  );
}
