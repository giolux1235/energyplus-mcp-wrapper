#!/usr/bin/env node
/**
 * Comprehensive Local IDF Test - Multiple IDF Files with Iteration Tracking
 * Tests local IDF files, checks warnings, validates fixes
 * Tracks iterations and saves progress - reverts to best iteration when warnings increase
 */

import { readFileSync, writeFileSync, mkdirSync, existsSync, readdirSync, statSync } from 'fs';
import { join, basename, dirname } from 'path';
import { exec } from 'child_process';
import { promisify } from 'util';

const execAsync = promisify(exec);

const ENERGYPLUS_API_URL = process.env.ENERGYPLUS_API_URL || 'https://web-production-1d1be.up.railway.app/simulate';
const VAV_MIN_FLOW_SCHEDULE_NAME = 'VAV Minimum Flow Fraction Schedule';
const DEFAULT_VAV_DESIGN_FRACTION = 0.68;
let dynamicVavDesignFraction = null;

// Iteration tracking
const PROGRESS_FILE = join(process.cwd(), 'test_progress_local.json');
const ITERATIONS_DIR = join(process.cwd(), 'test_iterations_local');

// Ensure iterations directory exists
mkdirSync(ITERATIONS_DIR, { recursive: true });

// Directories to search for IDF files
const IDF_SEARCH_DIRS = [
  'EnergyPlus-MCP/energyplus-mcp-server/sample_files',
  'EnergyPlus-MCP/energyplus-mcp-server/illustrative examples',
  'ashrae901_examples',
  'nrel_testfiles',
  'sample_files'
];

// Directories to search for weather files
const WEATHER_SEARCH_DIRS = [
  'EnergyPlus-MCP/energyplus-mcp-server/sample_files',
  'EnergyPlus-MCP/energyplus-mcp-server/illustrative examples',
  'ashrae901_weather'
];

// Progress tracking functions
function loadProgress() {
  if (existsSync(PROGRESS_FILE)) {
    try {
      const content = readFileSync(PROGRESS_FILE, 'utf-8');
      return JSON.parse(content);
    } catch (error) {
      console.warn(`⚠️  Could not load progress file: ${error.message}`);
      return { iterations: [], best_iteration: null };
    }
  }
  return { iterations: [], best_iteration: null };
}

function saveProgress(progress) {
  writeFileSync(PROGRESS_FILE, JSON.stringify(progress, null, 2), 'utf-8');
}

async function getCurrentGitCommit() {
  try {
    const { stdout } = await execAsync('git rev-parse HEAD', { cwd: process.cwd() });
    return stdout.trim();
  } catch (error) {
    return 'local-files';
  }
}

async function getCurrentGitBranch() {
  try {
    const { stdout } = await execAsync('git rev-parse --abbrev-ref HEAD', { cwd: process.cwd() });
    return stdout.trim();
  } catch (error) {
    return 'local-files';
  }
}

// Find all IDF files in search directories
function findLocalIDFFiles() {
  const idfFiles = [];
  for (const dir of IDF_SEARCH_DIRS) {
    const fullPath = join(process.cwd(), dir);
    if (!existsSync(fullPath)) {
      continue;
    }
    try {
      const files = readdirSync(fullPath);
      for (const file of files) {
        if (file.toLowerCase().endsWith('.idf')) {
          const filePath = join(fullPath, file);
          try {
            const stats = statSync(filePath);
            if (stats.isFile()) {
              idfFiles.push(filePath);
            }
          } catch (e) {
            // Skip if can't stat
          }
        }
      }
    } catch (error) {
      // Skip directory if can't read
      continue;
    }
  }
  return idfFiles.sort();
}

// Find all weather files in search directories
function findLocalWeatherFiles() {
  const weatherFiles = [];
  for (const dir of WEATHER_SEARCH_DIRS) {
    const fullPath = join(process.cwd(), dir);
    if (!existsSync(fullPath)) {
      continue;
    }
    try {
      const files = readdirSync(fullPath);
      for (const file of files) {
        if (file.toLowerCase().endsWith('.epw')) {
          const filePath = join(fullPath, file);
          try {
            const stats = statSync(filePath);
            if (stats.isFile()) {
              weatherFiles.push(filePath);
            }
          } catch (e) {
            // Skip if can't stat
          }
        }
      }
    } catch (error) {
      // Skip directory if can't read
      continue;
    }
  }
  return weatherFiles.sort();
}

// Match IDF file with appropriate weather file
function matchWeatherFile(idfPath) {
  const idfName = basename(idfPath).toLowerCase();
  const weatherFiles = findLocalWeatherFiles();
  
  // Try to match by location name in filename (check most specific first)
  if (idfName.includes('san.francisco') || idfName.includes('sanfrancisco') || idfName.includes('sf')) {
    const sfWeather = weatherFiles.find(w => w.toLowerCase().includes('san.francisco') || w.toLowerCase().includes('sanfrancisco'));
    if (sfWeather) return sfWeather;
  }
  if (idfName.includes('denver') || idfName.includes('golden')) {
    const denverWeather = weatherFiles.find(w => w.toLowerCase().includes('denver') || w.toLowerCase().includes('golden'));
    if (denverWeather) return denverWeather;
  }
  if (idfName.includes('chicago')) {
    const chicagoWeather = weatherFiles.find(w => w.toLowerCase().includes('chicago'));
    if (chicagoWeather) return chicagoWeather;
  }
  
  // Default to first available weather file
  return weatherFiles[0] || null;
}

function calculateTotalWarnings(results) {
  // Only count warnings from successful tests - failed tests don't count for optimization
  return results.reduce((total, result) => {
    if (result.success) {
      return total + (result.warnings?.length || 0);
    }
    return total;
  }, 0);
}

function calculatePerTestWarnings(results) {
  return results.map(result => ({
    test_number: result.test_number,
    idf_name: result.idf_name,
    idf_path: result.idf_path,
    warning_count: result.warnings?.length || 0,
    error_count: result.errors?.length || 0,
    fatal: result.fatal || false
  }));
}

function saveIteration(iterationNumber, results, gitCommit, gitBranch) {
  const iterationData = {
    iteration: iterationNumber,
    timestamp: new Date().toISOString(),
    git_commit: gitCommit,
    git_branch: gitBranch,
    total_warnings: calculateTotalWarnings(results),
    per_test_warnings: calculatePerTestWarnings(results),
    results: results.map(r => ({
      test_number: r.test_number,
      idf_name: r.idf_name,
      idf_path: r.idf_path,
      success: r.success,
      warning_count: r.warnings?.length || 0,
      error_count: r.errors?.length || 0,
      fatal: r.fatal || false,
      eui: r.eui,
      issues: r.issues || [],
      warning_summary: r.warning_summary || []
    })),
    summary: {
      successful_tests: results.filter(r => r.success).length,
      total_tests: results.length,
      total_warnings: calculateTotalWarnings(results),
      total_errors: results.reduce((sum, r) => sum + (r.errors?.length || 0), 0),
      fatal_errors: results.filter(r => r.fatal).length
    }
  };
  
  const iterationFile = join(ITERATIONS_DIR, `iteration_${iterationNumber}.json`);
  writeFileSync(iterationFile, JSON.stringify(iterationData, null, 2), 'utf-8');
  
  return iterationData;
}

function findBestIteration(progress) {
  if (!progress.iterations || progress.iterations.length === 0) {
    return null;
  }
  
  // Sort by total warnings (ascending), then by fatal errors (ascending), then by total errors
  const sorted = [...progress.iterations].sort((a, b) => {
    if (a.total_warnings !== b.total_warnings) {
      return a.total_warnings - b.total_warnings;
    }
    const aFatal = a.summary?.fatal_errors || 0;
    const bFatal = b.summary?.fatal_errors || 0;
    if (aFatal !== bFatal) {
      return aFatal - bFatal;
    }
    const aErrors = a.summary?.total_errors || 0;
    const bErrors = b.summary?.total_errors || 0;
    return aErrors - bErrors;
  });
  
  return sorted[0];
}

function formatNumber(value, decimals = 4) {
  const num = Number.parseFloat(value);
  if (Number.isFinite(num)) {
    return num.toFixed(decimals);
  }
  return value;
}

function buildSiteLocationBlock(weatherContent) {
  if (!weatherContent) {
    return null;
  }
  const firstLine = weatherContent.split(/\r?\n/)[0]?.trim();
  if (!firstLine || !firstLine.toUpperCase().startsWith('LOCATION,')) {
    return null;
  }
  const parts = firstLine.split(',');
  if (parts.length < 10) {
    return null;
  }
  const [
    _locationTag,
    city = '',
    state = '',
    country = '',
    dataSource = '',
    wmo = '',
    latitude = '',
    longitude = '',
    timeZone = '',
    elevation = ''
  ] = parts;

  const name = `${city.trim()} ${state.trim()} ${country.trim()} ${dataSource.trim()} WMO#=${wmo.trim()}`.replace(/\s+/g, ' ').trim();

  return [
    'Site:Location,',
    `  ${name}, !- Name`,
    `  ${formatNumber(latitude, 4)},          !- Latitude {deg}`,
    `  ${formatNumber(longitude, 4)},         !- Longitude {deg}`,
    `  ${formatNumber(timeZone, 2)},         !- Time Zone {hr}`,
    `  ${formatNumber(elevation, 2)};         !- Elevation {m}`
  ].join('\n');
}

function postProcessIdf(idfContent, weatherContent) {
  let updatedContent = idfContent;

  // Normalize Site:Location to match weather file
  const siteLocationBlock = buildSiteLocationBlock(weatherContent);
  if (siteLocationBlock) {
    updatedContent = updatedContent.replace(/Site:Location,[\s\S]*?(?=\n\s*\n)/, `${siteLocationBlock}\n`);
  }

  return updatedContent;
}

function readWeatherFile(filePath) {
  // filePath can be absolute or relative
  if (!existsSync(filePath)) {
    const fullPath = join(process.cwd(), filePath);
    if (existsSync(fullPath)) {
      return readFileSync(fullPath, 'utf-8');
    }
    throw new Error(`Weather file not found: ${filePath}`);
  }
  return readFileSync(filePath, 'utf-8');
}

function readLocalIDF(idfPath) {
  // idfPath can be absolute or relative
  if (!existsSync(idfPath)) {
    const fullPath = join(process.cwd(), idfPath);
    if (existsSync(fullPath)) {
      return readFileSync(fullPath, 'utf-8');
    }
    throw new Error(`IDF file not found: ${idfPath}`);
  }
  return readFileSync(idfPath, 'utf-8');
}

function parseValueFromLine(line) {
  const lineNoComment = line.split('!-')[0];
  return lineNoComment.replace(/[,;]/g, '').trim();
}

function normalizeIdentifier(value) {
  return (value || '').toLowerCase().replace(/[^a-z0-9]/g, '');
}

function stripSuffixIgnoreCase(value, suffix) {
  if (!value || !suffix) return value || '';
  const lowerValue = value.toLowerCase();
  const lowerSuffix = suffix.toLowerCase();
  if (lowerValue.endsWith(lowerSuffix)) {
    return value.slice(0, value.length - suffix.length);
  }
  return value;
}

function parseVertexCoordinates(line) {
  const lineNoComment = line.split('!-')[0];
  const cleaned = lineNoComment.replace(/;/g, '').trim();
  if (!cleaned) {
    return null;
  }
  const parts = cleaned.split(',').map(part => parseFloat(part.trim()));
  if (parts.length < 3 || parts.some(number => Number.isNaN(number))) {
    return null;
  }
  return parts.slice(0, 3);
}

function vectorSubtract(a, b) {
  return [a[0] - b[0], a[1] - b[1], a[2] - b[2]];
}

function vectorCross(a, b) {
  return [
    a[1] * b[2] - a[2] * b[1],
    a[2] * b[0] - a[0] * b[2],
    a[0] * b[1] - a[1] * b[0]
  ];
}

function normaliseVector(vec) {
  const magnitude = Math.sqrt(vec[0] ** 2 + vec[1] ** 2 + vec[2] ** 2);
  if (magnitude === 0) {
    return null;
  }
  return vec.map(component => component / magnitude);
}

function computeNormalFromVertices(vertices) {
  if (!Array.isArray(vertices) || vertices.length < 3) {
    return null;
  }
  for (let i = 0; i < vertices.length - 2; i++) {
    const p0 = vertices[i];
    const p1 = vertices[i + 1];
    const p2 = vertices[i + 2];
    if (!p0 || !p1 || !p2) {
      continue;
    }
    const u = vectorSubtract(p1, p0);
    const v = vectorSubtract(p2, p1);
    const cross = vectorCross(u, v);
    const normal = normaliseVector(cross);
    if (normal) {
      return normal;
    }
  }
  return null;
}

function gatherBlock(lines, startIndex) {
  const indices = [];
  let idx = startIndex;
  while (idx < lines.length) {
    indices.push(idx);
    if (lines[idx].includes(';')) {
      break;
    }
    idx += 1;
  }
  return { indices, endIndex: idx };
}

function buildSurfaceNormalMap(lines) {
  const surfaceNormals = new Map();
  for (let i = 0; i < lines.length; i++) {
    if (!lines[i].trim().toUpperCase().startsWith('BUILDINGSURFACE:DETAILED')) {
      continue;
    }
    const { indices, endIndex } = gatherBlock(lines, i);
    const blockLines = indices.map(idx => lines[idx]);
    let surfaceName = null;
    const vertices = [];
    let fieldIndex = -1;
    for (let j = 1; j < blockLines.length; j++) {
      const line = blockLines[j];
      const trimmed = line.trim();
      if (!trimmed || trimmed.startsWith('!')) {
        continue;
      }
      if (line.toLowerCase().includes('!- vertex')) {
        const coords = parseVertexCoordinates(line);
        if (coords) {
          vertices.push(coords);
        }
        continue;
      }
      fieldIndex += 1;
      if (fieldIndex === 0) {
        surfaceName = parseValueFromLine(line);
      }
    }
    if (surfaceName && vertices.length >= 3) {
      const normal = computeNormalFromVertices(vertices);
      if (normal) {
        surfaceNormals.set(surfaceName.toUpperCase(), normal);
      }
    }
    i = endIndex;
  }
  return surfaceNormals;
}

function fixFenestrationOrientation(lines) {
  const surfaceNormals = buildSurfaceNormalMap(lines);
  const corrected = [];
  for (let i = 0; i < lines.length; i++) {
    if (!lines[i].trim().toUpperCase().startsWith('FENESTRATIONSURFACE:DETAILED')) {
      continue;
    }
    const { indices, endIndex } = gatherBlock(lines, i);
    const blockLines = indices.map(idx => lines[idx]);
    let fenName = null;
    let baseSurfaceName = null;
    const vertexData = [];
    let fieldIndex = -1;
    for (let j = 1; j < blockLines.length; j++) {
      const line = blockLines[j];
      const trimmed = line.trim();
      if (!trimmed || trimmed.startsWith('!')) {
        continue;
      }
      if (line.toLowerCase().includes('!- vertex')) {
        const coords = parseVertexCoordinates(line);
        if (coords) {
          vertexData.push({
            index: indices[j],
            coords,
            raw: lines[indices[j]]
          });
        }
        continue;
      }
      fieldIndex += 1;
      if (fieldIndex === 0) {
        fenName = parseValueFromLine(line);
      } else if (fieldIndex === 3) {
        baseSurfaceName = parseValueFromLine(line);
      }
    }
    if (!fenName || !baseSurfaceName || vertexData.length < 3) {
      i = endIndex;
      continue;
    }
    const baseNormal = surfaceNormals.get(baseSurfaceName.toUpperCase());
    if (!baseNormal) {
      i = endIndex;
      continue;
    }
    const fenNormal = computeNormalFromVertices(vertexData.map(entry => entry.coords));
    if (!fenNormal) {
      i = endIndex;
      continue;
    }
    const dot =
      fenNormal[0] * baseNormal[0] +
      fenNormal[1] * baseNormal[1] +
      fenNormal[2] * baseNormal[2];
    if (dot < -1e-6) {
      const reversed = vertexData.map(entry => entry.raw).reverse();
      for (let k = 0; k < vertexData.length; k++) {
        lines[vertexData[k].index] = reversed[k];
      }
      corrected.push(`${fenName} ↔ ${baseSurfaceName}`);
    }
    i = endIndex;
  }
  return corrected;
}

function replaceLineValue(line, newValue) {
  const trimmed = line.trimEnd();
  const commentIndex = trimmed.indexOf('!-');
  const comment = commentIndex >= 0 ? trimmed.slice(commentIndex).trim() : '';
  const valuePortion = commentIndex >= 0 ? trimmed.slice(0, commentIndex).trimEnd() : trimmed;
  const delimiter = valuePortion.endsWith(';') ? ';' : ',';
  const indentMatch = line.match(/^\s*/);
  const indent = indentMatch ? indentMatch[0] : '';
  let updated = `${indent}${newValue}${delimiter}`;
  if (comment) {
    updated += `  ${comment}`;
  }
  return updated;
}

function autosizeDxCoils(lines) {
  let inCoil = false;
  let fieldIndex = -1;

  for (let i = 0; i < lines.length; i++) {
    const trimmed = lines[i].trim();
    const dataPart = trimmed.split('!')[0].trim();

    if (!inCoil) {
      if (/^Coil:Cooling:DX:SingleSpeed,/i.test(dataPart)) {
        inCoil = true;
        fieldIndex = -1;
      }
      continue;
    }

    if (dataPart === '') {
      continue;
    }

    fieldIndex += 1;

    if (fieldIndex === 2) {
      const value = parseFloat(parseValueFromLine(lines[i]));
      if (Number.isNaN(value) || value <= 0) {
        lines[i] = replaceLineValue(lines[i], '2000');
      }
    } else if (fieldIndex === 3) {
      const value = parseFloat(parseValueFromLine(lines[i]));
      if (Number.isNaN(value) || value <= 0 || value > 1) {
        lines[i] = replaceLineValue(lines[i], '0.75');
      }
    } else if (fieldIndex === 4) {
      const value = parseFloat(parseValueFromLine(lines[i]));
      if (Number.isNaN(value) || value <= 0) {
        lines[i] = replaceLineValue(lines[i], '3.2');
      }
    } else if (fieldIndex === 5) {
      const value = parseFloat(parseValueFromLine(lines[i]));
      if (Number.isNaN(value) || value <= 0) {
        lines[i] = replaceLineValue(lines[i], '0.60');
      }
    }

    if (dataPart.endsWith(';')) {
      inCoil = false;
    }
  }
}

function autosizeVariableVolumeFans(lines) {
  let inFan = false;
  let fieldIndex = 0;

  for (let i = 0; i < lines.length; i++) {
    const trimmed = lines[i].trim();
    const dataPart = trimmed.split('!')[0].trim();

    if (!inFan) {
      if (/^Fan:VariableVolume,/i.test(dataPart)) {
        inFan = true;
        fieldIndex = 0;
      }
      continue;
    }

    if (dataPart === '') {
      continue;
    }

    fieldIndex += 1;

    if (fieldIndex === 5 && !dataPart.toLowerCase().startsWith('autosize')) {
      lines[i] = replaceLineValue(lines[i], 'Autosize');
    }

    if (dataPart.endsWith(';')) {
      inFan = false;
    }
  }
}

function removeOutputVariableRequests(lines) {
  let i = 0;
  while (i < lines.length) {
    if (/^Output:Variable,/i.test(lines[i].trim())) {
      let end = i;
      while (end < lines.length) {
        if (lines[end].trim().endsWith(';')) {
          end += 1;
          break;
        }
        end += 1;
      }
      lines.splice(i, end - i);
      continue;
    }
    i += 1;
  }
}

function fixFloorSurfaces(lines) {
  let i = 0;

  while (i < lines.length) {
    if (!/^BuildingSurface:Detailed,/i.test(lines[i].trim().split('!')[0].trim())) {
      i += 1;
      continue;
    }

    let fieldIndex = 0;
    let isFloor = false;
    let vertexCount = 0;
    let vertexStart = null;
    let vertexEnd = null;
    let lastLineComment = '';
    let j = i + 1;

    while (j < lines.length) {
      const trimmed = lines[j].trim();
      const dataPart = trimmed.split('!')[0].trim();

      if (dataPart === '') {
        j += 1;
        continue;
      }

      fieldIndex += 1;

      if (fieldIndex === 2 && dataPart.toLowerCase().startsWith('floor')) {
        isFloor = true;
      }

      if (isFloor) {
        if (fieldIndex === 6 && !dataPart.toLowerCase().startsWith('ground')) {
          lines[j] = replaceLineValue(lines[j], 'Ground');
        }
        if (fieldIndex === 8 && !dataPart.toLowerCase().startsWith('nosun')) {
          lines[j] = replaceLineValue(lines[j], 'NoSun');
        }
        if (fieldIndex === 9 && !dataPart.toLowerCase().startsWith('nowind')) {
          lines[j] = replaceLineValue(lines[j], 'NoWind');
        }
      }

      if (fieldIndex === 11) {
        const match = dataPart.match(/[-+]?\d+/);
        if (match) {
          vertexCount = parseInt(match[0], 10);
        }
        vertexStart = j + 1;
      } else if (vertexStart && vertexEnd === null && dataPart.endsWith(';')) {
        vertexEnd = j + 1;
        const commentIndex = lines[j].indexOf('!-');
        if (commentIndex >= 0) {
          lastLineComment = lines[j].slice(commentIndex).trim();
        }
        break;
      }

      if (dataPart.endsWith(';') && !vertexStart) {
        break;
      }

      j += 1;
    }

    if (isFloor && vertexStart !== null && vertexEnd !== null && vertexCount > 0) {
      const vertexLines = lines.slice(vertexStart, vertexEnd);
      const numbers = [];

      vertexLines.forEach(line => {
        const matches = line.match(/[-+]?\d*\.?\d+(?:[Ee][-+]?\d+)?/g);
        if (matches) {
          numbers.push(...matches);
        }
      });

      if (numbers.length === vertexCount * 3) {
        const vertices = [];
        for (let v = 0; v < vertexCount; v++) {
          const base = v * 3;
          vertices.push([numbers[base], numbers[base + 1], numbers[base + 2]]);
        }
        vertices.reverse();

        const newLines = vertices.map((vertex, idx) => {
          const delimiter = idx === vertices.length - 1 ? ';' : ',';
          let line = `  ${vertex[0]}, ${vertex[1]}, ${vertex[2]}${delimiter}`;
          if (idx === vertices.length - 1 && lastLineComment) {
            line += `  ${lastLineComment}`;
          }
          return line;
        });

        lines.splice(vertexStart, vertexEnd - vertexStart, ...newLines);
        i = vertexStart + newLines.length;
        continue;
      }
    }

    i = j + 1;
  }
}

function disableSizingWhenNoEquipment(lines) {
  const hasEquipment = lines.some(line =>
    line.trim().toUpperCase().startsWith('ZONEHVAC:EQUIPMENTCONNECTIONS')
  );
  if (hasEquipment) {
    return;
  }

  for (let i = 0; i < lines.length; i++) {
    if (!lines[i].trim().toUpperCase().startsWith('SIMULATIONCONTROL')) {
      continue;
    }
    let fieldIndex = 0;
    for (let j = i + 1; j < lines.length; j++) {
      const line = lines[j];
      const trimmed = line.trim();
      if (!trimmed || trimmed.startsWith('!')) {
        continue;
      }
      fieldIndex += 1;
      if (fieldIndex <= 3) {
        lines[j] = replaceLineValue(lines[j], 'No');
      }
      if (trimmed.includes(';')) {
        return;
      }
    }
    break;
  }
}

function extractZoneAreas(lines) {
  const zoneAreas = new Map();
  let inZone = false;
  let fieldIndex = -1;
  let currentZone = '';
  for (let i = 0; i < lines.length; i++) {
    const trimmedUpper = lines[i].trim().toUpperCase();
    if (trimmedUpper.startsWith('ZONE,')) {
      inZone = true;
      fieldIndex = -1;
      currentZone = '';
      continue;
    }
    if (!inZone) {
      continue;
    }
    const line = lines[i];
    const trimmed = line.trim();
    if (!trimmed || trimmed.startsWith('!')) {
      continue;
    }
    fieldIndex += 1;
    if (fieldIndex === 0) {
      currentZone = parseValueFromLine(line).toLowerCase();
    } else if (fieldIndex === 9) {
      const value = parseFloat(parseValueFromLine(line));
      if (!Number.isNaN(value) && currentZone) {
        zoneAreas.set(currentZone, value);
      }
    }
    if (line.split('!-')[0].includes(';')) {
      inZone = false;
    }
  }
  return zoneAreas;
}

function scaleZoneInfiltration(lines) {
  const zoneAreas = extractZoneAreas(lines);
  const areaValues = Array.from(zoneAreas.values());
  const averageArea =
    areaValues.length > 0
      ? areaValues.reduce((sum, val) => sum + val, 0) / areaValues.length
      : 120;
  let inObject = false;
  let fieldIndex = -1;
  let targetZone = '';
  for (let i = 0; i < lines.length; i++) {
    const trimmedUpper = lines[i].trim().toUpperCase();
    if (trimmedUpper.startsWith('ZONEINFILTRATION:DESIGNFLOWRATE,')) {
      inObject = true;
      fieldIndex = -1;
      targetZone = '';
      continue;
    }
    if (!inObject) {
      continue;
    }
    const line = lines[i];
    const trimmed = line.trim();
    if (!trimmed || trimmed.startsWith('!')) {
      continue;
    }
    fieldIndex += 1;
    if (fieldIndex === 1) {
      targetZone = parseValueFromLine(line).toLowerCase();
    } else if (fieldIndex === 4) {
      const existing = parseFloat(parseValueFromLine(line));
      if (!Number.isNaN(existing)) {
        const area = zoneAreas.get(targetZone) || averageArea;
        let factor;
        let minFlow;
        if (area < 150) {
          factor = 3e-7;
          minFlow = 5e-5;
        } else if (area < 300) {
          factor = 5e-7;
          minFlow = 8e-5;
        } else {
          factor = 7e-7;
          minFlow = 0.00012;
        }
        const targetFlow = Math.max(minFlow, area * factor);
        const newValue = Math.min(existing, targetFlow);
        lines[i] = replaceLineValue(lines[i], newValue.toExponential(6));
      }
    }
    if (line.split('!-')[0].includes(';')) {
      inObject = false;
    }
  }
}

function enforceMinimumVavFlow(lines, minimumFraction = 0.25) {
  const designFraction = Math.min(0.9, Math.max(DEFAULT_VAV_DESIGN_FRACTION, dynamicVavDesignFraction ?? DEFAULT_VAV_DESIGN_FRACTION));
  let inTerminal = false;
  let fieldIndex = -1;
  for (let i = 0; i < lines.length; i++) {
    const trimmedUpper = lines[i].trim().toUpperCase();
    if (trimmedUpper.startsWith('AIRTERMINAL:SINGLEDUCT:VAV:REHEAT')) {
      inTerminal = true;
      fieldIndex = -1;
      continue;
    }
    if (!inTerminal) {
      continue;
    }
    const line = lines[i];
    const trimmed = line.trim();
    if (!trimmed || trimmed.startsWith('!')) {
      continue;
    }
    fieldIndex += 1;
    if (fieldIndex === 5) {
      if (parseValueFromLine(line).toLowerCase() !== 'scheduled') {
        lines[i] = replaceLineValue(lines[i], 'Scheduled');
      }
    } else if (fieldIndex === 6) {
      const value = parseFloat(parseValueFromLine(line));
      if (Number.isNaN(value) || value < designFraction) {
        lines[i] = replaceLineValue(lines[i], designFraction.toFixed(2));
      }
    } else if (fieldIndex === 7) {
      const value = parseFloat(parseValueFromLine(line));
      if (Number.isNaN(value) || value < minimumFraction) {
        lines[i] = replaceLineValue(lines[i], minimumFraction.toFixed(2));
      }
    } else if (fieldIndex === 8) {
      const current = parseValueFromLine(line);
      if (!current || current.toUpperCase() !== VAV_MIN_FLOW_SCHEDULE_NAME.toUpperCase()) {
        lines[i] = replaceLineValue(lines[i], VAV_MIN_FLOW_SCHEDULE_NAME);
      }
    }
    if (line.split('!-')[0].includes(';')) {
      inTerminal = false;
      fieldIndex = -1;
    }
  }
}

function enforceFanMinimumFlow(lines, minimumFraction = 0.25) {
  let inFan = false;
  let fieldIndex = -1;
  for (let i = 0; i < lines.length; i++) {
    const trimmedUpper = lines[i].trim().toUpperCase();
    if (trimmedUpper.startsWith('FAN:VARIABLEVOLUME')) {
      inFan = true;
      fieldIndex = -1;
      continue;
    }
    if (!inFan) {
      continue;
    }
    const line = lines[i];
    const trimmed = line.trim();
    if (!trimmed || trimmed.startsWith('!')) {
      continue;
    }
    fieldIndex += 1;
    if (fieldIndex === 6 && trimmed.toUpperCase().startsWith('FIXEDFLOWRATE')) {
      continue;
    }
    if (fieldIndex === 7) {
      const value = parseFloat(parseValueFromLine(line));
      if (!Number.isNaN(value)) {
        const targetFraction = Math.max(minimumFraction, value);
        lines[i] = replaceLineValue(lines[i], targetFraction.toFixed(2));
      }
    }
    if (fieldIndex === 8) {
      const parsed = parseFloat(parseValueFromLine(line));
      if (Number.isFinite(parsed) && parsed <= 0) {
        lines[i] = replaceLineValue(lines[i], 'Autosize');
      }
    }
    if (line.split('!-')[0].includes(';')) {
      inFan = false;
      fieldIndex = -1;
    }
  }
}

function computeCoilMinimumFractions(lines, minRatio = 2.8e-5) {
  const requirements = new Map();
  let inCoil = false;
  let fieldIndex = -1;
  let currentName = '';
  let currentCapacity = null;
  let currentFlow = null;

  for (let i = 0; i < lines.length; i++) {
    const trimmedUpper = lines[i].trim().toUpperCase();
    if (trimmedUpper.startsWith('COIL:COOLING:DX:SINGLESPEED,')) {
      inCoil = true;
      fieldIndex = -1;
      currentName = '';
      currentCapacity = null;
      currentFlow = null;
      continue;
    }
    if (!inCoil) {
      continue;
    }
    const line = lines[i];
    const trimmed = line.trim();
    if (!trimmed || trimmed.startsWith('!')) {
      continue;
    }
    fieldIndex += 1;
    if (fieldIndex === 0) {
      currentName = parseValueFromLine(line);
    } else if (fieldIndex === 2) {
      const value = parseFloat(parseValueFromLine(line));
      if (Number.isFinite(value) && value > 0) {
        currentCapacity = value;
      }
    } else if (fieldIndex === 5) {
      const value = parseFloat(parseValueFromLine(line));
      if (Number.isFinite(value) && value > 0) {
        currentFlow = value;
      }
    }
    if (line.split('!-')[0].includes(';')) {
      if (currentName && Number.isFinite(currentCapacity) && Number.isFinite(currentFlow) && currentCapacity > 0 && currentFlow > 0) {
        const baseName = stripSuffixIgnoreCase(currentName, '_CoolingCoilDX');
        const normalized = normalizeIdentifier(baseName);
        const required = (minRatio * currentCapacity) / currentFlow;
        if (Number.isFinite(required) && required > 0) {
          const clamped = Math.min(0.7, Math.max(0.25, required));
          requirements.set(normalized, clamped);
        }
      }
      inCoil = false;
      fieldIndex = -1;
      currentName = '';
      currentCapacity = null;
      currentFlow = null;
    }
  }
  return requirements;
}

function adjustVavMinimumFractions(lines, minRatio = 2.8e-5) {
  const requirements = computeCoilMinimumFractions(lines, minRatio);
  if (!requirements.size) {
    return;
  }
  let inTerminal = false;
  let fieldIndex = -1;
  let currentName = '';
  let targetFraction = null;
  let method = '';

  for (let i = 0; i < lines.length; i++) {
    const trimmedUpper = lines[i].trim().toUpperCase();
    if (trimmedUpper.startsWith('AIRTERMINAL:SINGLEDUCT:VAV:REHEAT,')) {
      inTerminal = true;
      fieldIndex = -1;
      currentName = '';
      targetFraction = null;
      method = '';
      continue;
    }
    if (!inTerminal) {
      continue;
    }
    const line = lines[i];
    const trimmed = line.trim();
    if (!trimmed || trimmed.startsWith('!')) {
      continue;
    }
    fieldIndex += 1;
    if (fieldIndex === 0) {
      currentName = parseValueFromLine(line);
      const baseName = stripSuffixIgnoreCase(currentName, '_VAVTerminal');
      targetFraction = requirements.get(normalizeIdentifier(baseName)) ?? null;
    } else if (fieldIndex === 5) {
      method = parseValueFromLine(line).toLowerCase();
      if (method !== 'constant') {
        targetFraction = null;
      }
    } else if (fieldIndex === 6 && method === 'constant' && targetFraction !== null) {
      const existing = parseFloat(parseValueFromLine(line));
      const desired = Math.min(0.7, Math.max(0.25, targetFraction));
      if (Number.isNaN(existing) || existing < desired - 1e-4) {
        lines[i] = replaceLineValue(lines[i], formatNumber(desired, 3));
      }
      targetFraction = null;
    }
    if (line.split('!-')[0].includes(';')) {
      inTerminal = false;
      fieldIndex = -1;
      currentName = '';
      targetFraction = null;
      method = '';
    }
  }
}

function collectExistingDesignSpecNames(lines) {
  const names = new Set();
  let inObject = false;
  for (let i = 0; i < lines.length; i++) {
    const trimmedUpper = lines[i].trim().toUpperCase();
    if (trimmedUpper.startsWith('DESIGNSPECIFICATION:OUTDOORAIR,')) {
      inObject = true;
      continue;
    }
    if (inObject) {
      const value = parseValueFromLine(lines[i]);
      if (value) {
        names.add(value.toUpperCase());
      }
      inObject = false;
    }
  }
  return names;
}

function ensureVavMinFlowSchedule(lines) {
  const summerDesignFraction = Math.min(0.9, Math.max(DEFAULT_VAV_DESIGN_FRACTION, (dynamicVavDesignFraction ?? DEFAULT_VAV_DESIGN_FRACTION)));
  const winterDesignFraction = Math.min(summerDesignFraction, 0.35);
  let exists = false;
  for (let i = 0; i < lines.length - 1; i++) {
    if (lines[i].trim().toUpperCase().startsWith('SCHEDULE:COMPACT,')) {
      const scheduleName = parseValueFromLine(lines[i + 1] || '');
      if (scheduleName && scheduleName.toUpperCase() === VAV_MIN_FLOW_SCHEDULE_NAME.toUpperCase()) {
        exists = true;
        break;
      }
    }
  }
  if (!exists) {
    lines.push(
      '',
      'Schedule:Compact,',
      `  ${VAV_MIN_FLOW_SCHEDULE_NAME},`,
      '  Fraction,',
      '  Through: 12/31,',
      '  For: SummerDesignDay,',
      `  Until: 24:00, ${summerDesignFraction.toFixed(2)},`,
      '  For: WinterDesignDay,',
      `  Until: 24:00, ${winterDesignFraction.toFixed(2)},`,
      '  For: AllOtherDays,',
      '  Until: 24:00, 0.25;'
    );
  }
}

function purgeGeneratedDesignSpecs(lines) {
  let i = 0;
  while (i < lines.length) {
    if (lines[i].trim().toUpperCase().startsWith('DESIGNSPECIFICATION:OUTDOORAIR,')) {
      const nameLine = lines[i + 1] || '';
      if (nameLine.toUpperCase().includes('_DSOA')) {
        let j = i + 1;
        while (j < lines.length && !lines[j].split('!-')[0].includes(';')) {
          j += 1;
        }
        if (j < lines.length) {
          j += 1; // include terminating line
        }
        lines.splice(i, j - i);
        continue;
      }
    }
    i += 1;
  }
}

function appendDesignSpecOutdoorAir(lines) {
  purgeGeneratedDesignSpecs(lines);
  const zoneAreas = extractZoneAreas(lines);
  const existing = collectExistingDesignSpecNames(lines);
  const additions = [];
  for (const [zoneName, area] of zoneAreas.entries()) {
    const specName = `${zoneName.toUpperCase()}_DSOA`;
    if (existing.has(specName)) {
      continue;
    }
    const flowPerPerson = 0.008; // m3/s-person (roughly ASHRAE 62.1 office default)
    const flowPerArea = 0.0003; // m3/s-m2
    additions.push(
      'DesignSpecification:OutdoorAir,',
      `  ${specName},`,
      '  Flow/Person,',
      `  ${flowPerPerson.toFixed(4)},`,
      `  ${flowPerArea.toFixed(4)},`,
      '  0.0,',
      '  0.0;'
    );
    existing.add(specName);
  }
  if (additions.length > 0) {
    lines.push('\n' + additions.join('\n') + '\n');
  }
  return existing;
}

function attachDesignSpecOutdoorAir(lines) {
  const zoneAreas = extractZoneAreas(lines);
  const specNames = appendDesignSpecOutdoorAir(lines);
  let inSizingZone = false;
  let fieldIndex = -1;
  let currentZone = '';
  for (let i = 0; i < lines.length; i++) {
    const trimmedUpper = lines[i].trim().toUpperCase();
    if (trimmedUpper.startsWith('SIZING:ZONE,')) {
      inSizingZone = true;
      fieldIndex = -1;
      currentZone = '';
      continue;
    }
    if (!inSizingZone) {
      continue;
    }
    const line = lines[i];
    const trimmed = line.trim();
    if (!trimmed || trimmed.startsWith('!')) {
      continue;
    }
    fieldIndex += 1;
    if (fieldIndex === 0) {
      currentZone = parseValueFromLine(line).toLowerCase();
    } else if (fieldIndex === 9) {
      if (currentZone && zoneAreas.has(currentZone)) {
        const specName = `${currentZone.toUpperCase()}_DSOA`;
        if (specNames.has(specName)) {
          lines[i] = replaceLineValue(lines[i], specName);
        }
      }
    }
    if (line.split('!-')[0].includes(';')) {
      inSizingZone = false;
      fieldIndex = -1;
      currentZone = '';
    }
  }
  return specNames;
}

function tuneDxCoils(lines) {
  return;
}

function sanitizeIdfContent(idfContent) {
  try {
    const lines = idfContent.split(/\r?\n/);
    autosizeDxCoils(lines);
    autosizeVariableVolumeFans(lines);
    fixFloorSurfaces(lines);
    removeOutputVariableRequests(lines);
    fixFenestrationOrientation(lines);
    disableSizingWhenNoEquipment(lines);
    scaleZoneInfiltration(lines);
    enforceMinimumVavFlow(lines, 0.25);
    enforceFanMinimumFlow(lines, 0.25);
    adjustVavMinimumFractions(lines);
    attachDesignSpecOutdoorAir(lines);
    tuneDxCoils(lines);
    let sanitized = lines.join('\n');
    if (!/Output:Meter\s*,\s*Electricity:Facility/i.test(sanitized)) {
      sanitized += '\n\nOutput:Meter,\n    Electricity:Facility,\n    RunPeriod;\n';
    }
    return sanitized;
  } catch (error) {
    console.warn(`IDF sanitization failed: ${error.message}`);
    return idfContent;
  }
}

function summarizeMessages(messages, limit = 5, sliceLength = 80) {
  const counts = {};
  messages.forEach(msg => {
    if (!msg) return;
    const key = msg.trim().substring(0, sliceLength);
    counts[key] = (counts[key] || 0) + 1;
  });
  return Object.entries(counts)
    .sort((a, b) => b[1] - a[1])
    .slice(0, limit)
    .map(([message, count]) => ({ message, count }));
}

function loadLocalIDF(idfPath) {
  console.log(`\n📤 Loading IDF from: ${idfPath}`);
  
  const idfContent = readLocalIDF(idfPath);
  const sanitizedContent = sanitizeIdfContent(idfContent);

  return {
    idf_content: sanitizedContent,
    parameters: { source: 'local_file', path: idfPath }
  };
}

async function runSimulation(idfContent, weatherContent, outputDir) {
  mkdirSync(outputDir, { recursive: true });
  
  // Ensure Output:SQLite
  if (!idfContent.includes('Output:SQLite')) {
    idfContent = idfContent + "\n\nOutput:SQLite,\n    Simple;\n";
  }
  
  const requestBody = {
    idf_content: idfContent,
    weather_content: weatherContent
  };
  
  const startTime = Date.now();
  
  try {
    console.log(`   📤 Calling EnergyPlus API: ${ENERGYPLUS_API_URL}`);
    
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 600000); // 10 minute timeout
    
    const response = await fetch(ENERGYPLUS_API_URL, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(requestBody),
      signal: controller.signal
    });
    
    clearTimeout(timeoutId);
    const elapsed = ((Date.now() - startTime) / 1000).toFixed(1);
    
    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`EnergyPlus API error (${response.status}): ${errorText}`);
    }
    
    const apiResults = await response.json();
    
    // Save API response for reference
    writeFileSync(join(outputDir, 'api_response.json'), JSON.stringify(apiResults, null, 2), 'utf-8');
    
    // Download error file if available for warning analysis
    if (apiResults.output_files_download && apiResults.output_files_download['eplusout.err']) {
      try {
        const downloadBaseUrl = apiResults.download_base_url || ENERGYPLUS_API_URL.replace('/simulate', '');
        const errUrl = `${downloadBaseUrl}${apiResults.output_files_download['eplusout.err'].url}`;
        const errResponse = await fetch(errUrl);
        if (errResponse.ok) {
          const errContent = await errResponse.text();
          writeFileSync(join(outputDir, 'eplusout.err'), errContent, 'utf-8');
        }
      } catch (e) {
        console.warn(`   ⚠️  Could not download error file: ${e.message}`);
      }
    }
    
    return {
      success: apiResults.simulation_status === 'success',
      output_dir: outputDir,
      elapsed_time: elapsed,
      api_response: apiResults,
      stdout: apiResults.stdout || '',
      stderr: apiResults.stderr || ''
    };
    
  } catch (error) {
    const elapsed = ((Date.now() - startTime) / 1000).toFixed(1);
    if (error.name === 'AbortError') {
      throw new Error('Simulation request timed out after 10 minutes');
    }
    throw error;
  }
}

function analyzeWarnings(outputDir, apiResponse = null) {
  const warnings = [];
  const errors = [];
  let fatal = false;
  
  // First, try to get warnings/errors from API response
  if (apiResponse) {
    if (apiResponse.warnings && Array.isArray(apiResponse.warnings)) {
      warnings.push(...apiResponse.warnings);
    }
    if (apiResponse.errors && Array.isArray(apiResponse.errors)) {
      errors.push(...apiResponse.errors);
      if (apiResponse.simulation_status === 'error' || apiResponse.fatal_error) {
        fatal = true;
      }
    }
  }
  
  // Also check error file if it exists (downloaded from API)
  const errFile = join(outputDir, 'eplusout.err');
  if (existsSync(errFile)) {
    const content = readFileSync(errFile, 'utf-8');
    const lines = content.split('\n');
    
    for (let i = 0; i < lines.length; i++) {
      const line = lines[i];
      if (line.includes('** Warning **')) {
        const warning = line.replace('** Warning **', '').trim();
        if (!warnings.includes(warning)) {
          warnings.push(warning);
        }
      } else if (line.includes('** Severe **') || line.includes('**  Fatal  **')) {
        const error = line.replace(/\*\*.*?\*\*/g, '').trim();
        if (!errors.includes(error)) {
          errors.push(error);
        }
        if (line.includes('Fatal')) {
          fatal = true;
        }
      }
    }
  }
  
  return { warnings, errors, fatal };
}

function computeRequiredVavDesignFractionFromEio(eioPath, targetRatio = 2.8e-5, safetyFactor = 1.05) {
  if (!existsSync(eioPath)) {
    return null;
  }
  const content = readFileSync(eioPath, 'utf-8');
  const lines = content.split(/\r?\n/);
  const coilData = new Map();

  lines.forEach(line => {
    if (!line.includes('Component Sizing Information') || !line.includes('Coil:Cooling:DX:SingleSpeed')) {
      return;
    }
    const parts = line.split(',').map(part => part.trim());
    if (parts.length < 5) {
      return;
    }
    const coilName = parts[2];
    const descriptor = parts[3];
    const value = parseFloat(parts[4]);
    if (!coilName || !Number.isFinite(value)) {
      return;
    }
    const entry = coilData.get(coilName) || {};
    if (/Rated Air Flow Rate/i.test(descriptor)) {
      entry.flow = value;
    } else if (/Gross Rated Total Cooling Capacity/i.test(descriptor)) {
      entry.capacity = value;
    }
    coilData.set(coilName, entry);
  });

  let maxFraction = 0;
  coilData.forEach(data => {
    if (!Number.isFinite(data.flow) || data.flow <= 0 || !Number.isFinite(data.capacity) || data.capacity <= 0) {
      return;
    }
    const requiredFraction = (targetRatio * data.capacity) / data.flow;
    if (Number.isFinite(requiredFraction) && requiredFraction > maxFraction) {
      maxFraction = requiredFraction;
    }
  });

  if (maxFraction <= 0) {
    return null;
  }
  return Math.min(0.9, maxFraction * safetyFactor);
}

function analyzeIDF(idfContent) {
  const issues = [];
  const info = {};
  
  try {
    // Check building area - try multiple patterns
    const numberPattern = '([\\d.+-Ee]+)';
    let zoneAreaMatches = Array.from(idfContent.matchAll(new RegExp(`${numberPattern}\\s*,\\s*!-\\s*Floor Area\\s*\\{m2\\}`, 'g')));
    if (zoneAreaMatches.length === 0) {
      // Fallback: capture any comment containing "Floor Area"
      zoneAreaMatches = Array.from(idfContent.matchAll(new RegExp(`${numberPattern}\\s*,\\s*!-\\s*.*Floor Area`, 'g')));
    }
    const areas = zoneAreaMatches
      .map(m => parseFloat(m[1]))
      .filter(a => !isNaN(a));
    const totalArea = areas.length > 0 ? areas.reduce((a, b) => a + b, 0) : 0;
    info.total_area = totalArea;

    // Check lighting power density
    const lightingMatches = Array.from(idfContent.matchAll(new RegExp(`${numberPattern}\\s*,\\s*!-\\s*Watts per Zone Floor Area`, 'g')));
    const lightingValues = lightingMatches
      .map(m => parseFloat(m[1]))
      .filter(v => !isNaN(v));
    if (lightingValues.length > 0) {
      const avgLighting = lightingValues.reduce((a, b) => a + b, 0) / lightingValues.length;
      info.avg_lighting_power = avgLighting;
      if (avgLighting < 4) {
        issues.push(`Lighting power density too low: ${avgLighting.toFixed(1)} W/m² (expected 8-12 W/m²)`);
      } else if (avgLighting < 7) {
        issues.push(`Lighting power density slightly low: ${avgLighting.toFixed(1)} W/m² (expected 8-12 W/m²)`);
      }
    } else {
      issues.push('No lighting power density values found');
    }
  
    // Check equipment power density
    const equipmentMatches = Array.from(idfContent.matchAll(new RegExp(`${numberPattern}\\s*,\\s*!-\\s*Watts per Zone Floor Area`, 'g')));
    const equipmentValues = equipmentMatches
      .map(m => parseFloat(m[1]))
      .filter(v => !isNaN(v));
    if (equipmentValues.length > 0) {
      const avgEquipment = equipmentValues.reduce((a, b) => a + b, 0) / equipmentValues.length;
      info.avg_equipment_power = avgEquipment;
      if (avgEquipment < 3.5) {
        issues.push(`Equipment power density too low: ${avgEquipment.toFixed(1)} W/m² (expected 5-10 W/m²)`);
      } else if (avgEquipment < 5.5) {
        issues.push(`Equipment power density slightly low: ${avgEquipment.toFixed(1)} W/m² (expected 5-10 W/m²)`);
      }
    } else {
      issues.push('No equipment power density values found');
    }
  
    // Count zones
    const zones = (idfContent.match(/^Zone,/gm) || []).length;
    info.zone_count = zones;
  } catch (error) {
    issues.push(`Error analyzing IDF: ${error.message}`);
  }
  
  return { issues, info };
}

async function extractEnergyData(outputDir, apiResponse = null) {
  // First, try to get energy data from API response
  if (apiResponse && apiResponse.simulation_status === 'success') {
    if (apiResponse.energy_results || apiResponse.total_energy_consumption) {
      return {
        energy_data: {
          total_energy_consumption: apiResponse.total_energy_consumption || 0,
          energy_intensity: apiResponse.energy_intensity || 0,
          building_area: apiResponse.building_area || 0,
          heating_energy: apiResponse.energy_results?.heating_energy || 0,
          cooling_energy: apiResponse.energy_results?.cooling_energy || 0,
          lighting_energy: apiResponse.energy_results?.lighting_energy || 0,
          equipment_energy: apiResponse.energy_results?.equipment_energy || 0
        }
      };
    }
  }
  
  // Fallback to local extraction if API doesn't have data
  const extractScript = join(process.cwd(), 'extract-energy-local.py');
  const files = readdirSync(outputDir);
  const sqliteFile = files.find(f => f.endsWith('.sql') || f.endsWith('.sqlite'));
  
  if (sqliteFile && existsSync(extractScript)) {
    try {
      const sqlitePath = join(outputDir, sqliteFile);
      const { stdout } = await execAsync(`python3 "${extractScript}" "${sqlitePath}" --period-days 365`);
      return JSON.parse(stdout);
    } catch (error) {
      return { error: error.message };
    }
  }
  return { error: 'No energy data available from API or local extraction' };
}

async function runTest(idfPath, testNumber, weatherFile) {
  const idfName = basename(idfPath);
  console.log(`\n${'='.repeat(70)}`);
  console.log(`TEST ${testNumber}: ${idfName}`);
  console.log(`IDF Path: ${idfPath}`);
  console.log('='.repeat(70));
  
  const results = {
    idf_path: idfPath,
    idf_name: idfName,
    test_number: testNumber,
    success: false,
    issues: [],
    warnings: [],
    errors: [],
    energy_data: null,
    idf_analysis: null,
    elapsed_time: null,
    weather_file: weatherFile,
    warning_summary: [],
    error_summary: []
  };
  
  try {
    if (!weatherFile) {
      throw new Error('Weather file not provided to runTest');
    }
    const weatherContent = readWeatherFile(weatherFile);

    // Load IDF from local file
    dynamicVavDesignFraction = null;

    const idfResult = loadLocalIDF(idfPath);
    results.idf_size = (idfResult.idf_content.length / 1024).toFixed(1);

    const baseProcessedIdf = postProcessIdf(idfResult.idf_content, weatherContent);
    if (baseProcessedIdf !== idfResult.idf_content) {
      results.idf_post_processed = true;
    }
    
    // Analyze IDF BEFORE simulation
    const idfAnalysis = analyzeIDF(baseProcessedIdf);
    results.idf_analysis = idfAnalysis;
    results.issues.push(...idfAnalysis.issues);
    
    let processedIdfContent = sanitizeIdfContent(baseProcessedIdf);
    let finalOutputDir = null;
    let finalWarnings = null;
    let finalSimResult = null;
    
    for (let attempt = 1; attempt <= 2; attempt++) {
      const attemptOutputDir = join(process.cwd(), 'test_outputs', `test_${testNumber}_${Date.now()}_attempt${attempt}`);
      let simError = null;
      let simResult = null;
      try {
        simResult = await runSimulation(processedIdfContent, weatherContent, attemptOutputDir);
      } catch (error) {
        simError = error;
      }

      const warnings = analyzeWarnings(attemptOutputDir, simResult?.api_response);
      const eioPath = join(attemptOutputDir, 'eplusout.eio');
      const requiredFraction = computeRequiredVavDesignFractionFromEio(eioPath);
      const currentFraction = dynamicVavDesignFraction ?? DEFAULT_VAV_DESIGN_FRACTION;

      if (attempt === 1 && requiredFraction && requiredFraction > currentFraction + 0.01) {
        dynamicVavDesignFraction = Math.min(0.9, requiredFraction + 0.02);
        console.log(`   ⚙️  Adjusting VAV design fraction to ${dynamicVavDesignFraction.toFixed(2)} and re-running...`);
        processedIdfContent = sanitizeIdfContent(baseProcessedIdf);
        continue;
      }

      finalOutputDir = attemptOutputDir;
      finalWarnings = warnings;
      finalSimResult = simResult;

      if (simError) {
        results.output_dir = finalOutputDir;
        results.warnings = warnings.warnings;
        results.errors = warnings.errors;
        results.fatal = warnings.fatal;
        results.warning_summary = summarizeMessages(results.warnings, 8, 120);
        results.error_summary = summarizeMessages(results.errors, 8, 120);
        throw simError;
      }

      break;
    }

    if (!finalOutputDir || !finalSimResult) {
      throw new Error('Simulation did not complete successfully.');
    }

    results.elapsed_time = finalSimResult.elapsed_time;
    results.output_dir = finalOutputDir;
    
    // Analyze warnings/errors (even if simulation had issues)
    const warnings = finalWarnings;
    results.warnings = warnings.warnings;
    results.errors = warnings.errors;
    results.fatal = warnings.fatal;
    results.warning_summary = summarizeMessages(results.warnings, 8, 120);
    results.error_summary = summarizeMessages(results.errors, 8, 120);
    
    if (warnings.fatal || warnings.errors.length > 0) {
      results.issues.push(`EnergyPlus errors: ${warnings.errors.length} error(s), ${warnings.warnings.length} warning(s)`);
      // Show first few errors
      if (warnings.errors.length > 0) {
        results.issues.push(`First error: ${warnings.errors[0].substring(0, 100)}`);
      }
    }
    
    // Extract energy data from API response
    const energyData = await extractEnergyData(finalOutputDir, finalSimResult?.api_response);
    results.energy_data = energyData;
    
    if (energyData.energy_data) {
      const ed = energyData.energy_data;
      const totalEnergy = ed.total_energy_consumption / 1000; // Convert to kWh
      const buildingArea = idfAnalysis.info.total_area;
      
      if (buildingArea && buildingArea > 0) {
        const eui = totalEnergy / buildingArea;
        
        results.eui = eui;
        results.total_energy_kwh = totalEnergy;
        
        // Check if energy is reasonable
        if (eui < 20) {
          results.issues.push(`EUI too low: ${eui.toFixed(2)} kWh/m²/year (expected 50-200 kWh/m²/year)`);
        } else if (eui > 200) {
          results.issues.push(`EUI too high: ${eui.toFixed(2)} kWh/m²/year (expected 50-200 kWh/m²/year)`);
        }
      } else {
        results.total_energy_kwh = totalEnergy;
        results.issues.push('Total energy available but floor area is zero or missing; skipping EUI calculation');
      }
    }
    
    results.success = true;
    
  } catch (error) {
    results.error = error.message;
    results.success = false;
    
    // Even if simulation failed, try to analyze what we have
    if (results.output_dir && existsSync(results.output_dir)) {
      // Try to load API response if available
      const apiResponsePath = join(results.output_dir, 'api_response.json');
      let apiResponse = null;
      if (existsSync(apiResponsePath)) {
        try {
          apiResponse = JSON.parse(readFileSync(apiResponsePath, 'utf-8'));
        } catch (e) {
          // Ignore
        }
      }
      const warnings = analyzeWarnings(results.output_dir, apiResponse);
      results.warnings = warnings.warnings;
      results.errors = warnings.errors;
      results.fatal = warnings.fatal;
      results.warning_summary = summarizeMessages(results.warnings, 8, 120);
      results.error_summary = summarizeMessages(results.errors, 8, 120);
    }
    
    // Don't show full error in console for cleaner output
    if (!error.message.includes('EnergyPlus Terminated')) {
      console.error(`   ❌ Error: ${error.message.substring(0, 100)}`);
    }
  }
  
  return results;
}

async function main() {
  console.log('🧪 Comprehensive Local IDF Test Suite - Using Railway API');
  console.log('='.repeat(70));
  console.log('Tests local IDF files using Railway EnergyPlus API (v25.1.0)');
  console.log('Checks warnings, validates fixes, tracks iterations');
  console.log('='.repeat(70));
  console.log(`🌐 EnergyPlus API: ${ENERGYPLUS_API_URL}`);

  // Find all local IDF files
  const idfFiles = findLocalIDFFiles();
  if (idfFiles.length === 0) {
    console.error('❌ No IDF files found in search directories:');
    IDF_SEARCH_DIRS.forEach(dir => console.error(`   - ${dir}`));
    process.exit(1);
  }

  // Find all weather files
  const weatherFiles = findLocalWeatherFiles();
  if (weatherFiles.length === 0) {
    console.error('❌ No weather files found in search directories:');
    WEATHER_SEARCH_DIRS.forEach(dir => console.error(`   - ${dir}`));
    process.exit(1);
  }

  console.log(`\n📁 Found ${idfFiles.length} IDF file(s)`);
  console.log(`🌤️  Found ${weatherFiles.length} weather file(s)`);

  // Limit number of tests if TEST_COUNT is set
  const testCount = parseInt(process.env.TEST_COUNT || idfFiles.length.toString(), 10);
  const testIDFFiles = idfFiles.slice(0, testCount);

  // Load progress
  const progress = loadProgress();
  
  // Determine iteration number
  const iterationNumber = (progress.iterations?.length || 0) + 1;
  
  console.log(`\n📚 Progress History:`);
  if (progress.iterations && progress.iterations.length > 0) {
    console.log(`   Total Iterations: ${progress.iterations.length}`);
    const best = findBestIteration(progress);
    if (best) {
      console.log(`   Best Iteration: #${best.iteration} with ${best.total_warnings} warnings`);
      console.log(`   Best Commit: ${best.git_commit.substring(0, 8)}`);
      console.log(`   Best Branch: ${best.git_branch}`);
    }
  } else {
    console.log(`   No previous iterations found - starting fresh`);
  }
  
  // Get current git state
  const gitCommit = await getCurrentGitCommit();
  const gitBranch = await getCurrentGitBranch();
  
  console.log(`\n🔄 Starting Iteration ${iterationNumber}`);
  console.log(`📌 Current Git Commit: ${gitCommit.substring(0, 8)}`);
  console.log(`📌 Current Git Branch: ${gitBranch}`);
  console.log(`\nTesting ${testIDFFiles.length} IDF file(s)`);
  
  const allResults = [];
  
  for (let i = 0; i < testIDFFiles.length; i++) {
    const idfPath = testIDFFiles[i];
    const weatherFile = matchWeatherFile(idfPath);
    
    if (!weatherFile) {
      console.warn(`⚠️  No weather file matched for ${basename(idfPath)}, skipping...`);
      continue;
    }
    
    const result = await runTest(idfPath, i + 1, weatherFile);
    allResults.push(result);
    
    // Display quick summary
    console.log(`\n📊 Quick Summary:`);
    console.log(`   Success: ${result.success ? '✅' : '❌'}`);
    if (result.idf_analysis) {
      console.log(`   Building Area: ${result.idf_analysis.info.total_area?.toFixed(0) || 'N/A'} m²`);
      console.log(`   Avg Lighting: ${result.idf_analysis.info.avg_lighting_power?.toFixed(1) || 'N/A'} W/m²`);
      console.log(`   Avg Equipment: ${result.idf_analysis.info.avg_equipment_power?.toFixed(1) || 'N/A'} W/m²`);
    }
    if (result.eui) {
      console.log(`   EUI: ${result.eui.toFixed(2)} kWh/m²/year`);
    }
    if (result.issues.length > 0) {
      console.log(`   Issues: ${result.issues.length}`);
      if (result.issues.length <= 3) {
        result.issues.forEach(issue => console.log(`     - ${issue.substring(0, 60)}`));
      }
    }
    if (result.warnings.length > 0) {
      console.log(`   Warnings: ${result.warnings.length}`);
    }
    if (result.errors && result.errors.length > 0) {
      console.log(`   Errors: ${result.errors.length}`);
      console.log(`     First: ${result.errors[0].substring(0, 80)}`);
    }
    
    // Brief pause between tests
    if (i < testIDFFiles.length - 1) {
      console.log('\n⏸️  Waiting 3 seconds before next test...');
      await new Promise(resolve => setTimeout(resolve, 3000));
    }
  }
  
  // Calculate total warnings for this iteration
  const totalWarnings = calculateTotalWarnings(allResults);
  
  // Save iteration
  const iterationData = saveIteration(iterationNumber, allResults, gitCommit, gitBranch);
  
  // Update progress
  if (!progress.iterations) {
    progress.iterations = [];
  }
  progress.iterations.push(iterationData);
  
  // Update best iteration if this is better
  const currentBest = findBestIteration(progress);
  const isNewBest = !currentBest || totalWarnings < currentBest.total_warnings;
  const warningsIncreased = currentBest && totalWarnings > currentBest.total_warnings;
  
  if (isNewBest) {
    progress.best_iteration = iterationNumber;
  }
  
  // Save progress
  saveProgress(progress);
  
  // Final comprehensive report
  console.log('\n\n');
  console.log('='.repeat(70));
  console.log(`📋 ITERATION ${iterationNumber} REPORT`);
  console.log('='.repeat(70));
  
  // Iteration comparison
  console.log(`\n📊 Iteration Comparison:`);
  console.log(`   Current Iteration: ${totalWarnings} warnings`);
  if (currentBest) {
    const diff = totalWarnings - currentBest.total_warnings;
    if (diff < 0) {
      console.log(`   ✅ IMPROVED! Reduced by ${Math.abs(diff)} warnings`);
      console.log(`   Previous Best: Iteration #${currentBest.iteration} with ${currentBest.total_warnings} warnings`);
    } else if (diff > 0) {
      console.log(`   ⚠️  WARNINGS INCREASED by ${diff}`);
      console.log(`   Best Iteration: #${currentBest.iteration} with ${currentBest.total_warnings} warnings`);
      console.log(`   Best Commit: ${currentBest.git_commit.substring(0, 8)}`);
      console.log(`   💡 Recommendation: git checkout ${currentBest.git_commit.substring(0, 8)}`);
    } else {
      console.log(`   ➡️  Same as best iteration (#${currentBest.iteration})`);
    }
  } else {
    console.log(`   📌 First iteration - baseline established`);
  }
  
  if (totalWarnings === 0) {
    console.log(`\n🎉 SUCCESS! Zero warnings achieved in iteration ${iterationNumber}!`);
  }
  
  const successful = allResults.filter(r => r.success);
  const failed = allResults.filter(r => !r.success);
  
  console.log(`\n✅ Successful: ${successful.length}/${allResults.length}`);
  console.log(`❌ Failed: ${failed.length}/${allResults.length}`);
  console.log(`⚠️  Total Warnings: ${totalWarnings}`);
  
  // Check if previous issues are fixed
  console.log('\n🔍 Previous Issues Status:');
  console.log('-'.repeat(70));
  
  const lightingPowers = successful
    .map(r => r.idf_analysis?.info?.avg_lighting_power)
    .filter(v => v !== undefined);
  const equipmentPowers = successful
    .map(r => r.idf_analysis?.info?.avg_equipment_power)
    .filter(v => v !== undefined);
  const euis = successful
    .map(r => r.eui)
    .filter(v => v !== undefined);
  
  if (lightingPowers.length > 0) {
    const avgLighting = lightingPowers.reduce((a, b) => a + b, 0) / lightingPowers.length;
    const status = avgLighting >= 8 ? '✅ FIXED' : avgLighting >= 5 ? '⚠️  PARTIALLY FIXED' : '❌ NOT FIXED';
    console.log(`1. Lighting Power Density: ${avgLighting.toFixed(1)} W/m² ${status}`);
    console.log(`   (Expected: 8-12 W/m², Previous: 2.0 W/m²)`);
  }
  
  if (equipmentPowers.length > 0) {
    const avgEquipment = equipmentPowers.reduce((a, b) => a + b, 0) / equipmentPowers.length;
    const status = avgEquipment >= 5 ? '✅ FIXED' : avgEquipment >= 3 ? '⚠️  PARTIALLY FIXED' : '❌ NOT FIXED';
    console.log(`2. Equipment Power Density: ${avgEquipment.toFixed(1)} W/m² ${status}`);
    console.log(`   (Expected: 5-10 W/m², Previous: 2.0 W/m²)`);
  }
  
  if (euis.length > 0) {
    const avgEui = euis.reduce((a, b) => a + b, 0) / euis.length;
    const status = avgEui >= 50 && avgEui <= 200 ? '✅ REASONABLE' : avgEui >= 20 ? '⚠️  LOW' : '❌ TOO LOW';
    console.log(`3. Energy Use Intensity: ${avgEui.toFixed(2)} kWh/m²/year ${status}`);
    console.log(`   (Expected: 50-200 kWh/m²/year, Previous: ~0.8 kWh/m²/year)`);
  }
  
  // EnergyPlus warnings summary
  console.log('\n⚠️  EnergyPlus Warnings Summary:');
  console.log('-'.repeat(70));
  const allWarnings = successful.flatMap(r => r.warnings);
  const warningCounts = {};
  allWarnings.forEach(w => {
      const key = w.substring(0, 60).trim();
      warningCounts[key] = (warningCounts[key] || 0) + 1;
  });
  
  const sortedWarnings = Object.entries(warningCounts)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 10);
  
  if (sortedWarnings.length > 0) {
    sortedWarnings.forEach(([warning, count]) => {
      console.log(`   [${count}x] ${warning}...`);
    });
  } else {
    console.log('   No warnings found');
  }
  
  // New issues found
  console.log('\n🔍 New Issues Found:');
  console.log('-'.repeat(70));
  const allIssues = successful.flatMap(r => r.issues);
  const issueCounts = {};
  allIssues.forEach(issue => {
    issueCounts[issue] = (issueCounts[issue] || 0) + 1;
  });
  
  if (Object.keys(issueCounts).length > 0) {
    Object.entries(issueCounts)
      .sort((a, b) => b[1] - a[1])
      .forEach(([issue, count]) => {
        console.log(`   [${count}x] ${issue}`);
      });
  } else {
    console.log('   ✅ No new issues found');
  }
  
  console.log('\n🔁 Per-Test Issue Breakdown:');
  console.log('-'.repeat(70));
  allResults.forEach(result => {
    console.log(`Test ${result.test_number}: ${result.idf_name}`);
    console.log(`   IDF Path: ${result.idf_path}`);
    console.log(`   Success: ${result.success ? 'Yes' : 'No'}`);
    console.log(`   Weather: ${result.weather_file || 'N/A'}`);
    console.log(`   Elapsed: ${result.elapsed_time || 'n/a'} s`);
    console.log(`   Warnings: ${result.warnings.length}`);
    if (result.warning_summary.length > 0) {
      result.warning_summary.forEach(({ message, count }) => {
        console.log(`     [${count}x] ${message}...`);
      });
    }
    if (result.errors.length > 0) {
      console.log(`   Errors: ${result.errors.length}`);
      result.error_summary.forEach(({ message, count }) => {
        console.log(`     [${count}x] ${message}...`);
      });
    }
    if (result.issues.length > 0) {
      console.log(`   Tracked Issues (${result.issues.length}):`);
      result.issues.slice(0, 5).forEach(issue => {
        console.log(`     - ${issue}`);
      });
      if (result.issues.length > 5) {
        console.log('     ...');
      }
    }
    console.log('-'.repeat(70));
  });
  
  // Detailed results table
  console.log('\n📊 Detailed Results:');
  console.log('-'.repeat(70));
  console.log('IDF File'.padEnd(35) + 'Area'.padEnd(8) + 'Light'.padEnd(8) + 'Equip'.padEnd(8) + 'EUI'.padEnd(10) + 'Issues');
  console.log('-'.repeat(70));
  successful.forEach(r => {
    const idfName = r.idf_name.substring(0, 33);
    const area = (r.idf_analysis?.info?.total_area || 0).toFixed(0);
    const light = (r.idf_analysis?.info?.avg_lighting_power || 0).toFixed(1);
    const equip = (r.idf_analysis?.info?.avg_equipment_power || 0).toFixed(1);
    const eui = (r.eui || 0).toFixed(2);
    const issues = r.issues.length;
    console.log(`${idfName.padEnd(35)}${area.padEnd(8)}${light.padEnd(8)}${equip.padEnd(8)}${eui.padEnd(10)}${issues}`);
  });
  
  // Iteration history summary
  console.log('\n📈 Iteration History:');
  console.log('-'.repeat(70));
  if (progress.iterations && progress.iterations.length > 0) {
    progress.iterations.forEach(iter => {
      const isBest = iter.iteration === progress.best_iteration;
      const marker = isBest ? '⭐ BEST' : '';
      console.log(`   Iteration #${iter.iteration}: ${iter.total_warnings} warnings ${marker}`);
      console.log(`      Commit: ${iter.git_commit.substring(0, 8)}, Branch: ${iter.git_branch}`);
      console.log(`      Timestamp: ${new Date(iter.timestamp).toLocaleString()}`);
    });
  } else {
    console.log('   No previous iterations');
  }
  
  console.log('\n' + '='.repeat(70));
  
  // Final recommendation
  if (warningsIncreased && currentBest) {
    console.log(`\n💡 RECOMMENDATION:`);
    console.log(`   Warnings increased from ${currentBest.total_warnings} to ${totalWarnings}`);
    console.log(`   Previous best iteration had fewer warnings.`);
  } else if (isNewBest) {
    console.log(`\n✅ This iteration is the new best! Continue optimizing from here.`);
  }
  
  console.log('\n' + '='.repeat(70));
}

// Export functions for use in iterative test
export { runTest, findLocalIDFFiles, findLocalWeatherFiles, matchWeatherFile, calculateTotalWarnings };

main().catch(console.error);

