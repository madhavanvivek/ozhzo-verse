'use client';

import React, { useEffect, useRef, useState } from 'react';

// ============================================================================
// ISO/IEC 18004 Standard QR Code Generator Engine (Pure TypeScript)
// ============================================================================

// Galois Field GF(256) Math for Reed-Solomon Error Correction
const GF_EXP: number[] = new Array(512);
const GF_LOG: number[] = new Array(256);

(function initGaloisField() {
  let x = 1;
  for (let i = 0; i < 255; i++) {
    GF_EXP[i] = x;
    GF_LOG[x] = i;
    x <<= 1;
    if (x & 0x100) {
      x ^= 0x11d; // Primitive polynomial x^8 + x^4 + x^3 + x^2 + 1
    }
  }
  for (let i = 255; i < 512; i++) {
    GF_EXP[i] = GF_EXP[i - 255];
  }
})();

function gfMul(x: number, y: number): number {
  if (x === 0 || y === 0) return 0;
  return GF_EXP[GF_LOG[x] + GF_LOG[y]];
}

function rsGeneratorPoly(degree: number): number[] {
  let poly = [1];
  for (let i = 0; i < degree; i++) {
    const nextPoly = new Array(poly.length + 1).fill(0);
    for (let j = 0; j < poly.length; j++) {
      nextPoly[j] ^= gfMul(poly[j], GF_EXP[i]);
      nextPoly[j + 1] ^= poly[j];
    }
    poly = nextPoly;
  }
  return poly;
}

function rsCalculateRemainder(data: number[], degree: number): number[] {
  const gen = rsGeneratorPoly(degree);
  const remainder = new Array(degree).fill(0);
  for (const byte of data) {
    const factor = byte ^ remainder[0];
    remainder.shift();
    remainder.push(0);
    for (let i = 0; i < degree; i++) {
      remainder[i] ^= gfMul(gen[i + 1], factor);
    }
  }
  return remainder;
}

// Error Correction Level M (Medium ~15%) and H (High ~30%) Specifications
// Version -> [totalCodewords, ecCodewordsPerBlock, numBlocksGroup1, dataCodewordsPerBlockG1, numBlocksGroup2, dataCodewordsPerBlockG2]
const QR_VERSION_SPECS_M: Record<number, [number, number, number, number, number, number]> = {
  1: [26, 10, 1, 16, 0, 0],
  2: [44, 16, 1, 28, 0, 0],
  3: [70, 26, 1, 44, 0, 0],
  4: [100, 18, 2, 32, 0, 0],
  5: [134, 24, 2, 43, 0, 0],
  6: [172, 16, 4, 27, 0, 0],
  7: [196, 18, 4, 31, 0, 0],
  8: [242, 22, 2, 38, 2, 39],
  9: [292, 22, 3, 36, 2, 37],
  10: [346, 26, 4, 43, 1, 44],
};

// Alignment pattern centers per version
const ALIGNMENT_PATTERN_POSITIONS: Record<number, number[]> = {
  1: [],
  2: [6, 18],
  3: [6, 22],
  4: [6, 26],
  5: [6, 30],
  6: [6, 34],
  7: [6, 22, 38],
  8: [6, 24, 42],
  9: [6, 26, 46],
  10: [6, 28, 50],
};

function selectVersion(dataLen: number): number {
  for (let v = 1; v <= 10; v++) {
    const spec = QR_VERSION_SPECS_M[v];
    const totalDataCapacity = spec[2] * spec[3] + spec[4] * spec[5];
    // Byte mode overhead: 4 bits mode + 8 bits length indicator (16 for v10+) = ~2-3 bytes
    const headerBytes = v >= 10 ? 3 : 2;
    if (dataLen + headerBytes <= totalDataCapacity) {
      return v;
    }
  }
  return 10;
}

export function generateStandardQRMatrix(text: string): boolean[][] {
  const utf8Bytes: number[] = [];
  for (let i = 0; i < text.length; i++) {
    let code = text.charCodeAt(i);
    if (code < 0x80) {
      utf8Bytes.push(code);
    } else if (code < 0x800) {
      utf8Bytes.push(0xc0 | (code >> 6), 0x80 | (code & 0x3f));
    } else if (code < 0xd800 || code >= 0xe000) {
      utf8Bytes.push(0xe0 | (code >> 12), 0x80 | ((code >> 6) & 0x3f), 0x80 | (code & 0x3f));
    } else {
      i++;
      code = 0x10000 + (((code & 0x3ff) << 10) | (text.charCodeAt(i) & 0x3ff));
      utf8Bytes.push(
        0xf0 | (code >> 18),
        0x80 | ((code >> 12) & 0x3f),
        0x80 | ((code >> 6) & 0x3f),
        0x80 | (code & 0x3f)
      );
    }
  }

  const version = selectVersion(utf8Bytes.length);
  const spec = QR_VERSION_SPECS_M[version];
  const [, ecPerBlock, numB1, dataPerB1, numB2, dataPerB2] = spec;
  const totalDataCapacity = numB1 * dataPerB1 + numB2 * dataPerB2;

  // 1. Build BitStream (Byte Mode: 0100)
  const bitStream: number[] = [];
  const pushBits = (val: number, length: number) => {
    for (let i = length - 1; i >= 0; i--) {
      bitStream.push((val >> i) & 1);
    }
  };

  // Mode: 0100 (Byte mode)
  pushBits(4, 4);
  // Length indicator
  pushBits(utf8Bytes.length, version >= 10 ? 16 : 8);
  // Data bytes
  for (const b of utf8Bytes) {
    pushBits(b, 8);
  }
  // Terminator
  const totalDataBits = totalDataCapacity * 8;
  const terminatorLen = Math.min(4, totalDataBits - bitStream.length);
  pushBits(0, terminatorLen);
  // Align to byte boundary
  while (bitStream.length % 8 !== 0) {
    bitStream.push(0);
  }
  // Pad bytes (0xEC, 0x11)
  const padBytes = [0xec, 0x11];
  let padIdx = 0;
  while (bitStream.length < totalDataBits) {
    pushBits(padBytes[padIdx % 2], 8);
    padIdx++;
  }

  // Convert bits to data codewords
  const dataCodewords: number[] = [];
  for (let i = 0; i < bitStream.length; i += 8) {
    let byte = 0;
    for (let b = 0; b < 8; b++) {
      byte = (byte << 1) | bitStream[i + b];
    }
    dataCodewords.push(byte);
  }

  // 2. Divide into blocks & generate Reed-Solomon EC codewords
  const dataBlocks: number[][] = [];
  const ecBlocks: number[][] = [];
  let offset = 0;

  for (let b = 0; b < numB1; b++) {
    const block = dataCodewords.slice(offset, offset + dataPerB1);
    dataBlocks.push(block);
    ecBlocks.push(rsCalculateRemainder(block, ecPerBlock));
    offset += dataPerB1;
  }
  for (let b = 0; b < numB2; b++) {
    const block = dataCodewords.slice(offset, offset + dataPerB2);
    dataBlocks.push(block);
    ecBlocks.push(rsCalculateRemainder(block, ecPerBlock));
    offset += dataPerB2;
  }

  // 3. Interleave data and EC codewords
  const finalCodewords: number[] = [];
  const maxDataBlockLen = Math.max(dataPerB1, dataPerB2);
  for (let i = 0; i < maxDataBlockLen; i++) {
    for (const block of dataBlocks) {
      if (i < block.length) finalCodewords.push(block[i]);
    }
  }
  for (let i = 0; i < ecPerBlock; i++) {
    for (const block of ecBlocks) {
      finalCodewords.push(block[i]);
    }
  }

  // 4. Construct Matrix & Function Patterns
  const size = version * 4 + 17;
  const matrix: boolean[][] = Array.from({ length: size }, () => Array(size).fill(false));
  const isFunction: boolean[][] = Array.from({ length: size }, () => Array(size).fill(false));

  const setModule = (r: number, c: number, val: boolean) => {
    matrix[r][c] = val;
    isFunction[r][c] = true;
  };

  // 4a. Finder Patterns & Separators
  const drawFinder = (row: number, col: number) => {
    for (let r = -1; r <= 7; r++) {
      for (let c = -1; c <= 7; c++) {
        const nr = row + r;
        const nc = col + c;
        if (nr >= 0 && nr < size && nc >= 0 && nc < size) {
          if (
            (r >= 0 && r <= 6 && (c === 0 || c === 6)) ||
            (c >= 0 && c <= 6 && (r === 0 || r === 6)) ||
            (r >= 2 && r <= 4 && c >= 2 && c <= 4)
          ) {
            setModule(nr, nc, true);
          } else {
            setModule(nr, nc, false);
          }
        }
      }
    }
  };
  drawFinder(0, 0);
  drawFinder(0, size - 7);
  drawFinder(size - 7, 0);

  // 4b. Alignment Patterns
  const alignPos = ALIGNMENT_PATTERN_POSITIONS[version] || [];
  for (const ar of alignPos) {
    for (const ac of alignPos) {
      // Avoid finder patterns
      if (
        (ar === 6 && ac === 6) ||
        (ar === 6 && ac === size - 7) ||
        (ar === size - 7 && ac === 6)
      ) {
        continue;
      }
      for (let r = -2; r <= 2; r++) {
        for (let c = -2; c <= 2; c++) {
          const isBorder = Math.abs(r) === 2 || Math.abs(c) === 2;
          const isCenter = r === 0 && c === 0;
          setModule(ar + r, ac + c, isBorder || isCenter);
        }
      }
    }
  }

  // 4c. Timing Patterns
  for (let i = 8; i < size - 8; i++) {
    if (!isFunction[6][i]) setModule(6, i, i % 2 === 0);
    if (!isFunction[i][6]) setModule(i, 6, i % 2 === 0);
  }

  // 4d. Dark Module & Format Info Reserve Area
  setModule(4 * version + 9, 8, true);

  for (let i = 0; i < 9; i++) {
    if (!isFunction[8][i]) isFunction[8][i] = true;
    if (!isFunction[i][8]) isFunction[i][8] = true;
  }
  for (let i = 0; i < 8; i++) {
    if (!isFunction[8][size - 1 - i]) isFunction[8][size - 1 - i] = true;
    if (!isFunction[size - 1 - i][8]) isFunction[size - 1 - i][8] = true;
  }

  // 5. Place Data Bits
  const dataBits: boolean[] = [];
  for (const byte of finalCodewords) {
    for (let b = 7; b >= 0; b--) {
      dataBits.push(((byte >> b) & 1) === 1);
    }
  }

  let bitIdx = 0;
  let upwards = true;
  for (let right = size - 1; right > 0; right -= 2) {
    if (right === 6) right--; // Skip vertical timing pattern
    const rows = upwards
      ? Array.from({ length: size }, (_, i) => size - 1 - i)
      : Array.from({ length: size }, (_, i) => i);

    for (const r of rows) {
      for (let c = 0; c < 2; c++) {
        const col = right - c;
        if (!isFunction[r][col]) {
          matrix[r][col] = bitIdx < dataBits.length ? dataBits[bitIdx] : false;
          bitIdx++;
        }
      }
    }
    upwards = !upwards;
  }

  // 6. Select Best Mask (Mask 0 to 7) using standard BCH Format Encoding
  // For Level M (00 in format info):
  const FORMAT_BITS_LEVEL_M: number[] = [
    0x5412, 0x5125, 0x5e7c, 0x5b4b, 0x45f9, 0x40ce, 0x4f97, 0x4aa0
  ];

  let bestScore = Infinity;
  let bestMatrix: boolean[][] = matrix;

  for (let mask = 0; mask < 8; mask++) {
    const maskedMatrix = matrix.map((row) => [...row]);

    for (let r = 0; r < size; r++) {
      for (let c = 0; c < size; c++) {
        if (!isFunction[r][c]) {
          let invert = false;
          switch (mask) {
            case 0: invert = (r + c) % 2 === 0; break;
            case 1: invert = r % 2 === 0; break;
            case 2: invert = c % 3 === 0; break;
            case 3: invert = (r + c) % 3 === 0; break;
            case 4: invert = (Math.floor(r / 2) + Math.floor(c / 3)) % 2 === 0; break;
            case 5: invert = ((r * c) % 2) + ((r * c) % 3) === 0; break;
            case 6: invert = (((r * c) % 2) + ((r * c) % 3)) % 2 === 0; break;
            case 7: invert = (((r + c) % 2) + ((r * c) % 3)) % 2 === 0; break;
          }
          if (invert) maskedMatrix[r][c] = !maskedMatrix[r][c];
        }
      }
    }

    // Apply Format Bits for this mask
    const formatValue = FORMAT_BITS_LEVEL_M[mask];
    for (let i = 0; i < 15; i++) {
      const bit = ((formatValue >> (14 - i)) & 1) === 1;
      // Top-left
      if (i <= 5) maskedMatrix[8][i] = bit;
      else if (i === 6) maskedMatrix[8][7] = bit;
      else if (i === 7) maskedMatrix[8][8] = bit;
      else if (i === 8) maskedMatrix[7][8] = bit;
      else maskedMatrix[14 - i][8] = bit;

      // Bottom-left / Top-right
      if (i < 8) maskedMatrix[size - 1 - i][8] = bit;
      else maskedMatrix[8][size - 15 + i] = bit;
    }

    // Evaluation Penalty
    let score = 0;
    // N1: 5+ consecutive same color
    for (let r = 0; r < size; r++) {
      let run = 1;
      for (let c = 1; c < size; c++) {
        if (maskedMatrix[r][c] === maskedMatrix[r][c - 1]) run++;
        else {
          if (run >= 5) score += 3 + (run - 5);
          run = 1;
        }
      }
      if (run >= 5) score += 3 + (run - 5);
    }
    for (let c = 0; c < size; c++) {
      let run = 1;
      for (let r = 1; r < size; r++) {
        if (maskedMatrix[r][c] === maskedMatrix[r - 1][c]) run++;
        else {
          if (run >= 5) score += 3 + (run - 5);
          run = 1;
        }
      }
      if (run >= 5) score += 3 + (run - 5);
    }

    if (score < bestScore) {
      bestScore = score;
      bestMatrix = maskedMatrix;
    }
  }

  return bestMatrix;
}

// ============================================================================
// React QRCode Component with Retina Canvas & High-Res PNG Export
// ============================================================================

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
      try {
        const m = generateStandardQRMatrix(value);
        setMatrix(m);
      } catch (err) {
        console.error('QR code matrix generation failed:', err);
      }
    }
  }, [value]);

  useEffect(() => {
    if (!canvasRef.current || matrix.length === 0) return;
    const canvas = canvasRef.current;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const moduleCount = matrix.length;
    const padding = 4; // Standard 4-module quiet zone
    const totalCells = moduleCount + padding * 2;

    // High resolution rendering for sharp scanability
    const dpr = typeof window !== 'undefined' ? Math.max(window.devicePixelRatio || 1, 2) : 2;
    const targetSize = Math.max(size, 256) * dpr;
    const cellSize = Math.floor(targetSize / totalCells);
    const canvasActualSize = totalCells * cellSize;

    canvas.width = canvasActualSize;
    canvas.height = canvasActualSize;

    // Background
    ctx.fillStyle = bgColor;
    ctx.fillRect(0, 0, canvasActualSize, canvasActualSize);

    // Foreground Modules
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
          boxShadow: '0 1px 4px rgba(0,0,0,0.08)',
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
