import React, { useEffect, useRef } from 'react';

interface Node3D {
  x: number;
  y: number;
  z: number;
  baseRadius: number;
  pulsePhase: number;
}

interface Connection {
  from: number;
  to: number;
  strength: number;
}

export const NeuralCoreVisualizer: React.FC = () => {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const containerRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    const container = containerRef.current;
    if (!canvas || !container) return;

    const ctx = canvas.getContext('2d', { alpha: true });
    if (!ctx) return;

    const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

    // Generate 3D unit spherical neural node lattice (normalized on unit sphere)
    const nodes: Node3D[] = [];
    const connections: Connection[] = [];
    const nodeCount = 52;

    // Fibonacci sphere distribution for uniform 3D sphere distribution
    const phi = Math.PI * (3 - Math.sqrt(5));

    for (let i = 0; i < nodeCount; i++) {
      const y = 1 - (i / (nodeCount - 1)) * 2;
      const radiusAtY = Math.sqrt(Math.max(0, 1 - y * y));
      const theta = phi * i;

      const x = Math.cos(theta) * radiusAtY;
      const z = Math.sin(theta) * radiusAtY;

      nodes.push({
        x,
        y,
        z,
        baseRadius: 2.2 + Math.random() * 2.2,
        pulsePhase: Math.random() * Math.PI * 2,
      });
    }

    // Connect proximate nodes based on unit distance (0.613 on unit sphere corresponds to ~95px at r=155)
    for (let i = 0; i < nodes.length; i++) {
      let neighborCount = 0;
      for (let j = i + 1; j < nodes.length; j++) {
        const dx = nodes[i].x - nodes[j].x;
        const dy = nodes[i].y - nodes[j].y;
        const dz = nodes[i].z - nodes[j].z;
        const unitDist = Math.sqrt(dx * dx + dy * dy + dz * dz);

        if (unitDist < 0.613 && neighborCount < 3) {
          connections.push({
            from: i,
            to: j,
            strength: Math.max(0.2, 1 - unitDist / 0.613),
          });
          neighborCount++;
        }
      }
    }

    let animationFrameId: number;
    let angleX = 0.2;
    let angleY = 0;
    let velX = 0;
    let velY = 0;
    let targetParallaxX = 0;
    let targetParallaxY = 0;
    let currentParallaxX = 0;
    let currentParallaxY = 0;
    let isVisible = true;

    // Interaction tracking (mouse & touch drag with inertia)
    let isMouseDown = false;
    let lastPointerX = 0;
    let lastPointerY = 0;
    let touchId: number | null = null;
    let touchStartX = 0;
    let touchStartY = 0;
    let isTouchInteracting = false;
    let isTouchScrolling = false;

    const handleResize = () => {
      const rect = container.getBoundingClientRect();
      const dpr = Math.min(window.devicePixelRatio || 1, 2);
      canvas.width = Math.round(rect.width * dpr);
      canvas.height = Math.round(rect.height * dpr);
      canvas.style.width = `${rect.width}px`;
      canvas.style.height = `${rect.height}px`;
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    };

    handleResize();
    const resizeObserver = new ResizeObserver(handleResize);
    resizeObserver.observe(container);

    // Mouse drag & hover parallax tilt
    const handleMouseDown = (e: MouseEvent) => {
      if (e.button !== 0) return;
      isMouseDown = true;
      lastPointerX = e.clientX;
      lastPointerY = e.clientY;
      velX = 0;
      velY = 0;
    };

    const handleMouseMove = (e: MouseEvent) => {
      if (isMouseDown) {
        const dx = e.clientX - lastPointerX;
        const dy = e.clientY - lastPointerY;
        lastPointerX = e.clientX;
        lastPointerY = e.clientY;

        angleY += dx * 0.007;
        angleX = Math.max(-1.2, Math.min(1.2, angleX + dy * 0.007));

        velY = dx * 0.007;
        velX = dy * 0.007;
      } else {
        const rect = container.getBoundingClientRect();
        const cx = rect.left + rect.width / 2;
        const cy = rect.top + rect.height / 2;
        const nx = (e.clientX - cx) / (rect.width / 2);
        const ny = (e.clientY - cy) / (rect.height / 2);

        targetParallaxY = nx * 0.35;
        targetParallaxX = -ny * 0.35;
      }
    };

    const handleMouseUp = () => {
      isMouseDown = false;
    };

    const handleMouseLeave = () => {
      targetParallaxX = 0;
      targetParallaxY = 0;
    };

    canvas.addEventListener('mousedown', handleMouseDown);
    window.addEventListener('mousemove', handleMouseMove, { passive: true });
    window.addEventListener('mouseup', handleMouseUp, { passive: true });
    container.addEventListener('mouseleave', handleMouseLeave);

    // Touch gesture support with scroll preservation
    const handleTouchStart = (e: TouchEvent) => {
      if (e.touches.length !== 1) return;
      const touch = e.touches[0];
      touchId = touch.identifier;
      lastPointerX = touch.clientX;
      lastPointerY = touch.clientY;
      touchStartX = touch.clientX;
      touchStartY = touch.clientY;
      isTouchInteracting = false;
      isTouchScrolling = false;
      velX = 0;
      velY = 0;
    };

    const handleTouchMove = (e: TouchEvent) => {
      if (touchId === null) return;
      const touch = Array.from(e.changedTouches).find(t => t.identifier === touchId);
      if (!touch) return;

      const dx = touch.clientX - lastPointerX;
      const dy = touch.clientY - lastPointerY;
      const totalDx = touch.clientX - touchStartX;
      const totalDy = touch.clientY - touchStartY;

      if (!isTouchInteracting && !isTouchScrolling) {
        // If initial movement is predominantly vertical, yield to native page scroll
        if (Math.abs(totalDy) > Math.abs(totalDx) * 1.5 && Math.abs(totalDy) > 8) {
          isTouchScrolling = true;
          return;
        }
        // When user drags horizontally or engages 3D model, take over gesture
        if (Math.hypot(totalDx, totalDy) > 6) {
          isTouchInteracting = true;
        }
      }

      if (isTouchInteracting) {
        if (e.cancelable) {
          e.preventDefault();
        }

        lastPointerX = touch.clientX;
        lastPointerY = touch.clientY;

        angleY += dx * 0.007;
        angleX = Math.max(-1.2, Math.min(1.2, angleX + dy * 0.007));

        velY = dx * 0.007;
        velX = dy * 0.007;
      }
    };

    const handleTouchEnd = (e: TouchEvent) => {
      if (touchId === null) return;
      const touch = Array.from(e.changedTouches).find(t => t.identifier === touchId);
      if (touch) {
        touchId = null;
        isTouchInteracting = false;
        isTouchScrolling = false;
      }
    };

    canvas.addEventListener('touchstart', handleTouchStart, { passive: true });
    window.addEventListener('touchmove', handleTouchMove, { passive: false });
    window.addEventListener('touchend', handleTouchEnd, { passive: true });
    window.addEventListener('touchcancel', handleTouchEnd, { passive: true });

    const intersectionObserver = new IntersectionObserver(([entry]) => {
      isVisible = entry.isIntersecting;
    }, { threshold: 0.05 });
    intersectionObserver.observe(container);

    const render = (time: number) => {
      if (!isVisible) {
        animationFrameId = requestAnimationFrame(render);
        return;
      }

      const isActivelyDragging = isMouseDown || isTouchInteracting;

      if (!isActivelyDragging) {
        // Inertia damping from manual drag or touch flick
        if (Math.abs(velX) > 0.0001 || Math.abs(velY) > 0.0001) {
          angleX += velX;
          angleY += velY;
          velX *= 0.92;
          velY *= 0.92;
          angleX = Math.max(-1.2, Math.min(1.2, angleX));
        } else {
          velX = 0;
          velY = 0;
        }

        if (!prefersReducedMotion) {
          // Ambient slow rotation when idle
          if (velX === 0 && velY === 0) {
            angleY += 0.006;

            // Smooth parallax easing
            currentParallaxX += (targetParallaxX - currentParallaxX) * 0.05;
            currentParallaxY += (targetParallaxY - currentParallaxY) * 0.05;

            const restingAngleX = 0.2 + currentParallaxX;
            angleX += (restingAngleX - angleX) * 0.03;
            angleY += currentParallaxY * 0.008;
          }
        }
      }

      const dpr = Math.min(window.devicePixelRatio || 1, 2);
      const width = canvas.width / dpr;
      const height = canvas.height / dpr;

      if (width <= 0 || height <= 0) {
        animationFrameId = requestAnimationFrame(render);
        return;
      }

      const centerX = width / 2;
      const centerY = height / 2;

      // Dynamic scaling for zero clipping across mobile, tablet, desktop, and ultrawide displays
      // Clamped with a floor of ~95px on small phones and smoothly scaling up to ~250px on 2K/4K/ultrawide displays
      const sphereRadius = Math.max(95, Math.min(width * 0.35, height * 0.36, 250));
      const scale = sphereRadius / 155;
      const fov = 380;

      ctx.clearRect(0, 0, width, height);

      const cosY = Math.cos(angleY);
      const sinY = Math.sin(angleY);
      const cosX = Math.cos(angleX);
      const sinX = Math.sin(angleX);

      // 3D coordinate transformation & perspective projection
      const projectedNodes = nodes.map((node, i) => {
        const nx = node.x * sphereRadius;
        const ny = node.y * sphereRadius;
        const nz = node.z * sphereRadius;

        const x1 = nx * cosY - nz * sinY;
        const z1 = nz * cosY + nx * sinY;

        const y2 = ny * cosX - z1 * sinX;
        const z2 = z1 * cosX + ny * sinX;

        const depth = fov / (fov + z2 + 200 * scale);
        const px = centerX + x1 * depth;
        const py = centerY + y2 * depth;
        const radius = Math.max(0.8, node.baseRadius * scale * depth * 1.4);
        const alpha = Math.max(0.12, Math.min(1, (z2 + sphereRadius) / (2 * sphereRadius)));
        const pulse = Math.sin(time * 0.003 + node.pulsePhase) * 0.5 + 0.5;

        return { px, py, z2, radius, alpha, pulse, originalIndex: i };
      });

      // Detect theme for adaptive particle contrast
      const isDark = document.documentElement.classList.contains('dark');

      // Soft ambient organic glow centered behind the 3D model (no box edges, 100% transparent at perimeter)
      const glowRadius = sphereRadius * 1.45;
      const radialGlow = ctx.createRadialGradient(
        centerX,
        centerY,
        15 * scale,
        centerX,
        centerY,
        glowRadius
      );
      if (isDark) {
        radialGlow.addColorStop(0, 'rgba(6, 182, 212, 0.22)');
        radialGlow.addColorStop(0.45, 'rgba(46, 49, 146, 0.10)');
        radialGlow.addColorStop(1, 'rgba(0, 0, 0, 0)');
      } else {
        radialGlow.addColorStop(0, 'rgba(6, 182, 212, 0.16)');
        radialGlow.addColorStop(0.45, 'rgba(14, 165, 233, 0.06)');
        radialGlow.addColorStop(1, 'rgba(255, 255, 255, 0)');
      }
      ctx.fillStyle = radialGlow;
      ctx.fillRect(0, 0, width, height);

      // Subtle holographic orbital ring (scaled proportionally to avoid horizontal clipping)
      ctx.save();
      ctx.beginPath();
      ctx.ellipse(
        centerX,
        centerY,
        sphereRadius * 1.35,
        sphereRadius * 0.38,
        angleY * 0.5,
        0,
        Math.PI * 2
      );
      ctx.strokeStyle = isDark ? 'rgba(6, 182, 212, 0.20)' : 'rgba(8, 145, 178, 0.25)';
      ctx.lineWidth = Math.max(0.8, 1.2 * scale);
      ctx.setLineDash([Math.max(4, 6 * scale), Math.max(8, 14 * scale)]);
      ctx.stroke();
      ctx.restore();

      // Connections with pulsing neural sparks (direct index access O(1) for high FPS)
      connections.forEach(({ from, to, strength }) => {
        const p1 = projectedNodes[from];
        const p2 = projectedNodes[to];
        if (!p1 || !p2) return;

        const avgAlpha = (p1.alpha + p2.alpha) / 2;
        const lineAlpha = avgAlpha * strength * (isDark ? 0.65 : 0.45);

        ctx.beginPath();
        ctx.moveTo(p1.px, p1.py);
        ctx.lineTo(p2.px, p2.py);
        ctx.strokeStyle = isDark ? `rgba(34, 211, 238, ${lineAlpha})` : `rgba(8, 145, 178, ${lineAlpha})`;
        ctx.lineWidth = Math.max(0.5, strength * 1.6 * avgAlpha * scale);
        ctx.stroke();

        // Pulsing spark on connection
        const t = (Math.sin(time * 0.002 + from * 0.7) + 1) / 2;
        const packetX = p1.px + (p2.px - p1.px) * t;
        const packetY = p1.py + (p2.py - p1.py) * t;

        ctx.beginPath();
        ctx.arc(packetX, packetY, Math.max(1, 1.5 * scale), 0, Math.PI * 2);
        ctx.fillStyle = isDark ? `rgba(255, 255, 255, ${avgAlpha * 0.95})` : `rgba(8, 145, 178, ${avgAlpha * 0.95})`;
        ctx.fill();
      });

      // Render nodes sorted by depth for correct 3D occlusion
      const sortedNodes = [...projectedNodes].sort((a, b) => a.z2 - b.z2);
      sortedNodes.forEach(({ px, py, radius, alpha, pulse }) => {
        ctx.beginPath();
        ctx.arc(px, py, radius + pulse * 2.8 * scale, 0, Math.PI * 2);
        ctx.fillStyle = isDark ? `rgba(6, 182, 212, ${alpha * 0.35})` : `rgba(8, 145, 178, ${alpha * 0.25})`;
        ctx.fill();

        ctx.beginPath();
        ctx.arc(px, py, radius, 0, Math.PI * 2);
        ctx.fillStyle = isDark ? `rgba(224, 242, 254, ${alpha * 0.95})` : `rgba(15, 23, 42, ${alpha * 0.95})`;
        ctx.fill();
      });

      animationFrameId = requestAnimationFrame(render);
    };

    animationFrameId = requestAnimationFrame(render);

    return () => {
      cancelAnimationFrame(animationFrameId);
      canvas.removeEventListener('mousedown', handleMouseDown);
      window.removeEventListener('mousemove', handleMouseMove);
      window.removeEventListener('mouseup', handleMouseUp);
      container.removeEventListener('mouseleave', handleMouseLeave);
      canvas.removeEventListener('touchstart', handleTouchStart);
      window.removeEventListener('touchmove', handleTouchMove);
      window.removeEventListener('touchend', handleTouchEnd);
      window.removeEventListener('touchcancel', handleTouchEnd);
      resizeObserver.disconnect();
      intersectionObserver.disconnect();
    };
  }, []);

  return (
    <div 
      ref={containerRef} 
      className="relative w-full h-[320px] sm:h-[420px] md:h-[500px] lg:h-[580px] xl:h-[680px] 2xl:h-[760px] flex items-center justify-center pointer-events-auto select-none"
      role="img"
      aria-label="Interactive 3D visualization"
    >
      <canvas 
        ref={canvasRef} 
        className="absolute inset-0 w-full h-full cursor-grab active:cursor-grabbing select-none" 
      />
    </div>
  );
};
