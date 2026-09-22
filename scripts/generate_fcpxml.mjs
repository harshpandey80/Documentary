#!/usr/bin/env node
/**
 * scripts/generate_fcpxml.mjs
 * Generates well-formed, frame-accurate FCPXML 1.8 from timeline.json using @chatoctopus/timeline.
 * Enforces mandatory validation check before writing output file.
 */

import fs from 'fs';
import path from 'path';
import {
  createTimeline,
  exportTimeline,
  validateTimeline,
  rational,
  secondsToFrameAligned,
  ZERO,
} from '@chatoctopus/timeline';

function main() {
  const args = process.argv.slice(2);
  if (args.length < 2) {
    console.error('Usage: node scripts/generate_fcpxml.mjs <input_timeline.json> <output_timeline.fcpxml>');
    process.exit(1);
  }

  const inputJsonPath = path.resolve(args[0]);
  const outputFcpxmlPath = path.resolve(args[1]);

  if (!fs.existsSync(inputJsonPath)) {
    console.error(`Input file not found: ${inputJsonPath}`);
    process.exit(1);
  }

  let timelineData;
  try {
    timelineData = JSON.parse(fs.readFileSync(inputJsonPath, 'utf8'));
  } catch (err) {
    console.error(`Failed to parse timeline JSON: ${err.message}`);
    process.exit(1);
  }

  const res = timelineData.resolution || { width: 1920, height: 1080, fps: 30 };
  const fpsRational = rational(res.fps || 30, 1);

  const videoClips = timelineData.tracks?.video || [];
  const audioMasterPath = timelineData.tracks?.audio_master;

  // Build video track items
  const videoItems = videoClips.map((c, idx) => {
    const durRational = secondsToFrameAligned(c.duration, fpsRational);
    const assetFile = c.asset_path ? path.resolve(c.asset_path) : `asset_${idx}.jpg`;
    const assetUrl = `file:///${assetFile.replace(/\\/g, '/')}`;

    return {
      kind: 'clip',
      name: c.clip_id || `clip_${idx}`,
      mediaReference: {
        type: 'external',
        targetUrl: assetUrl,
        name: path.basename(assetFile),
        mediaKind: 'image',
        availableRange: { startTime: ZERO, duration: durRational },
      },
      sourceRange: { startTime: ZERO, duration: durRational },
    };
  });

  const tracks = [
    {
      kind: 'video',
      items: videoItems,
    },
  ];

  // If audio master exists, add audio track
  if (audioMasterPath && fs.existsSync(audioMasterPath)) {
    const totalDurationSec = videoClips.reduce((acc, c) => acc + (c.duration || 0), 0);
    const audioDurRational = secondsToFrameAligned(totalDurationSec, fpsRational);
    const audioUrl = `file:///${path.resolve(audioMasterPath).replace(/\\/g, '/')}`;

    tracks.push({
      kind: 'audio',
      items: [
        {
          kind: 'clip',
          name: 'master_audio',
          mediaReference: {
            type: 'external',
            targetUrl: audioUrl,
            name: path.basename(audioMasterPath),
            mediaKind: 'audio',
            availableRange: { startTime: ZERO, duration: audioDurRational },
          },
          sourceRange: { startTime: ZERO, duration: audioDurRational },
        },
      ],
    });
  }

  const timeline = createTimeline({
    name: path.basename(path.dirname(inputJsonPath)) || 'DocStudio Project',
    format: {
      width: res.width || 1920,
      height: res.height || 1080,
      frameRate: fpsRational,
      audioRate: 48000,
    },
    tracks,
  });

  // Mandatory Validation Pass
  const validationErrors = validateTimeline(timeline);
  if (validationErrors && validationErrors.length > 0) {
    console.error('Validation FAILED for generated timeline:');
    for (const err of validationErrors) {
      console.error(` - [${err.code || 'ERROR'}] ${err.message} (${err.path || 'timeline'})`);
    }
    process.exit(2);
  }

  // Export to FCPXML 1.8
  let fcpxmlString;
  try {
    fcpxmlString = exportTimeline(timeline, 'fcpx');
  } catch (err) {
    console.error(`FCPXML export failed: ${err.message}`);
    process.exit(3);
  }

  // Write to destination
  fs.mkdirSync(path.dirname(outputFcpxmlPath), { recursive: true });
  fs.writeFileSync(outputFcpxmlPath, fcpxmlString, 'utf8');
  console.log(`Successfully generated and validated FCPXML 1.8: ${outputFcpxmlPath}`);
  process.exit(0);
}

main();
