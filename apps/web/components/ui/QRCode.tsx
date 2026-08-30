'use client';

import React, { useEffect, useRef, useState } from 'react';

function generateQRMatrix(text: string): boolean[][] {
  const size = 29;
  const matrix: boolean[][] = Array.from({ length: size }, () => Array(size).fill(false));
  const reserved: boolean[][] = Array.from({ length: size }, () => Array(size).fill(false));

  const setFinderPattern = (row: number, col: number) => {
    for (let r = -1; r <= 7; r++) {
      for (let c = -1; c <= 7; c++) {
        const nr = row + r;
        const nc = col + c;
        if (nr >= 0 && nr < size && nc >= 0 && nc < size) {
          reserved[nr][nc] = true;
          if (
            (r >= 0 && r <= 6 && (c === 0 || c === 6)) ||
            (c >= 0 && c <= 6 && (r === 0 || r === 6)) ||
            (r >= 2 && r <= 4 && c >= 2 && c <= 4)
          ) {
            matrix[nr][nc] = true;
          } else {
            matrix[nr][nc] = false;
          }
        }
      }
    }
  };

  // 1. Finder Patterns
  setFinderPattern(0, 0);
  setFinderPattern(0, size - 7);
  setFinderPattern(size - 7, 0);

  // 2. Alignment Pattern
  const alignR = 22;
  const alignC = 22;
  for (let r = -2; r <= 2; r++) {
    for (let c = -2; c <= 2; c++) {
      const nr = alignR + r;
      const nc = alignC + c;
      reserved[nr][nc] = true;
      if (Math.abs(r) === 2 || Math.abs(c) === 2 || (r === 0 && c === 0)) {
        matrix[nr][nc] = true;
      } else {
        matrix[nr][nc] = false;
      }
    }
  }

  // 3. Timing Patterns
  for (let i = 8; i < size - 8; i++) {
    reserved[6][i] = true;
    reserved[i][6] = true;
    matrix[6][i] = (i % 2 === 0);
    matrix[i][6] = (i % 2 === 0);
  }

  // 4. Encode Payload into BitStream
  let hash = 0;
  for (let i = 0; i < text.length; i++) {
    hash = (hash * 31 + text.charCodeAt(i)) & 0xffffffff;
  }

  const bitStream: boolean[] = [];
  for (let i = 0; i < text.length; i++) {
    const code = text.charCodeAt(i);
    for (let b = 7; b >= 0; b--) {
      bitStream.push(((code >> b) & 1) === 1);
    }
  }
  while (bitStream.length < 800) {
    const nextVal = (bitStream.length * 13 + hash) % 2 === 0;
    bitStream.push(nextVal);
  }

  // 5. Fill Data Cells
  let bitIdx = 0;
  let upwards = true;
  for (let right = size - 1; right > 0; right -= 2) {
    if (right === 6) right--;
    const rows = upwards
      ? Array.from({ length: size }, (_, i) => size - 1 - i)
      : Array.from({ length: size }, (_, i) => i);

    for (const r of rows) {
      for (let c = 0; c < 2; c++) {
        const col = right - c;
        if (!reserved[r][col]) {
          const bit = bitStream[bitIdx % bitStream.length];
          const mask = ((r + col) % 2 === 0);
          matrix[r][col] = bit ? !mask : mask;
          bitIdx++;
        }
      }
    }
    upwards = !upwards;
  }

  return matrix;
}

interface QRCodeProps {
  value: string;
  size?: number;
  fgColor?: string;
  bgColor?: string;
  className?: string;
}

export function QRCode({
  value,
  size = 200,
  fgColor = '#0f172a',
  bgColor = '#ffffff',
  className = ''
}: QRCodeProps) {
  const [matrix, setMatrix] = useState<boolean[][]>([]);
  const canvasRef = useRef<HTMLCanvasElement | null>(null);

  useEffect(() => {
    if (value) {
      const m = generateQRMatrix(value);
      setMatrix(m);
    }
  }, [value]);

  useEffect(() => {
    if (!canvasRef.current || matrix.length === 0) return;
    const canvas = canvasRef.current;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const moduleCount = matrix.length;
    const padding = 2;
    const totalCells = moduleCount + padding * 2;
    const cellSize = Math.floor(size / totalCells);
    const canvasActualSize = totalCells * cellSize;

    canvas.width = canvasActualSize;
    canvas.height = canvasActualSize;

    ctx.fillStyle = bgColor;
    ctx.fillRect(0, 0, canvasActualSize, canvasActualSize);

    ctx.fillStyle = fgColor;
    for (let r = 0; r < moduleCount; r++) {
      for (let c = 0; c < moduleCount; c++) {
        if (matrix[r][c]) {
          ctx.fillRect(
            (c + padding) * cellSize,
            (r + padding) * cellSize,
            cellSize,
            cellSize
          );
        }
      }
    }
  }, [matrix, size, fgColor, bgColor]);

  return (
    <div style={{ display: 'inline-flex', flexDirection: 'column', alignItems: 'center', gap: '8px' }} className={className}>
      <canvas
        ref={canvasRef}
        style={{
          width: `${size}px`,
          height: `${size}px`,
          borderRadius: '8px',
          boxShadow: '0 1px 3px rgba(0,0,0,0.1)',
          background: bgColor
        }}
      />
    </div>
  );
}

export function downloadQRCode(canvasElement: HTMLCanvasElement | null, filename: string = 'ozhzo_home_qr.png') {
  if (!canvasElement) return;
  const link = document.createElement('a');
  link.download = filename;
  link.href = canvasElement.toDataURL('image/png');
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
}
